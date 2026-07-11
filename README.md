# Online Examination System

A full-stack cloud-ready Online Examination System built with **Flask + MySQL**.

## Tech Stack
- Backend: Python (Flask), Flask-Login, Flask-SQLAlchemy
- Frontend: HTML5, Bootstrap 5, JavaScript
- Database: MySQL
- Deployment target: Render (or any cloud host that runs Python + connects to MySQL)

## Folder Structure
```
Online-Exam-System/
├── app.py                 # Application entry point, creates Flask app + blueprints
├── config.py               # Reads DB credentials/secret key from .env
├── requirements.txt
├── .env.example             # Copy to .env and fill in your MySQL details
├── models/                  # SQLAlchemy models (User, Exam, Question, StudentAnswer, Result)
├── routes/                  # Flask Blueprints: auth.py, student.py, admin.py
├── templates/                # Jinja2 + Bootstrap HTML pages
├── static/
│   ├── css/style.css
│   └── js/timer.js, exam_nav.js
└── utils/seed_admin.py       # Script to create the first admin account
```

## 1. Install Prerequisites
- Python 3.10+
- MySQL Server running locally (MySQL Workbench / XAMPP / standalone installer all work)

## 2. Set Up the Project (Windows PowerShell)
```powershell
cd Online-Exam-System
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Create the MySQL Database
Open MySQL command line or Workbench and run:
```sql
CREATE DATABASE exam_system;
```
That's it — tables are created automatically by the app on first run (via `db.create_all()`).

## 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Edit `.env` and fill in your real MySQL username/password:
```
SECRET_KEY=some-long-random-string
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
DB_NAME=exam_system
```

## 5. Run the App
```powershell
python app.py
```
Visit **http://127.0.0.1:5000** in your browser.

## 6. Create the First Admin Account
Since anyone who registers becomes a student by default, create the admin manually:
```powershell
python -m utils.seed_admin
```
Follow the prompts (name, email, password). Log in with those credentials to reach the Admin Dashboard.

## 7. Typical Usage Flow
1. Log in as admin → **Manage Exams → Create Exam** → add questions.
2. Register a new student account (or log out and register one).
3. Log in as that student → see the exam on the dashboard → take it → auto-graded result shown instantly.
4. Admin can view all results, search by student name, and see dashboard stats.

## 8. Deploying to the Cloud (Render example)
1. Push this project to a GitHub repo.
2. Provision a MySQL database in the cloud (Render's managed MySQL, Railway, Clever Cloud, or AWS RDS free tier all work).
3. On Render: New → Web Service → connect your repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
4. Add the same environment variables from `.env` (SECRET_KEY, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME) in Render's **Environment** tab, pointing at your cloud MySQL host instead of `localhost`.
5. Deploy. No code changes needed — only the `DB_HOST` env var changes from `localhost` to your cloud DB's host address.

## New Features

### 1. Tab-Switch Detection (Exam Integrity)
While a student is taking an exam, `static/js/proctor.js` listens for the browser's `visibilitychange` event (fires when the student switches tabs, minimizes, or alt-tabs away).
- 1st and 2nd switch: a warning banner appears on screen.
- 3rd switch: the exam is **auto-submitted immediately**.
- The `results` table stores `tab_switch_count` and `auto_submitted` for every attempt, visible to admins on the Results page (Clean / Flagged / Auto-submitted badges) and to the student on their own result page.

### 2. Analytics Dashboard (Admin → Analytics Dashboard)
Uses Chart.js (loaded from CDN, no install needed) to visualize:
- Overall pass/fail ratio (doughnut chart)
- Average score % per exam (bar chart)
- Question-level difficulty — % of students who got each question wrong (horizontal bar chart, filterable by exam)

All aggregation logic lives in `services/analytics_service.py`, kept separate from routes so it's easy to test or reuse.

### 3. Docker Support
`Dockerfile` + `docker-compose.yml` package the Flask app and a MySQL 8 container together, so the whole project runs with one command on any machine with Docker installed — no manual MySQL setup needed.

**To run with Docker:**
```powershell
docker compose up --build
```
This starts:
- `web` — the Flask app on **http://localhost:5000** (served by gunicorn, production-style)
- `db` — a MySQL 8 container on host port `3307` (mapped this way to avoid clashing with a MySQL you may already have running locally on 3306)

To create your admin account inside the container:
```powershell
docker compose exec web python -m utils.seed_admin
```

### 4. Auto-Calculated Total Marks
`total_marks` on an exam is no longer typed in manually — `Exam.recalculate_total_marks()` sums up the actual marks of its questions every time one is added, edited, or deleted. This makes the score-vs-total mismatch bug (e.g. showing `10/7`) structurally impossible.

### 5. Configurable Pass Percentage
Each exam has its own `pass_percentage` (default 40%), set when creating the exam, instead of a single hardcoded cutoff for every exam.

### 6. Student Profile Page
`/student/profile` shows an avatar, join date, exams taken, average %, pass count, and best score, plus an edit page to update name/password.

### 7. Landing Page + Visual Identity
Visiting `/` now shows a proper marketing-style landing page (hero section + feature cards) instead of redirecting straight to login. The whole UI uses a custom "graded paper" theme — ink-navy + gold accents, serif display type, an animated PASS/FAIL "stamp" on results, staggered fade-in animations on tables/cards, and animated count-up numbers on dashboard stats.

### 8. Automated Tests + CI Pipeline
`tests/test_app.py` is a pytest suite covering registration/login, exam creation, auto-calculated marks, full exam scoring, and the one-attempt-per-exam rule — all run against an in-memory SQLite DB (no MySQL server needed).

`.github/workflows/ci.yml` runs this test suite automatically on every push to GitHub, and also does a Docker build sanity check. This means every code change is verified automatically before it's considered "good" — a standard cloud/DevOps practice (Continuous Integration).

**To run tests locally:**
```powershell
pip install pytest
pytest tests/ -v
```

### 9. Basic Structured Logging
Every request now logs its method, path, and response status to stdout (`app.py`'s `log_request` hook). This is the standard logging pattern cloud platforms (Render, Railway, Docker) expect — their dashboards pick up stdout automatically as your app's logs, no extra configuration needed.

## ⚠️ Database Schema Update
Adding tab-switch tracking and configurable pass percentage added new columns (`tab_switch_count`, `auto_submitted` on `results`; `pass_percentage` on `exams`). If you already created your database before this update, either:
- **Easiest:** drop and recreate it, then re-run the app (tables regenerate automatically):
  ```sql
  DROP DATABASE exam_system;
  CREATE DATABASE exam_system;
  ```
  (You'll need to re-run `python -m utils.seed_admin` afterward.)
- **Or** manually add the columns without losing data:
  ```sql
  USE exam_system;
  ALTER TABLE results ADD COLUMN tab_switch_count INT NOT NULL DEFAULT 0;
  ALTER TABLE results ADD COLUMN auto_submitted BOOLEAN NOT NULL DEFAULT FALSE;
  ALTER TABLE exams ADD COLUMN pass_percentage INT NOT NULL DEFAULT 40;
  ```

## Notes for Your Internship Report
- Architecture follows MVC: `models/` (data), `templates/` (view), `routes/` (controller logic), `services/` (business logic/analytics kept separate from routes).
- Passwords are hashed with Werkzeug's `generate_password_hash` — never stored in plain text.
- Sessions are managed by Flask-Login; routes are protected with `@login_required` plus role checks (`admin_only()` / `student_only()`).
- Each student can attempt an exam only once (enforced at the route level by checking existing `Result` rows).
- Exam auto-submits via JavaScript countdown timer when time expires, or immediately upon repeated tab-switch violations (exam-integrity feature).
- The app is containerized with Docker, demonstrating a cloud-native deployment pattern (portable, reproducible environments) relevant to the cloud computing domain.
- MySQL password is URL-encoded in `config.py` to safely handle special characters (e.g. `@`) in credentials.
- Total marks are derived data (calculated from questions), not manually entered — a general "single source of truth" design principle.
- Automated tests + CI (GitHub Actions) demonstrate DevOps/cloud practices: every push is verified automatically before being considered deployable.
