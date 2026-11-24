"""Example systems under test: a correct version and a version with a planted bug."""


def validate_age_correct(age):
    return 18 <= age <= 60


def validate_age_buggy(age):
    # Deliberate off-by-one bug: rejects exactly 18.
    return 18 < age <= 60


def validate_name_length_correct(name):
    return 3 <= len(name) <= 20


def validate_name_length_buggy(name):
    # Deliberate off-by-one bug: rejects names of exactly 3 characters.
    return 3 < len(name) <= 20


def validate_status_correct(status):
    return status in ("NEW", "ACTIVE", "CLOSED")


def validate_status_buggy(status):
    # Deliberate bug: forgot to allow "CLOSED".
    return status in ("NEW", "ACTIVE")
