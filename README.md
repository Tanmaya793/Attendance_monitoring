# Attendance Monitoring System

A Flask-based attendance monitoring web application for rural schools.

The application provides:

- Teacher dashboard for selecting a class and viewing attendance.
- Class-wise attendance marking.
- Automatic calculation of attendance percentage.
- Panchayat dashboard for ration-card based student lookup.
- Attendance warning when a student's attendance is below 75%.
- SQLite for local development.
- PostgreSQL support for production deployment.
- Gunicorn WSGI deployment.
- Render deployment configuration through `render.yaml`.
- Health-check endpoint at `/health`.

## Project structure

```text
Attendance_monitoring/
├── app.py
├── database.py
├── wsgi.py
├── init_db.py
├── requirements.txt
├── Procfile
├── render.yaml
├── .env.example
├── .gitignore
├── README.md
│
├── data/
│   ├── students.csv
│   └── ration.csv
│
├── static/
└── templates/
```

## Requirements

- Python 3.11+ recommended
- pip
- Git
- PostgreSQL only when running with PostgreSQL

The application is designed to work locally without a `DATABASE_URL`. When that variable is not set, it automatically uses:

```text
attendance.db
```

inside the project directory.

## 1. Clone the repository

```bash
git clone https://github.com/Tanmaya793/Attendance_monitoring.git
cd Attendance_monitoring
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configure environment variables

Copy the example file.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### Linux/macOS

```bash
cp .env.example .env
```

For local SQLite development, you can leave `DATABASE_URL` empty.

Example:

```env
DATABASE_URL=
SECRET_KEY=replace-this-with-a-random-secret
HOST=127.0.0.1
PORT=5000
LOG_LEVEL=INFO
```

Do not commit `.env` to Git.

## 5. Run locally

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

Available pages:

```text
/             Home page
/teacher      Teacher dashboard
/panchayat    Panchayat dashboard
/health       Application/database health check
```

## 6. Test with Gunicorn locally

After installing dependencies:

```bash
gunicorn wsgi:app
```

On Windows, Gunicorn itself is generally used in Linux-based production environments. For Windows development, use:

```bash
python app.py
```

The WSGI entry point is:

```python
from app import app
```

Therefore the production command is:

```bash
gunicorn wsgi:app
```

## Database configuration

### Local development

No `DATABASE_URL` is required.

The application automatically uses:

```text
sqlite:///attendance.db
```

The SQLite database is intentionally ignored by Git.

### PostgreSQL production

Set:

```env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DATABASE
```

The application also normalizes legacy `postgres://` URLs automatically.

SQLAlchemy uses connection pre-pinging in production to reduce failures caused by stale database connections.

## Attendance workflow

### Teacher

1. Open `/teacher`.
2. Select a class.
3. View the students in that class.
4. Mark students who are present.
5. Submit attendance.
6. The application increments `classes_held` for every student in the selected class.
7. It increments `classes_attended` only for students marked present.
8. Attendance percentage is calculated as:

```text
(classes_attended / classes_held) × 100
```

### Panchayat

1. Open `/panchayat`.
2. Enter the ration-card number.
3. The application looks up students associated with that ration card.
4. Their attendance percentage is displayed.
5. Attendance below 75% is shown with a warning.

## Production deployment on Render

This repository includes `render.yaml`, which can be used as a Render Blueprint.

### Option A — Blueprint deployment

1. Push the latest project files to GitHub.
2. Open Render.
3. Create a new Blueprint.
4. Select the GitHub repository.
5. Render reads `render.yaml`.
6. The Blueprint creates:
   - A Python web service.
   - A PostgreSQL database.
   - `DATABASE_URL` linked to the PostgreSQL database.
   - A generated `SECRET_KEY`.
7. Start the deployment.
8. Wait for the build and deploy to complete.
9. Open the public Render URL.

The web service uses:

```bash
pip install -r requirements.txt
```

for the build and:

```bash
gunicorn --workers 2 --threads 4 --timeout 120 wsgi:app
```

to start the application.

### Option B — Manual Render deployment

Create a new **Web Service** and connect this GitHub repository.

Use:

