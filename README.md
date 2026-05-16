# ThinkSprint — Online Quiz Platform

A full-stack quiz platform built with Flask. Creators build quizzes with MCQ questions, share a join code, and participants race the clock for bonus points. Includes AI-powered answer explanations, gamification, per-question analytics, and a public quiz browse page.

---

## Features

### Quiz Creation & Management
- **MCQ Quiz Builder** — add unlimited questions with 2–6 options each, mark the correct answer, upload optional question images (PNG/JPG/GIF/WebP, max 5MB)
- **Question Explanations** — creator can write an optional explanation per question; if left blank, AI (Groq LLaMA) auto-generates one when participants review answers
- **Quiz Settings** — configure per-question timer (5–300s), join window (5/10/30/60 min), bonus system, negative marking, shuffle questions, multiple attempts
- **Public vs Private mode** — private quizzes use a 6-character join code (ABC123); public quizzes are always active, listed on the Browse page, no code needed
- **Creator Dashboard** — view all quizzes with status, attempt count, join code, and quick actions
- **Manage Page** — live participant count (auto-polls every 5s), leaderboard, start/end controls, analytics link
- **Per-Question Analytics** — for each question: % correct, wrong count, skipped count, average time, most common wrong answer, auto difficulty badge (Easy/Medium/Hard)
- **Quiz Preview** — creator can preview all questions before starting
- **Edit Quiz** — modify settings before any attempts are recorded

### Participant Experience
- **Join by Code** — enter a 6-character code with client-side format validation (3 letters + 3 digits)
- **Browse Public Quizzes** — search and filter active public quizzes, join without a code
- **Take Quiz** — per-question countdown timer with colour feedback (green → orange → red), auto-advance on expiry, answered counter showing X/Y answered live
- **Unanswered Warning** — before final submit, if questions were skipped a modal warns the participant with exact count and option to go back
- **Review Answers** — after submission, see every question with your answer, correct answer, time taken, and AI-generated explanation
- **Leaderboard** — sorted by final score then time; shows only best attempt per user when multiple attempts allowed
- **Attempt History** — full history of all quizzes taken with scores, accuracy bars, and links to results

### Scoring System
- **Raw Score** — count of correct answers
- **Negative Marking** — optional penalty per wrong answer (configurable 0.1–10 points)
- **Net Score** — `max(0, raw_score - penalty)`
- **Bonus Points** — awarded to highest scorer with least time (requires ≥2 participants)
- **Final Score** — `net_score + bonus_points`

### Gamification
- **Daily Streaks** — tracks consecutive days with at least one quiz; shows current streak, best streak, and a 7-day progress bar
- **5 Badges** — awarded automatically after each submission, shown with glowing icons on the profile page; locked badges show a padlock

| Badge | Condition |
|-------|-----------|
| Perfect Score | Score 100% on any quiz |
| Speed Demon | Finish in the fastest 25% of all participants |
| Quiz Veteran | Complete 10 or more quizzes |
| Streak Master | Maintain a 3-day daily quiz streak |
| Top Scholar | Rank #1 on any quiz leaderboard |

### AI Explanations (Groq)
- When a participant opens "Review Answers", questions without a creator-written explanation trigger a Groq LLaMA API call
- Explanation is generated in 1–2 seconds and cached permanently — the API is only called once per question ever
- AI-generated explanations are labelled "AI generated" so participants know the source
- Graceful fallback — if the API fails, the page still works normally with no error shown

### Security & Logic
- **Session hardening** — `HttpOnly`, `SameSite=Lax`, `Secure` in production
- **Password requirements** — minimum 8 characters, must contain at least one letter and one number
- **Server-side time cap** — submitted `total_time` is clamped to `(timer × questions) + 30s` to prevent cheating
- **Open redirect protection** — `next=` parameter validated to reject external URLs
- **Input length caps** — title (200 chars), description (1000 chars)
- **Image upload safety** — extension whitelist, 5MB limit, `secure_filename`, try/except on save
- **Leaderboard deduplication** — when multiple attempts allowed, only best attempt per user shown

