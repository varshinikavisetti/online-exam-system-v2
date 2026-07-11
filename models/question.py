from models import db


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)

    # "mcq" | "true_false" | "fill_blank"
    question_type = db.Column(db.String(20), nullable=False, default="mcq")

    question_text = db.Column(db.Text, nullable=False)

    # Only used for question_type == "mcq". Nullable so True/False and
    # Fill-in-the-Blank questions don't need to fill these in.
    option_a = db.Column(db.String(255), nullable=True)
    option_b = db.Column(db.String(255), nullable=True)
    option_c = db.Column(db.String(255), nullable=True)
    option_d = db.Column(db.String(255), nullable=True)

    # For "mcq": "A"/"B"/"C"/"D". For "true_false": "True"/"False".
    correct_option = db.Column(db.String(10), nullable=True)

    # For "fill_blank": the accepted correct answer text (matched
    # case-insensitively, whitespace-trimmed).
    correct_text = db.Column(db.String(255), nullable=True)

    marks = db.Column(db.Integer, nullable=False, default=1)

    # The FK gap that caused "Cannot delete or update a parent row... questions"
    # on exam delete: StudentAnswer references BOTH exam_id AND question_id.
    # Exam.questions (cascade) deletes the Question rows, but nothing was
    # telling SQLAlchemy to delete the StudentAnswer rows that still point
    # at those Question ids first, so MySQL's FK constraint on
    # student_answers.question_id rejected the DELETE. This relationship
    # closes that gap: deleting a Question now cascades to its answers too.
    student_answers = db.relationship(
        "StudentAnswer", backref="question", lazy=True, cascade="all, delete-orphan"
    )

    def options(self):
        if self.question_type == "true_false":
            return {"True": "True", "False": "False"}
        if self.question_type == "fill_blank":
            return {}
        return {
            "A": self.option_a,
            "B": self.option_b,
            "C": self.option_c,
            "D": self.option_d,
        }

    def is_correct(self, submitted_value):
        """Check a submitted answer against this question's correct answer."""
        if submitted_value is None:
            return False

        if self.question_type == "fill_blank":
            if not self.correct_text:
                return False
            return submitted_value.strip().lower() == self.correct_text.strip().lower()

        # mcq / true_false both compare against correct_option
        return submitted_value == self.correct_option
