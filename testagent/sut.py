"""Example systems under test."""


def validate_age_correct(age):
    return 18 <= age <= 60


def validate_age_buggy(age):
    # Deliberate off-by-one bug: rejects exactly 18.
    return 18 < age <= 60
