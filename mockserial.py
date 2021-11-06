import time


class IllegalModemOutput(BaseException):
    def __init__(self, s):
        super().__init__(s)


def _bs(s):
    assert type(s) in [str, bytes]
    if type(s) == str:
        return s.encode('cp437')
    else:
        return s


def _s(s):
    assert type(s) in [str, bytes]
    if type(s) == bytes:
        return s.decode('cp437')
    else:
        return s


_SHORT_WAIT = 0.1


class MockSerial:
    def __init__(self):
        self._start = time.monotonic()
        self._send = []
        self._expect = []
        self._sendcount = 0
        self._expectcount = 0
        self._first_time = True


    def send(self, data):
        if self._send == []:
            self._send.append((self._start, _bs(data)))
        else:
            lastclock, _ = self._send[-1]
            self._send.append((lastclock + _SHORT_WAIT, _bs(data)))


    def send_expect_echo(self, data):
        self.send(data)
        self.expect(data)


    def sendline(self, data):
        self.send(_bs(data) + b'\r')


    def sendline_expect_echo(self, data):
        self.send(_bs(data) + b'\r')
        self.expect(_bs(data) + b'\r\n')


    def expect(self, data):
        self._expect.append(_bs(data))


    def seconds(self):
        return _SHORT_WAIT * len(self._send) + _SHORT_WAIT


    def _firsttime(self):
        if self._first_time:
            print("User:\t\tModem:")
            print("----------------------")
            self._first_time = False

    ################################################

    def write(self, data):
        self._firsttime()
        assert self._expectcount < len(self._expect)
        print(f"<=\t\t'{repr(data)[2:-1]}'")
        expected = self._expect[self._expectcount]
        if expected != data:
            raise IllegalModemOutput(
                f"Expected: '{expected}', " +
                f"Got: '{data}'")
        self._expectcount += 1


    def read(self, _):
        self._firsttime()
        if self._sendcount >= len(self._send):
            return b''
        clock, tosend = self._send[self._sendcount]
        if time.monotonic() > clock:
            print(f"=> '{repr(tosend)[2:-1]}'")
            self._sendcount += 1
            return tosend

        else:
            return b''

    @property
    def in_waiting(self):
        if self._sendcount >= len(self._send):
            return 0
        clock, tosend = self._send[self._sendcount]
        if time.monotonic() > clock:
            return len(tosend)
        else:
            return 0
