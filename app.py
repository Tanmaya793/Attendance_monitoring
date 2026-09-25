import os
from flask import Flask, redirect, render_template, request
import pandas as pd
from sqlalchemy import text

from database import engine

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "attendance-monitor-dev")

STUDENT_FILE = "data/students.csv"
RATION_FILE = "data/ration.csv"


# ---------------------------------------------------------
# Initialize Attendance Table
# ---------------------------------------------------------

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
                    (:sid, 0, 0)
                """),
                {"sid": str(sid)}
            )


# ---------------------------------------------------------
# Home Page
# ---------------------------------------------------------

@app.route('/')
def home():

    return render_template('home.html')


# ---------------------------------------------------------
# Teacher Dashboard
# ---------------------------------------------------------

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():

    students = []
    selected_class = None

    students_df = pd.read_csv(STUDENT_FILE)

    attendance_df = pd.read_sql(
        text("""
            SELECT
                student_id AS "Student_ID",
                classes_held AS "Classes_Held",
                classes_attended AS "Classes_Attended"
            FROM attendance
        """),
        engine
    )

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


# ---------------------------------------------------------
# Submit Attendance
# ---------------------------------------------------------

@app.route('/submit_attendance', methods=['POST'])
def submit_attendance():

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
            if str(sid) in present_students:

                conn.execute(
                    text("""
                        UPDATE attendance
                        SET classes_attended = classes_attended + 1
                        WHERE student_id = :sid
                    """),
                    {"sid": sid}
                )

    return redirect('/teacher')


# ---------------------------------------------------------
# Panchayat Dashboard
# ---------------------------------------------------------

@app.route('/panchayat', methods=['GET', 'POST'])
def panchayat():

    students = []
    message = ""

    # -----------------------------------------------------
    # Load CSV files
    # -----------------------------------------------------

    students_df = pd.read_csv(STUDENT_FILE)
    ration_df = pd.read_csv(RATION_FILE)


    # -----------------------------------------------------
    # Get searched ration card number
    # -----------------------------------------------------

    if request.method == 'POST':

        ration_no = request.form.get(
            'ration_no',
            ''
        ).strip()

    else:

        ration_no = request.args.get(
            'ration_no',
            ''
        ).strip()


    # -----------------------------------------------------
    # Normalize ration card number
    #
    # Accepts:
    # 1001
    # RC1001
    # -----------------------------------------------------

    if ration_no:

        if not ration_no.upper().startswith('RC'):

            ration_no = 'RC' + ration_no

        ration_no = ration_no.upper()


    # -----------------------------------------------------
    # Create Ration Card Directory
    # -----------------------------------------------------

    ration_cards = []

    for ration_card, group in ration_df.groupby(
        'Ration_Card_No'
    ):

        ration_cards.append({

            'Ration_Card_No': ration_card,

            'Guardian_Name': group.iloc[0]['Guardian_Name'],

            'Student_Count': len(group)

        })


    # -----------------------------------------------------
    # Sort ration cards numerically
    # -----------------------------------------------------

    ration_cards = sorted(

        ration_cards,

        key=lambda x: int(
            str(x['Ration_Card_No'])
            .replace('RC', '')
        )

    )


    # -----------------------------------------------------
    # Filter directory when searching a ration card
    # -----------------------------------------------------

    if ration_no:

        ration_cards = [

            card

            for card in ration_cards

            if card['Ration_Card_No'] == ration_no

        ]


    # -----------------------------------------------------
    # Attendance lookup
    # -----------------------------------------------------

    if ration_no:

        attendance_df = pd.read_sql(
            text("""
                SELECT
                    student_id AS "Student_ID",
                    classes_held AS "Classes_Held",
                    classes_attended AS "Classes_Attended"
                FROM attendance
            """),
            engine
        )


        ration_results = ration_df[
            ration_df['Ration_Card_No'] == ration_no
        ]


        # -------------------------------------------------
        # Ration Card Found
        # -------------------------------------------------

        if not ration_results.empty:

            for _, row in ration_results.iterrows():

                student_name = row['Student_Name']


                # Find student information
                student_info = students_df[
                    students_df['Student_Name'] == student_name
                ]


                if not student_info.empty:

                    student_id = student_info.iloc[0]['Student_ID']


                    # Find attendance
                    attendance_info = attendance_df[
                        attendance_df['Student_ID'] == student_id
                    ]


                    held = 0
                    attended = 0


                    if not attendance_info.empty:

                        held = attendance_info.iloc[0][
                            'Classes_Held'
                        ]

                        attended = attendance_info.iloc[0][
                            'Classes_Attended'
                        ]


                    # Calculate percentage
                    percentage = 0

                    if held > 0:

                        percentage = round(
                            (attended / held) * 100,
                            2
                        )


                    # Create student result
                    student_data = {

                        'Student_Name': student_name,

                        'Class': student_info.iloc[0]['Class'],

                        'Attendance': percentage

                    }


                    # Attendance warning
                    if percentage < 75:

                        student_data['Warning'] = (
                            "⚠ Low Attendance"
                        )

                    else:

                        student_data['Warning'] = (
                            "✅ Good Attendance"
                        )


                    students.append(student_data)


        # -------------------------------------------------
        # Ration Card Not Found
        # -------------------------------------------------

        else:

            message = "Ration Card Not Found"


    # -----------------------------------------------------
    # Render Panchayat Dashboard
    # -----------------------------------------------------

    return render_template(

        'panchayat.html',

        students=students,

        message=message,

        ration_cards=ration_cards,

        searched_ration_no=ration_no

    )


# ---------------------------------------------------------
# Run Application
# ---------------------------------------------------------

if __name__ == '__main__':

    host = os.getenv(
        'HOST',
        '0.0.0.0'
    )

    port = int(
        os.getenv(
            'PORT',
            5000
        )
    )

    app.run(
        host=host,
        port=port,
        debug=False
    )

