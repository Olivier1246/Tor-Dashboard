# Tor Relay Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-stem-009688.svg)
![Platform](https://img.shields.io/badge/Platform-Debian%20%7C%20Ubuntu-A81D33.svg)
![Access](https://img.shields.io/badge/Access-Tor%20onion%20%2B%202FA-7D4698.svg)

Tableau de bord web pour piloter un **relais Tor personnel** hébergé sur une VM
Debian/Ubuntu. Il affiche les métriques du relais, permet de modifier sa
configuration (`torrc`), et de le démarrer / arrêter / redémarrer — le tout
derrière une authentification forte et accessible **hors LAN via un service
onion** (aucun port ouvert sur Internet).

## Fonctionnalités

- **Métriques temps réel** : débits montant/descendant (sparklines), trafic
  cumulé, temps de fonctionnement, % de bootstrap, circuits & connexions,
  drapeaux du consensus (Guard/Fast/Stable/Exit…), politique de sortie,
  comptabilité de bande passante (`AccountingMax`), identité (surnom,
  empreinte, version), adresse `.onion` du dashboard.
- **Historique persistant** : échantillonnage en arrière-plan (SQLite) des
  débits, circuits et connexions, avec graphiques sur 1 h / 6 h / 24 h / 7 j
  (rétention configurable). Survit aux redémarrages du dashboard.
- **Connexions par pays** : répartition géographique des pairs relais, résolue
  via le ControlPort (`orconn-status` → consensus → base GeoIP de Tor), sans
  aucun accès aux sockets système.
- **Édition de configuration** : éditeur `torrc` avec **validation
  `tor --verify-config` avant écriture** (un fichier invalide est rejeté sans
  rien écraser) + vue des directives clés.
- **Contrôle du service** : démarrer / arrêter / redémarrer / recharger via
  `systemctl`, état systemd en direct.
- **Sécurité** : login + mot de passe (bcrypt) + **2FA TOTP**, sessions
  signées, exposition via **onion service v3**, privilèges élevés confinés à un
  unique helper root (sudoers restreint).
- **Démarrage automatique** au boot de la VM, **après** le relais Tor
  (`After=`/`Requires=tor.service`).

## Architecture

```
Navigateur (Tor Browser)
        │  http://xxxxxxxx.onion
        ▼
   Démon Tor  ──HiddenServicePort──►  127.0.0.1:8080  (uvicorn / FastAPI)
        ▲                                   │
        │ ControlPort 9051 (métriques)      │ sudo  ┌───────────────────────┐
        └───────────────────────────────────┴──────►│ tor-dashboard-helper  │
                                                     │ start/stop/.../torrc  │ (root)
                                                     └───────────────────────┘
```

| Composant | Rôle |
|-----------|------|
| `app/tor_controller.py` | Lecture des métriques + connexions par pays (stem) |
| `app/history.py`        | Historique persistant (SQLite) + échantillonnage |
| `app/countries.py`      | Codes pays ISO → nom FR + drapeau emoji |
| `app/system_control.py` | Appels au helper privilégié (sudo) |
| `app/torrc_manager.py`  | Lecture/parsing du `torrc` |
| `app/auth.py`           | Mot de passe bcrypt + TOTP + sessions |
| `app/main.py`           | Routes FastAPI + pages + tâche d'échantillonnage |
| `deploy/`               | Helper, unité systemd, sudoers, exemple torrc |
| `scripts/`              | `install.sh`, `manage.py` (comptes) |

## Installation (sur la VM)

```bash
git clone <repo> tor-dashboard && cd tor-dashboard
sudo ./scripts/install.sh
```

Puis suivez les 4 étapes affichées en fin d'installation :

1. **Activer ControlPort + onion service** — ajoutez `deploy/torrc.example`
   à `/etc/tor/torrc` (en adaptant les directives de relais), puis
   `sudo systemctl restart tor@default`.
2. **Créer un compte** :
   ```bash
   sudo -u tordash /opt/tor-dashboard/.venv/bin/python \
        /opt/tor-dashboard/scripts/manage.py useradd admin
   ```
   Scannez le QR code TOTP affiché (Aegis, Google Authenticator…).
3. **Démarrer** : `sudo systemctl start tor-dashboard`.
4. **Récupérer l'adresse onion** :
   `sudo cat /var/lib/tor/dashboard/hostname` → à ouvrir dans Tor Browser.

## Développement local (Windows/Linux)

> Le contrôle réel d'un relais nécessite la VM. En local, on peut lancer
> l'interface ; les métriques resteront « hors ligne » sans ControlPort
> accessible.

```bash
python -m venv .venv
.venv\Scripts\activate          # PowerShell : .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # éditez SECRET_KEY
python scripts\manage.py useradd admin
uvicorn app.main:app --reload --port 8080
```

Ouvrez http://127.0.0.1:8080/.

## Sécurité — notes

- Le dashboard n'écoute qu'en `127.0.0.1`. L'accès distant passe
  **exclusivement** par l'onion service : rien n'est exposé sur l'IP publique.
- Les actions privilégiées (systemctl, écriture du torrc) ne sont **jamais**
  exécutées directement par le service web : elles transitent par
  `tor-dashboard-helper`, seul binaire autorisé dans sudoers, à sous-commandes
  fixes.
- `.env` et `users.json` (hash + secret TOTP) sont en mode `600`,
  propriété de `tordash`, et exclus de Git.
- Pensez à conserver précieusement le secret TOTP affiché à la création du
  compte (impossible à récupérer ensuite ; recréez le compte si perdu).

## Gestion des comptes

```bash
manage.py useradd <nom>   # crée un compte + secret TOTP (QR)
manage.py passwd  <nom>   # change le mot de passe
manage.py list            # liste les comptes
manage.py delete  <nom>   # supprime un compte
```

## Licence

Distribué sous licence **MIT** — voir [LICENSE](LICENSE). Fourni tel quel, sans
garantie. Vous êtes libre de l'utiliser, le modifier et le redistribuer.
