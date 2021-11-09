"""
A modem emulator
 - meant for older software that wants to interface with a modem and make calls
"""
import enum
import logging
import re
import time


def _int0(string_of_digits): # convert string with digits to int, 0 if empty
    assert isinstance(string_of_digits, bytes)
    return 0 if string_of_digits == b'' else int(string_of_digits)


def _tobstr(value): # convert any value to byte string
    return str(value).encode('ascii')


def _bchr(byte_value): # convert a number between 0 and 255 to a bytestring of length 1
    assert isinstance(byte_value, int)
    assert 0 <= byte_value <= 255
    return (byte_value).to_bytes(1, byteorder='big')


class _ModemState(enum.Enum):
    # These values have no meaning outside this program
    COMMAND = 1
    ONLINE = 2
    ONLINE_COMMAND = 3

class _ModemResult(enum.Enum):
    # These values are standard for Hayes compatible modems
    OK = 0
    CONNECT = 1
    RING = 2
    NO_CARRIER = 3
    ERROR = 4
    NO_DIALTONE = 6
    BUSY = 7
    NO_ANSWER = 8

_BUFSIZE = 4096      # number of bytes we try to read each time
_SHORT_WAIT = 0.05   # seconds to wait when we read no data


class DummyDialer:
    """A dummy dialer for testing"""
    def dial(self, to_number): # pylint: disable=no-self-use
        """pretend to dial a number"""
        print(f"Dummydialer dialing: {to_number}")


