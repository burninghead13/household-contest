# 🏆 Haushalt Wettbewerb

Eine selbst gehostete Web-App für den monatlichen Haushaltspunkte-Wettbewerb.  
Wer am Monatsende die meisten Punkte hat, bekommt ein Essen spendiert!

---

## Features

- **Live-Rangliste** mit Punktestand beider Spieler
- **Schnelleintrag** – Aufgabe auswählen, Spieler anklicken, fertig
- **Admin-Bereich** – Aufgaben & Punktwerte frei konfigurieren, Spielernamen & Farben anpassen
- **Monatsarchiv** – alle vergangenen Wettbewerbe einsehbar
- **Passwortschutz** – separates App- und Admin-Passwort
- **Automatischer Monatsreset** – neuer Monat = neue Runde (alte Daten bleiben im Archiv)

---

## Deployment auf dem Raspberry Pi

### 1. Dateien übertragen

```bash
# Vom eigenen PC aus (ersetze IP entsprechend)
scp -r haushalt-app/ tom@<PI-IP>:/opt/haushalt-app
```

Oder direkt auf dem Pi klonen/erstellen:

```bash
mkdir -p /opt/haushalt-app
cd /opt/haushalt-app
# Dateien hineinkopieren
```

### 2. Passwörter anpassen

In `docker-compose.yml` die drei Werte ändern:

```yaml
environment:
  - APP_PASSWORD=dein-app-passwort       # für alle Nutzer
  - ADMIN_PASSWORD=dein-admin-passwort   # nur für dich
  - SECRET_KEY=langer-zufaelliger-string # z.B. mit: openssl rand -hex 32
```

### 3. Container starten

```bash
cd /opt/haushalt-app
docker compose up -d --build
```

### 4. App aufrufen

Im Heimnetz erreichbar unter:

```
http://<PI-IP>:8095
```

Den Port 8095 kannst du in `docker-compose.yml` beliebig ändern.

---

## Verwaltung

```bash
# Logs anschauen
docker compose logs -f haushalt

# Container neustarten
docker compose restart haushalt

# Update (nach Änderungen an den Dateien)
docker compose up -d --build

# Stoppen
docker compose down
```

---

## Passwörter

| Passwort | Zugang |
|---|---|
| `APP_PASSWORD` | Normale Nutzung (Punkte eintragen, Archiv sehen) |
| `ADMIN_PASSWORD` | Admin-Bereich (Aufgaben/Spieler verwalten, Einträge löschen) |

Der Admin hat automatisch auch vollen App-Zugriff.

---

## Daten

Die SQLite-Datenbank liegt im Docker Volume `haushalt-data` und überlebt Container-Neustarts und Updates problemlos.

Backup erstellen:
```bash
docker cp haushalt-app:/data/haushalt.db ./haushalt-backup-$(date +%Y%m%d).db
```

---

## Standardmäßig enthaltene Aufgaben

| Aufgabe | Punkte |
|---|---|
| Staubsaugen | 3 |
| Wischen | 4 |
| Abwasch | 2 |
| Einkaufen | 3 |
| Wäsche waschen | 3 |
| Wäsche aufhängen | 2 |
| Müll rausbringen | 2 |
| Bad putzen | 4 |
| Kochen | 3 |

Alle Aufgaben können im Admin-Bereich angepasst, deaktiviert oder gelöscht werden.
