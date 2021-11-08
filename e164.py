"""Wraps a dialer and converts input from the modem to E164 format"""
import re

class SimpleE164Adapter:
    """Wraps a dialer and converts input from the modem to E164 format"""
    def __init__(self, country_code, local_code, dialer):
        if isinstance(country_code, int):
            country_code = str(int)
        if isinstance(local_code, int):
            local_code = str(int)
        elif local_code is None:
            local_code = ''
        assert isinstance(country_code, str) and re.match(r'\d+', country_code)
        assert isinstance(local_code, str) and re.match(r'\d*', local_code)
        self._country_code = country_code
        self._local_code = local_code
        self._dialer = dialer


    def dial(self, to_number):
        """Converts number to E164 format and dials using the stored dialer"""
        if isinstance(to_number, int):
            to_number = str(to_number)
        to_number = to_number.replace(' ', '')
        if re.match(r'\+\d+$', to_number):
            self._dialer.dial(to_number)
        elif matches := re.match(r'00(\d+)$', to_number):
            self._dialer.dial(f"+{matches.group(1)}")
        elif matches := re.match(r'0(\d+)$', to_number):
            self._dialer.dial(f"+{self._country_code}{matches.group(1)}")
        elif re.match(r'\d+$', to_number):
            self._dialer.dial(f"+{self._country_code}{self._local_code}{to_number}")
        else:
            raise ValueError(f"number must contain only digits: {to_number}")
