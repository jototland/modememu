"""Mock a serial line - used for testing modem emulator"""
import time


class IllegalModemOutput(BaseException):
    """raised when the modem outputs something unexpected"""


def _bs(string):
    assert isinstance(string, (str, bytes))
    if isinstance(string, str):
        return string.encode('cp437')
    return string


def _s(string):
    assert isinstance(string, (str, bytes))
    if isinstance(string, bytes):
        return string.decode('cp437')
    return string


_SHORT_WAIT = 0.1


class MockSerial:
    """Mock a serial line - used for testing modem emulator"""
    def __init__(self):
        self._start = time.monotonic()
        self._send = []
        self._expect = []
        self._sendcount = 0
        self._expectcount = 0
        self._first_time = True


    def send(self, data):
        """queue data to be sent later"""
        if self._send == []:
            self._send.append((self._start, _bs(data)))
        else:
            lastclock, _ = self._send[-1]
            self._send.append((lastclock + _SHORT_WAIT, _bs(data)))


    def send_expect_echo(self, data):
        """queue data to be sent later, and queue expectation of echo """
        self.send(data)
        self.expect(data)


    def sendline(self, data):
        """queue data to be sent later, followed by a carriage return"""
        self.send(_bs(data) + b'\r')


    def sendline_expect_echo(self, data):
        """queue data to be sent later, followed by a carriage return,
        and queue expection of echo"""
        self.send(_bs(data) + b'\r')
        self.expect(_bs(data) + b'\r\n')


    def expect(self, data):
        """queue expection of data to receive back on serial line"""
        self._expect.append(_bs(data))


    def seconds(self):
        """report number of seconds for simulation so far"""
        return _SHORT_WAIT * len(self._send) + _SHORT_WAIT


    def _firsttime(self):
        if self._first_time:
            print("User:\t\tModem:")
            print("----------------------")
            self._first_time = False

    ################################################

    def write(self, data):
        """simulate serial.write"""
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
        """simulate serial.read"""
        self._firsttime()
        if self._sendcount >= len(self._send):
            return b''
        clock, tosend = self._send[self._sendcount]
        if time.monotonic() > clock:
            print(f"=> '{repr(tosend)[2:-1]}'")
            self._sendcount += 1
            return tosend
        return b''

    @property
    def in_waiting(self):
        """simulate serial.in_waiting"""
        if self._sendcount >= len(self._send):
            return 0
        clock, tosend = self._send[self._sendcount]
        if time.monotonic() > clock:
            return len(tosend)
        return 0
