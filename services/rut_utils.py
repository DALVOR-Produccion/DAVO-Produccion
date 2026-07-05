import re


def clean_rut(rut: str) -> str:
    if not rut:
        return ""

    rut = rut.strip().upper()
    rut = rut.replace(".", "").replace("-", "")
    rut = re.sub(r"[^0-9K]", "", rut)

    return rut


def format_rut(rut: str) -> str:
    rut = clean_rut(rut)

    if len(rut) < 2:
        return rut

    body = rut[:-1]
    dv = rut[-1]

    return f"{body}-{dv}"


def calculate_dv(rut_body: str) -> str:
    reversed_digits = map(int, reversed(rut_body))
    factors = [2, 3, 4, 5, 6, 7]

    total = 0
    factor_index = 0

    for digit in reversed_digits:
        total += digit * factors[factor_index]
        factor_index = (factor_index + 1) % len(factors)

    remainder = 11 - (total % 11)

    if remainder == 11:
        return "0"
    if remainder == 10:
        return "K"
    return str(remainder)


def is_valid_rut(rut: str) -> bool:
    rut = clean_rut(rut)

    if len(rut) < 2:
        return False

    body = rut[:-1]
    dv = rut[-1]

    if not body.isdigit():
        return False

    expected_dv = calculate_dv(body)
    return dv == expected_dv


def normalize_rut(rut: str) -> str:
    rut = clean_rut(rut)

    if len(rut) < 2:
        return rut

    return format_rut(rut)
