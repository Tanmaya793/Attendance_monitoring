import logging
import os
from pathlib import Path

import pandas as pd
from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy import text

from database import engine

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STUDENT_FILE = DATA_DIR / "students.csv"
RATION_FILE = DATA_DIR / "ration.csv"

app = Flask(__name__)

# Development fallback keeps the app usable on a fresh machine.
# Set SECRET_KEY in production through the hosting platform.
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("RENDER", "").lower() == "true",
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def load_students():
    """Load the static student master data."""
    return pd.read_csv(STUDENT_FILE, encoding="utf-8-sig", dtype={"Student_ID": str})


def load_ration_data():
    """Load the static ration-card mapping data."""
    return pd.read_csv(RATION_FILE, encoding="utf-8-sig", dtype={"Ration_Card_No": str})


def initialize_database():
    """Create the attendance table and seed missing student records."""
    if not STUDENT_FILE.exists():
        raise FileNotFoundError(f"Required data file not found: {STUDENT_FILE}")

    students_df = load_students()

    required_columns = {"Student_ID", "Student_Name", "Class"}
    missing = required_columns - set(students_df.columns)
    if missing:
        raise ValueError(
            f"students.csv is missing required columns: {', '.join(sorted(missing))}"
        )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS attendance (
                    student_id VARCHAR(20) PRIMARY KEY,
                    classes_held INTEGER NOT NULL DEFAULT 0,
                    classes_attended INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )

        existing_ids = {
            str(row[0])
            for row in conn.execute(text("SELECT student_id FROM attendance")).fetchall()
        }

        for sid in students_df["Student_ID"].dropna().astype(str):
            if sid not in existing_ids:
                conn.execute(
                    text(
                        """
                        INSERT INTO attendance
                            (student_id, classes_held, classes_attended)
                        VALUES
                            (:sid, 0, 0)
                        """
                    ),
                    {"sid": sid},
                )


def get_attendance_map():
    """Return attendance rows keyed by student ID."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT student_id, classes_held, classes_attended
                FROM attendance
                """
            )
        ).mappings().all()

    return {
        str(row["student_id"]): {
            "Classes_Held": int(row["classes_held"] or 0),
            "Classes_Attended": int(row["classes_attended"] or 0),
        }
        for row in rows
    }


# Initialize once when the application module is loaded by Gunicorn.
initialize_database()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/teacher", methods=["GET", "POST"])
def teacher():
    students = []
    selected_class = None

    students_df = load_students()
    attendance_map = get_attendance_map()

    classes = sorted(
        students_df["Class"].dropna().astype(str).unique(),
        key=lambda value: (len(value), value),
    )

    if request.method == "POST":
        selected_class = request.form.get("class", "").strip()

        class_students = students_df[
            students_df["Class"].astype(str) == selected_class
        ]

        for _, student in class_students.iterrows():
            sid = str(student["Student_ID"])
            attendance_info = attendance_map.get(
                sid, {"Classes_Held": 0, "Classes_Attended": 0}
            )

            held = attendance_info["Classes_Held"]
            attended = attendance_info["Classes_Attended"]
            percentage = round((attended / held) * 100, 2) if held else 0

            students.append(
                {
                    "Student_ID": sid,
                    "Student_Name": student["Student_Name"],
                    "Classes_Held": held,
                    "Classes_Attended": attended,
                    "Attendance_Percentage": percentage,
                }
            )

    return render_template(
        "teacher.html",
        classes=classes,
        students=students,
        selected_class=selected_class,
    )


@app.route("/submit_attendance", methods=["POST"])
def submit_attendance():
    present_students = set(request.form.getlist("present"))
    selected_class = request.form.get("selected_class", "").strip()

    if not selected_class:
        return redirect(url_for("teacher"))

    students_df = load_students()
    class_students = students_df[
        students_df["Class"].astype(str) == selected_class
    ]

    with engine.begin() as conn:
        for _, student in class_students.iterrows():
            sid = str(student["Student_ID"])

            # Every submission represents one class held.
            conn.execute(
                text(
                    """
                    UPDATE attendance
                    SET classes_held = classes_held + 1
                    WHERE student_id = :sid
                    """
                ),
                {"sid": sid},
            )

            # Only checked/present students receive an attendance increment.
            if sid in present_students:
                conn.execute(
                    text(
                        """
                        UPDATE attendance
                        SET classes_attended = classes_attended + 1
                        WHERE student_id = :sid
                        """
                    ),
                    {"sid": sid},
                )

    return redirect(url_for("teacher", **{"class": selected_class}))


@app.route("/panchayat", methods=["GET", "POST"])
def panchayat():
    students = []
    message = ""

    if request.method == "POST":
        raw_ration_no = request.form.get("ration_no", "").strip().upper()

        if raw_ration_no.startswith("RC"):
            ration_no = raw_ration_no
        else:
            ration_no = f"RC{raw_ration_no}"

        students_df = load_students()
        ration_df = load_ration_data()
        attendance_map = get_attendance_map()

        ration_results = ration_df[
            ration_df["Ration_Card_No"].astype(str).str.upper() == ration_no
        ]

        if not ration_results.empty:
            for _, row in ration_results.iterrows():
                student_name = str(row["Student_Name"])

                student_info = students_df[
                    students_df["Student_Name"].astype(str) == student_name
                ]

                if student_info.empty:
                    continue

                student_row = student_info.iloc[0]
                student_id = str(student_row["Student_ID"])

                attendance_info = attendance_map.get(
                    student_id, {"Classes_Held": 0, "Classes_Attended": 0}
                )

                held = attendance_info["Classes_Held"]
                attended = attendance_info["Classes_Attended"]
                percentage = round((attended / held) * 100, 2) if held else 0

                students.append(
                    {
                        "Student_Name": student_name,
                        "Class": student_row["Class"],
                        "Attendance": percentage,
                        "Warning": (
                            "⚠ Low Attendance"
                            if percentage < 75
                            else "✅ Good Attendance"
                        ),
                    }
                )
        else:
            message = "Ration Card Not Found"

    return render_template(
        "panchayat.html",
        students=students,
        message=message,
    )


@app.get("/health")
def health():
    """Simple health endpoint for hosting-platform health checks."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}, 200
    except Exception:
        logger.exception("Health check failed")
        return {"status": "error"}, 503


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port, debug=False)
