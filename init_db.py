import pandas as pd
from sqlalchemy import text

from database import engine

students = pd.read_csv("data/students.csv")

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS attendance (
            student_id VARCHAR(20) PRIMARY KEY,
            classes_held INTEGER DEFAULT 0,
            classes_attended INTEGER DEFAULT 0
        )
    """))

    for sid in students["Student_ID"]:
        conn.execute(
            text("""
                INSERT INTO attendance (student_id, classes_held, classes_attended)
                VALUES (:sid, 0, 0)
                ON CONFLICT (student_id) DO NOTHING
            """),
            {"sid": str(sid)}
        )
