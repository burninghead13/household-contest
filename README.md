# 🏆 Household Contest

A self-hosted web app for a monthly household chores competition.  
Whoever has the most points at the end of the month wins a free dinner!

---

## Features

- **Live leaderboard** with point totals for both players
- **Quick entry** – select a player, pick a task, done
- **Admin panel** – freely configure tasks & point values, customize player names & colors
- **Monthly archive** – all past competitions with results
- **Password protection** – separate app and admin passwords
- **Automatic monthly reset** – new month = new round (old data stays in the archive)
- **Language support** – English and German, switchable at any time

---

## Deployment on Raspberry Pi (or any Docker host)

### 1. Transfer files

```bash
# From your local machine (replace name and IP accordingly)
scp -r household-contest/ name@<PI-IP>:/opt/household-contest
```

Or directly on the Pi:

```bash
mkdir -p /opt/household-contest
cd /opt/household-contest
# Copy files here
```

### 2. Set your passwords

Edit `docker-compose.yml` and change the three placeholder values:

```yaml
environment:
  - APP_PASSWORD=your-app-password        # for all users
  - ADMIN_PASSWORD=your-admin-password    # for you only
  - SECRET_KEY=long-random-string         # generate with: openssl rand -hex 32
  - DEFAULT_LANG=en                       # 'en' for English, 'de' for German
```

### 3. Start the container

```bash
cd /opt/household-contest
docker compose up -d --build
```

### 4. Open the app

Available in your home network at:

```
http://<PI-IP>:8095
```

The port `8095` can be changed freely in `docker-compose.yml`.

---

## Management

```bash
# View logs
docker compose logs -f haushalt

# Restart container
docker compose restart haushalt

# Update after file changes
docker compose up -d --build

# Stop
docker compose down
```

---

## Passwords

| Password | Access |
|---|---|
| `APP_PASSWORD` | Normal use (log tasks, view archive) |
| `ADMIN_PASSWORD` | Admin panel (manage tasks/players, delete entries) |

The admin password also grants full app access.

---

## Data & Backups

The SQLite database lives in the Docker volume `haushalt-data` and survives container restarts and updates.

Create a backup:
```bash
docker cp haushalt-app:/data/haushalt.db ./household-backup-$(date +%Y%m%d).db
```

**Never run `docker compose down -v`** – the `-v` flag deletes volumes including your data.

---

## Default tasks

| Task | Points |
|---|---|
| Vacuuming | 3 |
| Mopping | 4 |
| Dishes | 2 |
| Grocery shopping | 3 |
| Doing laundry | 3 |
| Hanging laundry | 2 |
| Taking out trash | 2 |
| Cleaning bathroom | 4 |
| Cooking | 3 |

All tasks can be adjusted, deactivated, or deleted in the admin panel.

---

## Adding a new language

Open `translations.py` and add a new language block following the existing `de` and `en` entries. Then add the new language option to the switcher in `templates/base.html` and `templates/login.html`.
