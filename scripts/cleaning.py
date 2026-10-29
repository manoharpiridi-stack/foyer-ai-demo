"""Clean the claims Excel file before loading it, and report every fix (data/data_quality.json)."""

from datetime import date, datetime

import pandas as pd

ALLOWED = {
    "product": ["Home", "Motor", "Liability"],
    "status": ["Open", "Paid", "Rejected"],
    "channel": ["Agent", "Online", "Broker"],
    "canton": [
        "Capellen", "Clervaux", "Diekirch", "Echternach", "Esch-sur-Alzette", "Grevenmacher",
        "Luxembourg", "Mersch", "Redange", "Remich", "Vianden", "Wiltz",
    ],
}

# Spellings seen in the file that don't match after trimming spaces and ignoring case
ALIASES = {
    "esch/alzette": "Esch-sur-Alzette",
    "esch sur alzette": "Esch-sur-Alzette",
    "luxemburg": "Luxembourg",
    "lux-ville": "Luxembourg",
    "grevenmaacher": "Grevenmacher",
}

# Luxembourg data: 03/04/2024 means 3 April (day first), never 4 March.
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"]


def simplify(text) -> str:
    return " ".join(str(text).strip().lower().split())


def clean_category(value, column: str):
    for name in ALLOWED[column]:
        if simplify(name) == simplify(value):
            return name
    return ALIASES.get(simplify(value))  # None if unknown


def clean_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(str(value).strip(), date_format).date()
        except ValueError:
            continue
    return None


def clean_amount(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("€", "").replace("EUR", "").replace(" ", "")
    if "," in text and text.rfind(",") > text.rfind("."):
        text = text.replace(".", "").replace(",", ".")  # European format: 1.234,56
    else:
        text = text.replace(",", "")  # English format: 1,234.56
    try:
        return float(text)
    except ValueError:
        return None


def count_changed(before: list, after: list) -> int:
    return sum(1 for old, new in zip(before, after) if new is not None and new != old)


def clean_claims(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows_read = len(df)
    fixes = []

    df = df.drop_duplicates(subset="claim_id").copy()
    fixes.append({"issue": "Duplicate claims (same claim_id twice)", "rows": rows_read - len(df), "fix": "Kept the first copy"})

    for column in ["product", "status", "channel", "canton"]:
        before = list(df[column])
        df[column] = [clean_category(value, column) for value in before]
        fixes.append({
            "issue": f"Inconsistent {column} spelling (case, spaces, variants)",
            "rows": count_changed(before, list(df[column])),
            "fix": f"Mapped to the {len(ALLOWED[column])} official values",
        })

    before = list(df["claim_date"])
    df["claim_date"] = [clean_date(value) for value in before]
    text_dates = sum(1 for value in before if isinstance(value, str))
    fixes.append({"issue": "Dates typed as text (31/12/2024, 31.12.2024, 2024-12-31)", "rows": text_dates, "fix": "Parsed, day first"})

    before = list(df["claimed_amount"])
    df["claimed_amount"] = [clean_amount(value) for value in before]
    df["paid_amount"] = [clean_amount(value) for value in df["paid_amount"]]
    text_amounts = sum(1 for value in before if isinstance(value, str))
    fixes.append({"issue": "Amounts typed as text (1.234,56 €, EUR 1,234.56)", "rows": text_amounts, "fix": "Converted to numbers"})

    required = ["product", "status", "channel", "canton", "claim_date", "claimed_amount"]
    unusable = df[required].isna().any(axis=1)
    df = df[~unusable].copy()
    fixes.append({"issue": "Rows missing a required value (e.g. claimed amount)", "rows": int(unusable.sum()), "fix": "Removed"})

    report = {"rows_read": rows_read, "rows_kept": len(df), "fixes": fixes}
    return df, report
