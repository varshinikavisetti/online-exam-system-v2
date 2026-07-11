from datetime import datetime
from models import db


class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    # Float rather than Integer because negative marking can produce
    # fractional scores (e.g. -0.25 per wrong answer).
    score = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    passed = db.Column(db.Boolean, nullable=False, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    attempt_number = db.Column(db.Integer, nullable=False, default=1)

    # Proctoring / exam-integrity fields
    tab_switch_count = db.Column(db.Integer, nullable=False, default=0)
    auto_submitted = db.Column(db.Boolean, nullable=False, default=False)

    # True if the exam was force-terminated for an integrity violation
    # (webcam proctoring failure, tab-switch limit, or submitting before the
    # configured minimum time).
    terminated = db.Column(db.Boolean, nullable=False, default=False)

    # "tab_switch_limit" | "phone_or_object_detected" | "no_face_detected"
    # | "submitted_too_early" | None
    termination_reason = db.Column(db.String(50), nullable=True)

    def is_flagged(self):
        """True if the exam had any tab-switch or proctoring issue."""
        return self.tab_switch_count > 0 or self.terminated

