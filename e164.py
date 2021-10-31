import re


class SimpleE164Adapter:
    def __init__(self, country_code, dialer):
        self._country_code = country_code
        self._dialer = dialer


    def dial(self, to):
        to = to.replace(' ', '')
        if m:= re.match('00(\d+)$', to):
            self._dialer.dial(f"+{m.group(1)}")
        elif n:= re.match('\d+$', to):
            self._dialer.dial(f"+47{to}")
        else:
            raise "hell"
