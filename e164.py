"""Convert phone number to E.164 format (digits prefixed by +)"""
import re

def to_e164(number, country_code='', local_code=''):
    """Convert phone number to E.164 format (digits prefixed by +)"""
    number = str(number)
    country_code = str(country_code)
    local_code = str(local_code)
    digits = re.sub(r'\D', '', number)

    if re.match(r'^\+', number):
        return f"+{digits}"

    if re.match(r'^00', number):
        return f"+{digits[2:]}"

    if re.match(r'^\+', country_code):
        country_code = country_code[1:]
    if re.match(r'^00', country_code):
        country_code = country_code[2:]

    if re.match(r'^0', number):
        return f"+{country_code}{digits[1:]}"

    if re.match(r'^0', local_code):
        local_code = local_code[1:]

    return f"+{country_code}{local_code}{digits}"
