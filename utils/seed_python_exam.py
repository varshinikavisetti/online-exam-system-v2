"""
One-time helper to create a sample "Python Coding Basics" exam with 5 questions.

Run with:  python -m utils.seed_python_exam
"""
from app import create_app
from models import db
from models.exam import Exam
from models.question import Question

app = create_app()

QUESTIONS = [
    {
        "question_text": "What is the output of print(type(5/2))?",
        "option_a": "<class 'int'>",
        "option_b": "<class 'float'>",
        "option_c": "<class 'double'>",
        "option_d": "<class 'str'>",
        "correct_option": "B",
        "marks": 2,
    },
    {
        "question_text": "Which keyword is used to define a function in Python?",
        "option_a": "func",
        "option_b": "define",
        "option_c": "def",
        "option_d": "function",
        "correct_option": "C",
        "marks": 2,
    },
    {
        "question_text": "What will len([1, 2, [3, 4], 5]) return?",
        "option_a": "5",
        "option_b": "4",
        "option_c": "3",
        "option_d": "Error",
        "correct_option": "B",
        "marks": 2,
    },
    {
        "question_text": "Which of these correctly creates a list in Python?",
        "option_a": "list = (1, 2, 3)",
        "option_b": "list = {1, 2, 3}",
        "option_c": "list = [1, 2, 3]",
        "option_d": "list = <1, 2, 3>",
        "correct_option": "C",
        "marks": 2,
    },
    {
        "question_text": "What does the range(5) function generate?",
        "option_a": "1 to 5",
        "option_b": "0 to 4",
        "option_c": "0 to 5",
        "option_d": "1 to 4",
        "correct_option": "B",
        "marks": 2,
    },
]

with app.app_context():
    existing = Exam.query.filter_by(title="Python Coding Basics").first()
    if existing:
        print("An exam called 'Python Coding Basics' already exists. Skipping.")
    else:
        total_marks = sum(q["marks"] for q in QUESTIONS)

        exam = Exam(
            title="Python Coding Basics",
            subject="Computer Science",
            duration=15,
            total_marks=total_marks,
        )
        db.session.add(exam)
        db.session.commit()  # commit so exam.id is generated

        for q in QUESTIONS:
            question = Question(exam_id=exam.id, **q)
            db.session.add(question)

        db.session.commit()
        print(f"Created exam '{exam.title}' with {len(QUESTIONS)} questions "
              f"({total_marks} total marks).")