### UX
- **Hamster loading screen** — animated hamster in a wheel shown for 2 seconds on every page navigation and quiz submission (from Uiverse.io by Nawsome)
- **Mobile responsive** — works on all screen sizes
- **Flash messages** — categorised success/warning/danger/info banners
- **Scroll-to-error** — server-side validation errors shown as flash messages

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.0 + SQLAlchemy + Flask-Migrate |
| Database | PostgreSQL (production) / SQLite (dev) |
| Auth | Flask-Login + Werkzeug password hashing |
| Frontend | Jinja2 templates + Tailwind CSS (CDN) |
| JavaScript | Vanilla JS (quiz timer, answer tracking, AI fetch) |
| AI | Groq API — LLaMA 3.1 8B Instant |
| Deploy | Render (gunicorn) |
| Config | python-dotenv |

---

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/Bhagyesh312/CODSOFT.git
cd CODSOFT

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env — add your DATABASE_URL, SECRET_KEY, and GROQ_API_KEY

# 5. Run database migrations
flask db upgrade

# 6. Start the app
flask run
```

Visit `http://localhost:5000`

> **Quick start on Windows:** double-click `start.bat` — activates venv, runs migrations, starts Flask, and opens the browser automatically.

---

## Environment Variables

```
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost/thinksprint
GROQ_API_KEY=your-groq-api-key-here
```

Get a free Groq API key at **https://console.groq.com/keys** (14,400 requests/day free).

---

## Database Setup (PostgreSQL via pgAdmin4)

Run the SQL files in `data/` in order:

1. `01_setup.sql` — creates all tables
2. `02_indexes.sql` — adds indexes and constraints
3. `03_migrate.sql` — creates Alembic version tracking table
4. `04_add_shuffle_questions.sql` — shuffle questions feature
5. `05_new_features.sql` — additional quiz columns
6. `06_add_is_public.sql` — public quiz listing
7. `07_add_streak_and_badges.sql` — streak tracking and badges system

---

## Project Structure

```
ThinkSprint/
├── app.py                  # All routes, business logic, AI endpoint
├── models.py               # SQLAlchemy models (User, Quiz, Question, Attempt, Badge...)
├── config.py               # Config classes + constants
├── start.bat               # Windows one-click dev server launcher
├── requirements.txt
├── data/                   # pgAdmin SQL migration files
├── migrations/             # Alembic migration versions
├── static/
│   ├── css/style.css       # Global styles + hamster loader CSS
│   └── js/quiz_timer.js    # Quiz timer, answer tracking, unanswered warning
└── templates/
    ├── base.html           # Base layout + hamster overlay + nav
    ├── index.html          # Homepage
    ├── profile.html        # Streaks, badges, recent attempts
    ├── error.html
    ├── auth/               # login.html, register.html
    ├── creator/            # dashboard, create_quiz, edit_quiz, manage_quiz,
    │                       # preview_quiz, analytics
    └── participant/        # join, take_quiz, result, leaderboard,
                            # my_attempts, quiz_listing
```

---

## Bonus Logic

- Requires minimum **2 participants**
- Finds the **highest net score** among all submitted attempts
- Among top scorers, finds the **minimum time taken**
- All participants matching both conditions receive the configured bonus points
- Calculated when the creator clicks **End Quiz** or when the last participant submits on an already-ended quiz
- Ties: all tied participants receive the bonus

---

## Public vs Private Quizzes

| | Private | Public |
|---|---|---|
| Access | 6-char join code | Browse page, no code |
| Active state | Creator starts/ends manually | Always active |
| Join window | Configurable expiry | No expiry |
| Multiple attempts | Optional | Forced on |
| Leaderboard | Yes | Yes |

---

## Loading Screen

The animated hamster loading screen is sourced from **[Uiverse.io](https://uiverse.io)**, created by **Nawsome**.

- Pure HTML + CSS, no JavaScript
- Shows for 2 seconds minimum on every page navigation
- Shows during quiz submission with "Crunching your answers..." message
- Integrated into `templates/base.html` and `static/css/style.css`

---

## Deploy to Render

1. Push to GitHub
2. Create a new Web Service on Render pointing to your repo
3. Set environment variables: `SECRET_KEY`, `DATABASE_URL`, `GROQ_API_KEY`
4. Render runs `flask db upgrade` and starts with `gunicorn app:app`
