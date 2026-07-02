import pandas as pd
from database import engine

students = pd.read_csv("data/students.csv")

with engine.begin() as conn:

    conn.exec_driver_sql("""

    CREATE TABLE IF NOT EXISTS attendance (

        student_id VARCHAR(20) PRIMARY KEY,
        classes_held INTEGER DEFAULT 0,
        classes_attended INTEGER DEFAULT 0

    )

    """)

    for sid in students["Student_ID"]:

        conn.exec_driver_sql("""

        INSERT INTO attendance(student_id)

        VALUES (%s)

        ON CONFLICT (student_id) DO NOTHING

        """,(sid,))