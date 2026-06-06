"""FastAPI application for the Tor relay dashboard."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import __version__
from .auth import (
    NotAuthenticated,
    current_user,
    login_redirect,
    require_auth,
    verify_credentials,
)
from .config import settings
from .history import history
from .system_control import HelperError, save_torrc, service_action, service_status
from .torrc_manager import QUICK_KEYS, parse_quick_values, read_torrc
from .tor_controller import tor

BASE_DIR = Path(__file__).resolve().parent

# Time windows offered for the history (label -> seconds)
RANGES = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800}


async def _sampler() -> None:
    """Sample the metrics at a regular interval for the history."""
    retention = settings.history_retention_days * 86400
    while True:
        try:
            metrics = await asyncio.to_thread(tor.get_metrics)
            history.add(metrics)
            history.prune(retention)
        except Exception:
            pass
        await asyncio.sleep(settings.sample_interval)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_sampler())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        tor.close()


app = FastAPI(title="Tor Relay Dashboard", version=__version__, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=settings.session_max_age,
    same_site="lax",
    https_only=settings.cookie_secure,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# --- handling of missing authentication -------------------------------------
@app.exception_handler(NotAuthenticated)
async def _on_not_authenticated(request: Request, exc: NotAuthenticated):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "unauthenticated"}, status_code=401)
    return login_redirect()


def _ctx(request: Request, **extra) -> dict:
    return {
        "request": request,
        "user": current_user(request),
        "version": __version__,
        **extra,
    }


# --- authentication ---------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", _ctx(request, error=None))


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    totp: str = Form(""),
):
    if verify_credentials(username, password, totp):
        request.session["user"] = username
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        _ctx(request, error="Identifiants ou code 2FA invalides."),
        status_code=401,
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# --- pages ------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    require_auth(request)
    return templates.TemplateResponse("dashboard.html", _ctx(request, page="dashboard"))


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    require_auth(request)
    content = read_torrc()
    return templates.TemplateResponse(
        "config.html",
        _ctx(
            request,
            page="config",
            torrc=content,
            quick_keys=QUICK_KEYS,
            quick_values=parse_quick_values(content),
            torrc_path=settings.torrc_path,
            flash=request.session.pop("flash", None),
            flash_err=request.session.pop("flash_err", None),
        ),
    )


@app.post("/config")
async def config_save(request: Request, torrc: str = Form(...)):
    require_auth(request)
    try:
        save_torrc(torrc)
        request.session["flash"] = (
            "Configuration validée et enregistrée. "
            "Redémarrez ou rechargez Tor pour l'appliquer."
        )
    except HelperError as exc:
        request.session["flash_err"] = f"torrc refusé : {exc}"
    return RedirectResponse("/config", status_code=303)


@app.get("/control", response_class=HTMLResponse)
async def control_page(request: Request):
    require_auth(request)
    return templates.TemplateResponse(
        "control.html",
        _ctx(
            request,
            page="control",
            status=service_status(),
            service=settings.tor_service,
            flash=request.session.pop("flash", None),
            flash_err=request.session.pop("flash_err", None),
        ),
    )


@app.post("/control/{action}")
async def control_action(request: Request, action: str):
    require_auth(request)
    labels = {
        "start": "démarré",
        "stop": "arrêté",
        "restart": "redémarré",
        "reload": "rechargé",
    }
    if action not in labels:
        request.session["flash_err"] = "Action inconnue."
        return RedirectResponse("/control", status_code=303)
    try:
        service_action(action)
        request.session["flash"] = f"Relais Tor {labels[action]} avec succès."
        if action in ("stop", "restart"):
            tor.close()  # invalidate the ControlPort connection
    except HelperError as exc:
        request.session["flash_err"] = f"Échec de l'action : {exc}"
    return RedirectResponse("/control", status_code=303)


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    require_auth(request)
    return templates.TemplateResponse(
        "history.html",
        _ctx(request, page="history", ranges=list(RANGES.keys())),
    )


@app.get("/connections", response_class=HTMLResponse)
async def connections_page(request: Request):
    require_auth(request)
    return templates.TemplateResponse(
        "connections.html", _ctx(request, page="connections")
    )


# --- API (consumed by the JS front-end) -------------------------------------
@app.get("/api/metrics")
async def api_metrics(request: Request):
    require_auth(request)
    return JSONResponse(tor.get_metrics())


@app.get("/api/history")
async def api_history(request: Request, range: str = "24h"):
    require_auth(request)
    seconds = RANGES.get(range, RANGES["24h"])
    points = await asyncio.to_thread(history.series, seconds)
    return JSONResponse({"range": range, "points": points})


@app.get("/api/connections")
async def api_connections(request: Request):
    require_auth(request)
    data = await asyncio.to_thread(tor.connections_by_country)
    return JSONResponse(data)


@app.get("/api/status")
async def api_status(request: Request):
    require_auth(request)
    return JSONResponse({"status": service_status()})


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": __version__}
