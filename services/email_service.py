"""
Email notifications for exams — used for "take this exam on time" reminders.

Uses Flask-Mail, configured from environment variables (see config.py):
  MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD,
  MAIL_DEFAULT_SENDER

If mail isn't configured (MAIL_SERVER unset), sending is skipped and a
clear message is returned instead of raising — so the rest of the app
(exam creation, etc.) never breaks just because SMTP isn't set up yet.
"""
import logging
from flask import current_app
from flask_mail import Message
from extensions import mail
from utils.timezone_helper import utc_to_ist

logger = logging.getLogger("exam_system")


def _mail_is_configured():
    return bool(current_app.config.get("MAIL_SERVER"))


def send_exam_notification_to_students(exam, students, extra_note=""):
    """
    Emails every student in `students` about `exam` (new exam / reminder /
    schedule). Returns (sent_count, error_message_or_None).
    Sends one-by-one with per-recipient error handling so one bad address
    doesn't stop the rest of the batch.
    """
    if not _mail_is_configured():
        return 0, (
            "Email is not configured on this server yet (MAIL_SERVER is unset). "
            "Set the MAIL_* environment variables to enable notifications."
        )

    schedule_line = ""
    if exam.scheduled_start:
        start_ist = utc_to_ist(exam.scheduled_start)
        schedule_line = f"\nScheduled window: {start_ist.strftime('%d %b %Y, %I:%M %p')}"
        if exam.scheduled_end:
            end_ist = utc_to_ist(exam.scheduled_end)
            schedule_line += f" to {end_ist.strftime('%d %b %Y, %I:%M %p')}"
        schedule_line += " IST"

    sent = 0
    for student in students:
        if not student.email:
            continue
        try:
            msg = Message(
                subject=f"Exam reminder: {exam.title}",
                recipients=[student.email],
                body=(
                    f"Hi {student.name},\n\n"
                    f"This is a reminder for the exam \"{exam.title}\" ({exam.subject}).\n"
                    f"Duration: {exam.duration} minutes."
                    f"{schedule_line}\n\n"
                    f"{extra_note}\n\n"
                    "Please log in and complete it on time.\n\n"
                    "— Online Examination System"
                ),
            )
            mail.send(msg)
            sent += 1
        except Exception as exc:
            logger.warning("Failed to email %s about exam %s: %s", student.email, exam.id, exc)

    return sent, None
