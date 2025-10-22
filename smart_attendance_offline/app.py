import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="face_recognition_models")

import os
import cv2
import numpy as np
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import face_recognition

# ---------------- Flask Setup ----------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# ---------------- Database Models ----------------
class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    students = db.relationship('Student', backref='classroom', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    photo_path = db.Column(db.String(200), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=True)

with app.app_context():
    #db.drop_all()
    db.create_all()

# ---------------- Routes ----------------

# Home Page
@app.route('/')
def index():
    classrooms = Classroom.query.all()
    return render_template('index.html', classrooms=classrooms)

# Manage Students
@app.route('/students')
def students():
    all_students = Student.query.all()
    classrooms = Classroom.query.all()
    return render_template('students.html', students=all_students, classrooms=classrooms)

# Add Student
@app.route('/add_student', methods=['POST'])
def add_student():
    name = request.form['name']
    file = request.files['photo']
    classroom_id = request.form.get('classroom_id')  # Get selected classroom

    if not name or not file:
        return redirect(url_for('students'))

    filename = file.filename
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    new_student = Student(
        name=name,
        photo_path=path,
        classroom_id=int(classroom_id) if classroom_id else None
    )
    db.session.add(new_student)
    db.session.commit()
    return redirect(url_for('students'))

# Delete Student
@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    student = Student.query.get_or_404(id)
    # Remove photo from disk
    if os.path.exists(student.photo_path):
        os.remove(student.photo_path)
    db.session.delete(student)
    db.session.commit()
    return redirect(url_for('students'))

# Attendance Page (placeholder)
@app.route('/attendance')
def attendance():
    return render_template('attendance.html')

@app.route('/upload_class_photo', methods=['POST'])
def upload_class_photo():
    file = request.files.get('class_photo')
    classroom_id = request.form.get('classroom_id')
    if not file or not classroom_id:
        return redirect(url_for('index'))

    # Save uploaded photo
    filename = file.filename
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    # Get the classroom object
    classroom = Classroom.query.get(int(classroom_id))

    # Get students in this classroom only
    students = Student.query.filter_by(classroom_id=int(classroom_id)).all()
    known_encodings = []
    known_names = []

    for student in students:
        student_image = face_recognition.load_image_file(student.photo_path)
        encodings = face_recognition.face_encodings(student_image)
        if encodings:
            known_encodings.append(encodings[0])
            known_names.append(student.name)

    class_image = face_recognition.load_image_file(path)
    face_locations = face_recognition.face_locations(class_image)
    face_encodings = face_recognition.face_encodings(class_image, face_locations)

    results = {s.name: False for s in students}

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
        if True in matches:
            match_index = matches.index(True)
            name = known_names[match_index]
            results[name] = True

    return render_template(
        'result.html',
        classroom_name=classroom.name,
        photo=url_for('static', filename=f'uploads/{filename}'),
        results=results
    )


# ---------------- Optional Classroom Management ----------------
# Add Classroom (for creating new classrooms from a form)
@app.route('/add_classroom', methods=['POST'])
def add_classroom():
    name = request.form['name']
    if name:
        new_class = Classroom(name=name)
        db.session.add(new_class)
        db.session.commit()
    return redirect(url_for('students'))  # redirect back to students page

# Delete Classroom
@app.route('/delete_classroom/<int:id>', methods=['POST'])
def delete_classroom(id):
    classroom = Classroom.query.get_or_404(id)
    db.session.delete(classroom)
    db.session.commit()
    return redirect(url_for('students'))

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True)
