from django.utils import timezone


def current_financial_year_start() -> int:
    today = timezone.now().date()
    return today.year if today.month >= 4 else today.year - 1


def current_financial_year_digits() -> str:
    start_year = current_financial_year_start()
    return f"{start_year}{str(start_year + 1)[-2:]}"


def financial_year_range_from_digits(fy_digits: str) -> str:
    """Inverse of current_financial_year_digits: "202627" -> "2026-2027"."""
    start_year = int(fy_digits[:4])
    return f"{start_year}-{start_year + 1}"
