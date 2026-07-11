from datetime import datetime
from models import db


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Integer, nullable=False, default=0)
    pass_percentage = db.Column(db.Integer, nullable=False, default=40)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ---- New exam configuration options ----
    negative_marking_enabled = db.Column(db.Boolean, nullable=False, default=False)
    # Marks deducted for each wrong answer, e.g. 0.25 -> quarter mark cut per wrong answer.
    negative_marks_value = db.Column(db.Float, nullable=False, default=0)

    shuffle_questions = db.Column(db.Boolean, nullable=False, default=False)
    shuffle_options = db.Column(db.Boolean, nullable=False, default=False)

    # How many times a student may attempt this exam. 1 = old behaviour.
    max_attempts = db.Column(db.Integer, nullable=False, default=1)

    # Whether students can see their result immediately after submitting.
    show_results = db.Column(db.Boolean, nullable=False, default=True)

    # Draft exams (unpublished) are hidden from students entirely.
    is_published = db.Column(db.Boolean, nullable=False, default=True)

    # Minimum minutes that must elapse before a student is allowed to submit.
    # Submitting earlier than this doesn't block the submission, but it is
    # flagged for the admin as a possible integrity violation.
    min_submit_minutes = db.Column(db.Integer, nullable=False, default=0)

    # Whether webcam-based proctoring (face presence / phone detection) is
    # required for this exam.
    webcam_proctoring_enabled = db.Column(db.Boolean, nullable=False, default=False)

    # Scheduling: if set, students can't start the exam before/after this
    # window even though it's published. Null means "no schedule" (always
    # open while published), preserving old behaviour for existing exams.
    scheduled_start = db.Column(db.DateTime, nullable=True)
    scheduled_end = db.Column(db.DateTime, nullable=True)

    questions = db.relationship(
        "Question", backref="exam", lazy=True, cascade="all, delete-orphan"
    )
    # cascade="all, delete-orphan" so deleting an exam also deletes its
    # questions/results at the ORM level instead of hitting a FK constraint
    # error from MySQL (this, plus Question.student_answers in
    # models/question.py, was the cause of "delete exam doesn't work" —
    # every StudentAnswer belongs to a Question, so cascading through
    # Question fully covers answer cleanup too; no separate relationship
    # needed here for that).
    results = db.relationship(
        "Result", backref="exam", lazy=True, cascade="all, delete-orphan"
    )

    def is_open_for_attempt(self):
        """True if right now falls inside this exam's scheduled window
        (or the exam has no schedule set at all)."""
        now = datetime.utcnow()
        if self.scheduled_start and now < self.scheduled_start:
            return False
        if self.scheduled_end and now > self.scheduled_end:
            return False
        return True

    def question_count(self):
        return len(self.questions)

    def recalculate_total_marks(self):
        """Keep total_marks in sync with the actual sum of question marks.
        Called automatically whenever a question is added, edited, or deleted."""
        self.total_marks = sum(q.marks for q in self.questions)