```text
Language:
Python 3

Build Command:
pip install -r requirements.txt

Start Command:
gunicorn --workers 2 --threads 4 --timeout 120 wsgi:app
```

Set these environment variables:

```text
DATABASE_URL=<Render PostgreSQL connection string>
SECRET_KEY=<long random secret>
HOST=0.0.0.0
PORT=10000
LOG_LEVEL=INFO
```

Then deploy.

Render provides a public `onrender.com` URL after a successful deployment.

## Render PostgreSQL

Create a PostgreSQL database in Render and connect the web service to it.

The application expects:

```text
DATABASE_URL
```

For example:

```text
postgresql+psycopg2://username:password@hostname:5432/database
```

Do not put the real database URL in GitHub.

## Render health check

The application exposes:

```text
GET /health
```

A successful database connection returns:

```json
{
  "status": "ok"
}
```

If the database cannot be reached, the endpoint returns HTTP 503.

Render uses this endpoint in `render.yaml`:

```yaml
healthCheckPath: /health
```

## Security configuration

Production secrets should be supplied through the hosting platform rather than committed to the repository.

Required production configuration:

```text
SECRET_KEY
DATABASE_URL
```

The application also enables:

- HTTP-only session cookies.
- SameSite `Lax` cookies.
- Secure cookies when running on Render.
- SQLAlchemy parameterized SQL queries.
- Environment-based configuration.
- Production WSGI server through Gunicorn.

### Important application-security note

The current application does not implement user authentication or role-based authorization. The teacher and panchayat dashboards are application routes rather than authenticated accounts.

If this application is going to be used with real student information, authentication, authorization, CSRF protection, audit logging, and stronger privacy controls should be added before real-world use.

## Data files

The application expects:

```text
data/students.csv
data/ration.csv
```

`students.csv` contains the student master data.

`ration.csv` maps ration-card numbers to students.

These files are treated as application reference data and are expected to be committed with the project.

## Production filesystem note

Render web services use an ephemeral filesystem by default. Do not use local SQLite as the production database if attendance records need to survive redeployments.

Use Render PostgreSQL for production attendance data.

The local `attendance.db` file is intended for development/testing only.

## Troubleshooting

### `ModuleNotFoundError`

Activate the virtual environment and run:

```bash
pip install -r requirements.txt
```

### `DATABASE_URL` missing

This is not an error for local development.

If `DATABASE_URL` is not set, the application automatically falls back to SQLite.

### PostgreSQL connection error

Check:

```text
DATABASE_URL
```

and verify that the PostgreSQL database is running and accessible.

### `students.csv` not found

Make sure the repository contains:

```text
data/students.csv
```

and that the application is being started from the project root.

### Render build failure

Check the Render build logs and verify:

```bash
pip install -r requirements.txt
```

works locally.

### Render application crash

Check the deploy logs and verify that:

```bash
gunicorn wsgi:app
```

starts successfully.

Also check that `DATABASE_URL` and `SECRET_KEY` are configured.

## Production checklist

Before deployment:

- [ ] Push all code to GitHub.
- [ ] Remove `__pycache__` from Git.
- [ ] Do not commit `.env`.
- [ ] Keep `.env.example` only as a template.
- [ ] Verify `data/students.csv`.
- [ ] Verify `data/ration.csv`.
- [ ] Test `python app.py` locally.
- [ ] Test `/teacher`.
- [ ] Test `/panchayat`.
- [ ] Test `/health`.
- [ ] Verify `gunicorn wsgi:app`.
- [ ] Create PostgreSQL for production.
- [ ] Set a strong `SECRET_KEY`.
- [ ] Deploy to Render.
- [ ] Test the public URL.
- [ ] Test attendance submission against PostgreSQL.
- [ ] Test ration-card lookup against PostgreSQL.

## Technology stack

- **Python** — application programming language
- **Flask** — web framework
- **SQLAlchemy** — database access
- **SQLite** — local development database
- **PostgreSQL** — production database
- **Pandas** — CSV data processing
- **Gunicorn** — production WSGI server
- **python-dotenv** — local environment configuration
- **HTML/CSS** — user interface

## License

This project is intended for academic/project use.
