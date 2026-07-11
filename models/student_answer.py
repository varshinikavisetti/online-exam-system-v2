from models import db


class StudentAnswer(db.Model):
    __tablename__ = "student_answers"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    # Stores "A"/"B"/"C"/"D" for MCQ, "True"/"False" for True-False, or the
    # raw typed text for Fill-in-the-Blank answers.
    selected_option = db.Column(db.String(255), nullable=True)

    # Which attempt (1, 2, 3...) this answer belongs to, so a student can
    # retake an exam multiple times without answers from different attempts
    # getting mixed together.
    attempt_number = db.Column(db.Integer, nullable=False, default=1)
