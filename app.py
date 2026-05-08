from flask import Flask, render_template, request, redirect
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)

STUDENT_FILE = "data/students.csv"
RATION_FILE = "data/ration.csv"

# Current month attendance file
month_file = datetime.now().strftime("attendance_%Y_%m.csv")
ATTENDANCE_FILE = f"data/attendance/{month_file}"


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

    attendance_df = pd.read_csv(ATTENDANCE_FILE)

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

    attendance_df = pd.read_csv(ATTENDANCE_FILE)

    present_students = request.form.getlist('present')

    students_df = pd.read_csv(STUDENT_FILE)

    selected_class = request.form['selected_class']

    class_students = students_df[
        students_df['Class'].astype(str) == selected_class
    ]

    for _, student in class_students.iterrows():

        sid = student['Student_ID']

        # Increase total classes held
        attendance_df.loc[
            attendance_df['Student_ID'] == sid,
            'Classes_Held'
        ] += 1

        # If present increase attended
        if sid in present_students:

            attendance_df.loc[
                attendance_df['Student_ID'] == sid,
                'Classes_Attended'
            ] += 1

    attendance_df.to_csv(ATTENDANCE_FILE, index=False)

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
        attendance_df = pd.read_csv(ATTENDANCE_FILE)

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