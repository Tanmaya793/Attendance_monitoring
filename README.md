# Attendance Monitoring System

A Flask-based attendance tracking system for teachers and panchayat staff.

## Local setup

1. Create a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the sample environment file:
   ```bash
   copy .env.example .env
   ```
4. Start the app:
   ```bash
   python app.py
   ```
5. Open the app in a browser at:
   http://127.0.0.1:5000

## Deployment

This project is ready for deployment with Gunicorn.

Use the following commands on a hosting platform:

```bash
gunicorn wsgi:app
```

### Recommended production setup

- Set `DATABASE_URL` to a managed Postgres database URL.
- Set `SECRET_KEY` to a strong random value.
- Keep `HOST=0.0.0.0` and `PORT=5000` for server platforms.

### Example deployment platforms

- Render
- Railway
- Fly.io
- Heroku

For those platforms, deploy the repository as a Python web app and set the environment variables from `.env.example`.

## Project flow

- Teacher dashboard: mark attendance by class
- Panchayat dashboard: lookup student attendance using ration card number
- Data is stored in SQLite by default for local development and can be replaced with Postgres for production