# ThinkSprint — Online Quiz Platform

A full-stack quiz platform built with Flask. Creators build quizzes with MCQ questions, share a join code, and participants race the clock for bonus points.

---

## Features

- **Quiz Creation** — MCQ questions, per-question timer, custom bonus system
- **Private Access** — 6-character join code (ABC123 style), valid for 10 minutes
- **Live Timer** — per-question countdown with auto-advance on expiry
- **Bonus System** — highest score + least time earns configurable bonus points
- **Leaderboard** — shareable, sorted by final score then time
- **Review Answers** — question-by-question breakdown after submission
- **Creator Dashboard** — manage, preview, start/end quizzes, view attempts
- **Attempt History** — participants can view all their past attempts
- **Streaks & Badges** — daily quiz streaks, longest streak record, and 5 earnable badges (Perfect Score, Speed Demon, Quiz Veteran, Streak Master, Top Scholar)
- **Mobile Responsive** — works on all screen sizes

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Backend    | Flask + SQLAlchemy + Flask-Migrate |
| Database   | PostgreSQL (Render) / SQLite (dev) |
| Auth       | Flask-Login + Werkzeug hashing    |
| Frontend   | Jinja2 + Tailwind CSS             |
| Timer      | Vanilla JS                        |
| Deploy     | Render                            |

---

## Local Setup

```bash
# 1. Clone and enter the project
cd ThinkSprint

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your DATABASE_URL and SECRET_KEY

# 5. Run database migrations
flask db upgrade

# 6. Start the app
flask run
```

Visit `http://localhost:5000`

> **Quick start on Windows:** double-click `start.bat` — it activates the venv, runs migrations, starts Flask, and opens the browser automatically.

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

Then set your `.env`:
```
DATABASE_URL=postgresql://postgres:yourpassword@localhost/thinksprint
```

---

## Project Structure

```
ThinkSprint/
├── app.py                  # All routes and business logic
├── models.py               # SQLAlchemy models
├── config.py               # App configuration
├── start.bat               # Windows one-click dev server launcher
├── data/                   # SQL setup files for pgAdmin4
├── static/
│   ├── css/style.css       # Global styles + loading screen CSS
│   └── js/quiz_timer.js    # Quiz timer + submission logic
└── templates/
    ├── base.html           # Base layout + global loading overlay
    ├── index.html
    ├── profile.html        # Streaks, badges, recent attempts
    ├── error.html
    ├── auth/               # login, register
    ├── creator/            # dashboard, create, edit, manage, preview
    └── participant/        # join, take_quiz, result, leaderboard, my_attempts
```

---

## Bonus Logic

- Requires minimum **2 participants**
- Finds the **highest score** among all submitted attempts
- Among top scorers, finds the **minimum time taken**
- All participants matching both conditions receive the configured bonus points
- Calculated when the creator clicks **End Quiz** (or when quiz `is_active = False`)
- Ties: all tied participants receive the bonus

---

## Badges

Badges are awarded automatically after each quiz submission:

| Badge | Condition |
|-------|-----------|
| Perfect Score | Score 100% on any quiz |
| Speed Demon | Finish in the fastest 25% of all participants |
| Quiz Veteran | Complete 10 or more quizzes |
| Streak Master | Maintain a 3-day daily quiz streak |
| Top Scholar | Rank #1 on any quiz leaderboard |

Earned badges glow on the profile page. Locked badges show a padlock icon.

---

## Loading Screen

The animated hamster loading screen shown during page navigation and quiz submission is sourced from **[Uiverse.io](https://uiverse.io)**, created by **Nawsome**.

- Component: Rotating hamster in a wheel (pure HTML + CSS, no JS)
- Source: https://uiverse.io
- Used on: all page navigations (2-second minimum display) and quiz submission flow
- Integrated into `templates/base.html` and `static/css/style.css`


