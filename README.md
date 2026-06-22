# Davlat Auditi Oliy Maktabi, Telegram Bot

Production Telegram bot for **@davlat_auditi_bot**: student registration and
two-way Q&A for the Higher School of State Audit at Toshkent Davlat
Iqtisodiyot Universiteti.

## Features

- **Student side**: Uzbek registration flow (name, phone, program, region) with
  confirmation, text + voice questions, `/info` to view their record.
- **Admin side**: dashboard (`/admin`), unanswered-question worklist (`/queue`),
  question stats (`/stats`), reply-to-student flow (text or voice), reusable
  canned answers (`/faq_add`, `/faq_list`, `/faq_del`, `/faq` in reply mode),
  `/broadcast`, CSV `/export`.
- **Persistence**: SQLite (single file, WAL mode).
- **Healthcheck**: tiny aiohttp endpoint on `PORT` so Railway never sleeps the
  service.

## Tech

- Python 3.11+
- aiogram 3.x (async)
- aiosqlite
- aiohttp (healthcheck)

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your BOT_TOKEN and ADMIN_IDS
```

Then export the variables and run:

```powershell
$env:BOT_TOKEN = "123:abc..."
$env:ADMIN_IDS = "111111111,222222222"
$env:PORT      = "8080"
python -m bot.main
```

Probe the healthcheck:

```powershell
Invoke-WebRequest http://localhost:8080/
```

## Configuration

| Variable    | Required | Default              | Purpose                                            |
|-------------|----------|----------------------|----------------------------------------------------|
| `BOT_TOKEN` | yes      | (none)               | BotFather token                                    |
| `ADMIN_IDS` | yes      | (none)               | Comma-separated Telegram user IDs of admins        |
| `PORT`      | no       | `8080`               | aiohttp healthcheck port                           |
| `DB_PATH`   | no       | `davlat_auditi.db`   | SQLite file path (set to `/data/...` on Railway)   |

To get a user's Telegram ID, message `@userinfobot` from the account.

## Railway deploy

1. Push this repo to GitHub.
2. New Project, "Deploy from GitHub repo".
3. Add environment variables (`BOT_TOKEN`, `ADMIN_IDS`).
4. Add a Volume mounted at `/data` so the SQLite file survives redeploys.
   Then set `DB_PATH=/data/davlat_auditi.db` in env.
5. Railway will read `railway.toml` and `Dockerfile`. The healthcheck path
   `/` keeps the service awake on plans that idle inactive web services.

### Fallback ping (free tier safety net)

If your Railway plan still sleeps the service despite the healthcheck,
register the public URL with [UptimeRobot](https://uptimerobot.com) (free,
5-minute interval) pointing at `https://<your-service>.up.railway.app/`.

## Database

The schema is created automatically on first run:

- `students`: one row per registered user.
- `questions`: one row per inbound question (`text` or `voice`); `answered_at`
  is `NULL` until an admin replies.
- `question_notifications`: per-(question, admin) notification message id, so a
  question can be marked answered across every admin's chat.
- `faq`: reusable canned answers keyed by a normalized keyword.

Backups: copy the SQLite file from the Railway volume. Locally, just copy
`davlat_auditi.db`.

## Admin commands

| Command            | What it does                                                |
|--------------------|-------------------------------------------------------------|
| `/admin`           | Dashboard: counts, unanswered questions, command list       |
| `/queue`           | Paged worklist of unanswered questions, oldest first        |
| `/stats`           | Question stats: total, unanswered, answered                 |
| `/faq_add`         | Save a reusable canned answer (asks for keyword, then text) |
| `/faq_list`        | List all saved canned answers                               |
| `/faq_del <kw>`    | Delete the canned answer with keyword `<kw>`                |
| `/broadcast <msg>` | Send `<msg>` to every registered student (paced, ~20/sec)   |
| `/export`          | Send a CSV file of all students                             |
| `/cancel`          | Exit the current flow (reply mode, FAQ add, broadcast)      |

Admin reply flow: each new question notification ships with a **Javob yozish**
inline button. Click it, then send a text or voice message; the bot forwards
it to the student and marks the question answered, closing out that
notification (button removed, "✅ Javob berildi" appended) in every admin's
chat.

`/queue` is the worklist: it lists only unanswered questions (5 per page,
oldest first, with how long each has waited), and each row has a numbered
reply button. Pagination edits the same message in place.

Canned answers: in reply mode, send `/faq <keyword>` to reply with a saved
answer instead of typing it. When a new text question arrives, the bot
keyword-matches it against saved FAQs and, on a strong match, adds a
**Tayyor javob** button (plus a `/faq <keyword>` hint) to the notification.
Tapping it shows the full answer with a **Yuborilsinmi?** Ha/Yo'q
confirmation; the answer is only sent on Ha (no auto-send, to avoid a keyword
false-positive replying to a student).

## Project layout

```
bot/
  main.py          entrypoint, dispatcher, healthcheck
  config.py        env-var parsing
  db.py            aiosqlite persistence
  utils.py         phone normalization, CSV builder, age + FAQ-match helpers
  keyboards.py     inline + reply keyboards
  texts.py         all Uzbek strings
  handlers/
    start.py         /start, /info
    registration.py  FSM registration flow
    questions.py     student text + voice questions
    admin.py         admin commands, reply mode, broadcast, export
Dockerfile
railway.toml
requirements.txt
.env.example
```