class Modem:
    """Simulates a modem"""
    # pylint: disable=too-many-instance-attributes
    def __init__(self, serial_port, dialer):
        self._command_log = logging.getLogger('command').info
        self._response_log = logging.getLogger('response').info

        self._serial_port = serial_port
        self._dialer = dialer

        self._serial_port.timeout = None

        self._state = _ModemState.COMMAND

        self._command_buffer = b''
        self._data_buffer = b''

        self._last_data_read = 0.0
        self._escape_chars_read = 0

        self._current_s_register = None
        self._s = {}

        self._command_mode_echo = True
        self._verbose_results = True
        self._result_code_suppression = False
        self.set_defaults()


    def set_defaults(self):
        """sets modem to default settings (similar to ATZ command)"""
        self._command_mode_echo = True
        self._verbose_results = True
        self._result_code_suppression = False
        self._s = {
            2: ord('+'),    # escape character
            3: ord('\r'),   # line termination character
            4: ord('\n'),   # response formatting character
            5: ord('\b'),   # command line editing character
            12: 50,         # guard time for escape sequence in 1/50 seconds
            # The following S-registers makes no sense in an emulator,
            # but are common in init strings. We define and ignore them.
            0:0, 1:0, 6:0, 7:0, 9:0, 10:0, 11:0
            }

    @property
    def escape(self):
        """returns the current escape character for exiting online mode, default '+'"""
        return _bchr(self._s[2])
    @property

    def carriage_return(self):
        """returns the current CR character, default \\r"""
        return _bchr(self._s[3])
    @property
    def line_feed(self):
        """returns the current LF character, default \\n"""
        return _bchr(self._s[4])
    @property
    def backspace(self):
        """returns the current backspace character, default \\b"""
        return _bchr(self._s[5])
    @property
    def escape_wait(self):
        """returns the current waiting period for escape sequence in seconds, default 1s"""
        return self._s[12] / 50


    def _set_state(self, state):
        self._state = state
        if state == _ModemState.ONLINE:
            self._serial_port.timeout = 0
        else:
            self._serial_port.timeout = None


    def _write_command_result(self, result):
        result_name = result.name.replace('_', ' ')
        self._response_log(result_name)
        if self._verbose_results:
            self._serial_port.write(
                self.carriage_return + self.line_feed +
                _tobstr(result_name) +
                self.carriage_return + self.line_feed)
        else:
            self._serial_port.write(
                _tobstr(str(result.value)) +
                self.carriage_return)


    def _write_command_response(self, response):
        assert isinstance(response, bytes)
        self._response_log(response.strip().decode('cp437'))
        if self._verbose_results:
            self._serial_port.write(self.carriage_return + self.line_feed +
                                    response +
                                    self.carriage_return + self.line_feed)
        else:
            self._serial_port.write(response + self.carriage_return + self.line_feed)


    def _read_serial(self):
        # pylint: disable=too-many-branches
        buf = self._serial_port.read(1)
        while self._serial_port.in_waiting > 0:
            buf += self._serial_port.read(self._serial_port.in_waiting)
        now = time.monotonic()
        if self._state == _ModemState.ONLINE:
            if self._escape_chars_read == 3:
                if now - self._last_data_read > self.escape_wait:
                    self._set_state(_ModemState.ONLINE_COMMAND)
                    self._write_command_result(_ModemResult.NO_CARRIER)
                    self._escape_chars_read = 0
                    self._command_buffer += buf
                elif buf != b'':
                    self._data_buffer += (self.escape * self._escape_chars_read) + buf
                    self._escape_chars_read = 0
                    self._last_data_read = now
            elif self._escape_chars_read > 0:
                if (self._escape_chars_read == 1 and buf in [self.escape, self.escape * 2] or
                        self._escape_chars_read == 2 and buf == self.escape):
                    self._escape_chars_read += len(buf)
                    self._last_data_read = now
                elif buf != b'':
                    self._data_buffer += (self.escape + self._escape_chars_read) + buf
                    self._escape_chars_read = 0
                    self._last_data_read = now
            elif (now - self._last_data_read > self.escape_wait and
                  buf in [self.escape, self.escape * 2, self.escape * 3]):
                self._escape_chars_read = len(buf)
                self._last_data_read = now
            elif buf != b'':
                self._data_buffer += buf
                self._last_data_read = now
        elif self._state in [_ModemState.COMMAND, _ModemState.ONLINE_COMMAND]:
            if buf != b'':
                self._command_buffer += buf
                if self._command_mode_echo:
                    if _bchr(buf[-1]) == self.carriage_return:
                        self._serial_port.write(buf + self.line_feed)
                    else:
                        self._serial_port.write(buf)

        return len(buf) != 0


    def run(self):
        """runs the modem forever"""
        while True:
            self.run_once()

    def run_for(self, seconds):
        """runs the modem for the given number of seconds"""
        start = time.monotonic()
        while time.monotonic() < start + seconds:
            self.run_once()

    def run_once(self):
        """does one pass of the inner loop for running the modem"""
        if not self._read_serial():
            time.sleep(_SHORT_WAIT)
            return
        if self._state == _ModemState.COMMAND:
            self._process_command_buffer()
        elif self._state == _ModemState.ONLINE_COMMAND:
            if self._data_buffer != b'':
                pass # FIXME: does nothing as of now
            self._process_command_buffer()
        elif self._state == _ModemState.ONLINE:
            pass # FIXME: does nothing as of now
        else:
            assert False, "Illegal value of Modem._state"


    def _process_command_buffer(self):
        while self.carriage_return in self._command_buffer:
            eol = self._command_buffer.find(self.carriage_return)
            line = self._command_buffer[:eol].strip()
            self._command_log(line.strip().decode('cp437'))
            self._command_buffer = self._command_buffer[eol+1:]
            while self.backspace in line:
                line = re.sub(b'[^' + self.backspace + b']' + self.backspace, b'', line)
                line = re.sub(b'^' + self.backspace, b'', line)
            while line[:3] == b'+++':
                line = line[3:]
            if line.strip() == b'':
                return
            if matches := re.match(b'^[aA][tT](.*)$', line):
                self._process_at_commands(matches.group(1).upper())
            else:
                self._write_command_result(_ModemResult.ERROR)


    @staticmethod
    def _command_nop(legal_values=[]): # pylint: disable=dangerous-default-value
        assert all(isinstance(x, int) for x in legal_values)
        def nop(self, value): # pylint: disable=unused-argument
            if value not in legal_values:
                raise ValueError(f'value myst be in {list(legal_values)}')
            return _ModemResult.OK
        return nop


    def _command_ate(self, value):
        if value not in [0,1]:
            raise ValueError('ATE: value must be 0 or 1')
        self._command_mode_echo = bool(value)
        return _ModemResult.OK


    def _command_ath(self, value):
        if value != 0:
            raise ValueError('ATH: value must be 0')
        assert value == 0
        if self._state == _ModemState.ONLINE:
            self._set_state(_ModemState.COMMAND)
            return _ModemResult.NO_CARRIER
        return _ModemResult.OK


    def _command_ato(self, value):
        if value == 0:
            raise NotImplementedError
        if value == 999:
            self._set_state(_ModemState.ONLINE)
            return _ModemResult.CONNECT
        raise ValueError('ATO: Value must be 0')

    def _command_atq(self, value):
        if value not in [0,1]:
            raise ValueError('ATQ: value must be 0 or 1')
        self._result_code_suppression = bool(value)
        return _ModemResult.OK


    def _command_ats(self, value):
        # pylint: disable=consider-iterating-dictionary
        if value not in self._s.keys():
            raise ValueError('ATS: unsupported S-register')
        self._current_s_register = value
        return _ModemResult.OK


    def _command_atv(self, value):
        if value not in [0,1]:
            raise ValueError('ATV: value must be 0 or 1')
        self._verbose_results = value
        return _ModemResult.OK


    def _command_atz(self,value):
        if value != 0:
            raise ValueError('ATZ: value must be 0')
        self.set_defaults()
        return _ModemResult.OK


    def _command_at_equals(self, value):
        if not 0 <= value <= 255:
            raise ValueError('AT=: value must be between 0 and 255')
        self._s[self._current_s_register] = value
        return _ModemResult.OK


    def _command_at_question(self, value):
        if value != 0:
            raise ValueError('AT?: value must be 0')
        value = _tobstr(self._s[self._current_s_register])
        self._write_command_response(value)
        return _ModemResult.OK


    _commands = {}
    _commands[b'A'] = _command_nop()
    _commands[b'B'] = _command_nop(range(2))
    _commands[b'E'] = _command_ate
    _commands[b'H'] = _command_ath
    _commands[b'L'] = _command_nop(range(4))
    _commands[b'M'] = _command_nop(range(4))
    _commands[b'O'] = _command_ato
    _commands[b'Q'] = _command_atq
    _commands[b'S'] = _command_ats
    _commands[b'V'] = _command_atv
    _commands[b'X'] = _command_nop(range(5))
    _commands[b'Z'] = _command_atz
    _commands[b'\\='] = _command_at_equals
    _commands[b'\\?'] = _command_at_question


    def _process_at_commands(self, line):
        result = _ModemResult.OK
        while line != b'' and result == _ModemResult.OK:

            # ignore whitespace and +++ when already in command mode
            if matches:= re.match(b'\\s*\\+\\+\\+(.*)$', line):
                line = matches.group(1).strip

            # Handle most of the supported AT-commands
            break_out = False
            for cmd_name, cmd_func in Modem._commands.items():
                if matches := re.match(cmd_name + b'(\\d*)(.*)$', line):
                    break_out = True
                    param = _int0(matches.group(1))
                    line = matches.group(2)
                    try:
                        result = cmd_func(self, param)
                    except (ValueError, NotImplementedError):
                        result = _ModemResult.ERROR
                    break
            if break_out:
                continue

            # D: dial a number
            if matches := re.match(b'D[PT]?(\\s*\\+?[\\d\\s\\*\\#]+)\\;?$', line):
                number = re.sub(b'\\s', b'', matches.group(1))
                line = b''

                try:
                    self._dialer.dial(number.decode('ascii'))
                except (ValueError, NotImplementedError):
                    result = _ModemResult.ERROR

                # if we actually connect to something that looks like data
                # from another modem, such as a telnet server,
                # we should also send CONNECT later.
                # But no CONNECT for voice calls.

            # otherwise: unknown command
            else:
                result = _ModemResult.ERROR
                break

        self._write_command_result(result)

if __name__ == "__main__":

    from init_serial import init_serial

    def runmodem():
        """creates a dummy modem for running tests"""
        serial_port = init_serial()
        dialer = DummyDialer()
        modem = Modem(serial_port, dialer)

        modem.run()


    runmodem()
