from datetime import date, datetime

from scripts.cleaning import clean_amount, clean_category, clean_date


def test_categories_ignore_case_spaces_and_known_variants():
    assert clean_category(" MOTOR ", "product") == "Motor"
    assert clean_category("rejected", "status") == "Rejected"
    assert clean_category("Esch/Alzette", "canton") == "Esch-sur-Alzette"
    assert clean_category("Luxemburg", "canton") == "Luxembourg"


def test_unknown_category_is_not_guessed():
    assert clean_category("Paris", "canton") is None


def test_dates_are_read_day_first():
    assert clean_date("03/04/2024") == date(2024, 4, 3)
    assert clean_date("03.04.2024") == date(2024, 4, 3)
    assert clean_date("2024-04-03") == date(2024, 4, 3)
    assert clean_date(datetime(2024, 4, 3, 0, 0)) == date(2024, 4, 3)
    assert clean_date("not a date") is None


def test_amounts_in_european_and_english_formats():
    assert clean_amount("1.234,56 €") == 1234.56
    assert clean_amount("EUR 1,234.56") == 1234.56
    assert clean_amount("572,10") == 572.10
    assert clean_amount(99.5) == 99.5
    assert clean_amount(None) is None
