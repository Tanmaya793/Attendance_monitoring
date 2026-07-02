from flask import Flask, render_template, request, redirect
import pandas as pd
from datetime import datetime, timedelta
import os
from database import engine
from sqlalchemy import text

app = Flask(__name__)

STUDENT_FILE = "data/students.csv"
RATION_FILE = "data/ration.csv"


with engine.begin() as conn:

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS attendance (

            student_id VARCHAR(20) PRIMARY KEY,
            classes_held INTEGER DEFAULT 0,
            classes_attended INTEGER DEFAULT 0

        )
    """))

    count = conn.execute(
        text("SELECT COUNT(*) FROM attendance")
    ).scalar()

    if count == 0:

        students = pd.read_csv(STUDENT_FILE)

        for sid in students["Student_ID"]:

            conn.execute(
                text("""
                    INSERT INTO attendance
                    (student_id, classes_held, classes_attended)

                    VALUES
                    (:sid,0,0)
                """),
                {"sid": sid}
            )

# Home Page
@app.route('/')
def home():
    return render_template('home.html')


# Teacher Dashboard
@app.route('/teacher', methods=['GET', 'POST'])
def teacher():

    students = []
    selected_class = None

    students_df = pd.read_csv(STUDENT_FILE)

    attendance_df = pd.read_sql(text("""
    SELECT
        student_id AS "Student_ID",
        classes_held AS "Classes_Held",
        classes_attended AS "Classes_Attended"
    FROM attendance
    """), engine)

    classes = sorted(students_df['Class'].unique())

    if request.method == 'POST':

        selected_class = request.form['class']

        class_students = students_df[
            students_df['Class'].astype(str) == selected_class
        ]

        for _, student in class_students.iterrows():

            sid = student['Student_ID']

            attendance_info = attendance_df[
                attendance_df['Student_ID'] == sid
            ]

            held = 0
            attended = 0
            percentage = 0

            if not attendance_info.empty:

                held = attendance_info.iloc[0]['Classes_Held']
                attended = attendance_info.iloc[0]['Classes_Attended']

                if held > 0:
                    percentage = round(
                        (attended / held) * 100,
                        2
                    )

            students.append({
                'Student_ID': sid,
                'Student_Name': student['Student_Name'],
                'Classes_Held': held,
                'Classes_Attended': attended,
                'Attendance_Percentage': percentage
            })

    return render_template(
        'teacher.html',
        classes=classes,
        students=students,
        selected_class=selected_class
    )

# Submit Attendance
@app.route('/submit_attendance', methods=['POST'])
def submit_attendance():

    conn = engine.connect()

    present_students = request.form.getlist('present')

    students_df = pd.read_csv(STUDENT_FILE)

    selected_class = request.form['selected_class']

    class_students = students_df[
        students_df['Class'].astype(str) == selected_class
    ]

    with engine.begin() as conn:

        for _, student in class_students.iterrows():
        
            sid = student['Student_ID']

            # Increase total classes held
            conn.execute(
                text("""
                    UPDATE attendance
                    SET classes_held = classes_held + 1
                    WHERE student_id = :sid
                """),
                {"sid": sid}
            )

            # Increase attended if present
            if sid in present_students:

                conn.execute(
                    text("""
                        UPDATE attendance
                        SET classes_attended = classes_attended + 1
                        WHERE student_id = :sid
                    """),
                    {"sid": sid}
                )

    return redirect('/teacher')


# Panchayat Dashboard
@app.route('/panchayat', methods=['GET', 'POST'])
def panchayat():

    students = []
    message = ""

    if request.method == 'POST':

        ration_no = request.form['ration_no']
        ration_no = "RC"+ration_no

        students_df = pd.read_csv(STUDENT_FILE)
        ration_df = pd.read_csv(RATION_FILE)
        attendance_df = pd.read_sql(text("""
        SELECT
            student_id AS "Student_ID",
            classes_held AS "Classes_Held",
            classes_attended AS "Classes_Attended"
        FROM attendance
        """), engine)

        ration_results = ration_df[
            ration_df['Ration_Card_No'] == ration_no
        ]

        if not ration_results.empty:

            for _, row in ration_results.iterrows():

                student_name = row['Student_Name']

                student_info = students_df[
                    students_df['Student_Name'] == student_name
                ]

                if not student_info.empty:

                    student_id = student_info.iloc[0]['Student_ID']

                    attendance_info = attendance_df[
                        attendance_df['Student_ID'] == student_id
                    ]

                    if not attendance_info.empty:

                        held = attendance_info.iloc[0]['Classes_Held']
                        attended = attendance_info.iloc[0]['Classes_Attended']

                        percentage = 0

                        if held > 0:
                            percentage = round(
                                (attended / held) * 100,
                                2
                            )

                        student_data = {
                            'Student_Name': student_name,
                            'Class': student_info.iloc[0]['Class'],
                            'Attendance': percentage
                        }

                        if percentage < 75:
                            student_data['Warning'] = "⚠ Low Attendance"
                        else:
                            student_data['Warning'] = "✅ Good Attendance"

                        students.append(student_data)

        else:
            message = "Ration Card Not Found"

    return render_template(
        'panchayat.html',
        students=students,
        message=message
    )


if __name__ == '__main__':
    app.run(debug=True)
