"""
Timezone helpers for exam scheduling.

The database stores scheduled_start/scheduled_end as naive UTC datetimes
(consistent with datetime.utcnow() used everywhere else in this app). But
every HUMAN touchpoint — the admin typing a time into the schedule form,
and the message shown to students about when an exam opens — should be in
IST (Asia/Kolkata), since that's this college's timezone. Without this
conversion, a naive datetime-local value like "18:28" typed by an admin in
India got stored and compared as if it were 18:28 UTC, which is actually
23:58 IST — nearly 5.5 hours later than intended. This module is the single
place that conversion happens, so it can't drift out of sync between forms.

No DST in India, so a fixed offset is sufficient (no need for pytz/zoneinfo
database dependency).
"""
from datetime import datetime, timedelta

IST_OFFSET = timedelta(hours=5, minutes=30)


def ist_input_to_utc(value):
    """Parses an HTML <input type="datetime-local"> value
    ("YYYY-MM-DDTHH:MM"), TREATING IT AS IST (what the admin typed), and
    returns the equivalent naive UTC datetime for storage. Returns None if
    blank/invalid."""
    if not value:
        return None
    try:
        ist_naive = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None
    return ist_naive - IST_OFFSET


def utc_to_ist(value):
    """Converts a naive UTC datetime from the DB to naive IST, for display
    or for pre-filling a datetime-local form field. Returns None if value
    is None."""
    if value is None:
        return None
    return value + IST_OFFSET


def utc_now_as_ist():
    return utc_to_ist(datetime.utcnow())
