# This is a simple modem emulator.
# It is not complete, and probably not useful for anyone else.

# Interesting links about modems:
# https://en.wikipedia.org/wiki/Command_and_Data_modes_(modem)
# https://en.wikipedia.org/wiki/Hayes_command_set
# https://www.itu.int/rec/T-REC-V.25ter/en
# http://www.messagestick.net/modem/hayes_modem.html
# https://support.usr.com/support/3453b/3453b-crg/chap%201-installing%20your%20modem.html

# Documentation for pyserial:
# https://pyserial.readthedocs.io/en/latest/pyserial_api.html

# Virtual serial port driver:
# http://com0com.sourceforge.net/
# Signed version at:
# https://code.google.com/archive/p/powersdr-iq/downloads

import re
import enum
import time
import abc


def _onoff(value): # convert bool to bytestring 'on' or 'off'
    return b'on' if value else b'off'


def _illval(value): # prints error message as byte string
    return b'Illegal param: ' + str(value).encode('ascii')


def _int0(s): # convert string with digits to int, 0 if empty
    return 0 if s == b'' else int(s)


def _tobstr(v): # convert value to byte string
    return str(v).encode('ascii')


def _bchr(n): # convert numbers between 0 and 255 to bytestring of length 1
    return (n).to_bytes(1, byteorder='big')


def _command_nop(legal_values=[]):
    def nop(self, value):
        if value not in legal_values:
            raise NotImplementedError
    return nop


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
    def dial(self, to):
        print(f"Dummydialer dialing: {to}")


class Modem:
    def __init__(self, serial_port, dialer):
        self._serial_port = serial_port
        self._serial_port.timeout = None
        self._state = _ModemState.COMMAND
        self._debug = True
        self._command_buffer = b''
        self._data_buffer = b''
        self._last_data_read = 0.0
        self._escape_chars_read = 0
        self._current_s_register = 12
        self.set_defaults()
        self._dialer = dialer


    def set_defaults(self):
        self.command_mode_echo = True
        self.verbose_results = True
        self.result_code_suppression = 0
        self._s = {
            2: ord('+'),    # escape character
            3: ord('\r'),   # line termination character
            4: ord('\n'),   # response formatting character
            5: ord('\b'),   # command line editing character
            12: 50,         # guard time for escape sequence in 1/50 seconds
            # the following S-registers makes no sense in an emulator, but are common in init strings
            0:0, 1:0, 6:0, 7:0, 9:0, 10:0, 11:0
            }

    @property
    def escape(self):
        return _bchr(self._s[2])
    @property
    def cr(self):
        return _bchr(self._s[3])
    @property
    def lf(self):
        return _bchr(self._s[4])
    @property
    def bs(self):
        return _bchr(self._s[5])
    @property
    def escape_wait(self):
        return self._s[12] / 50


    def _set_state(self, state):
        self._state = state
        if state == _ModemState.ONLINE:
            self._serial_port.timeout = 0
        else:
            self._serial_port.timeout = None


    def _write_command_result(self, result):
        if self.verbose_results:
            self._serial_port.write(
                self.cr + self.lf +
                _tobstr(result.name) +
                self.cr + self.lf)
        else:
            self._serial_port.write(
                _tobstr(str(result.value)) +
                self.cr)


    def _write_command_response(self, response):
        assert type(response) == bytes
        if self.verbose_results:
            self._serial_port.write(self.cr + self.lf + response + self.cr + self.lf)
        else:
            self._serial_port.write(response + self.cr + self.lf)


    def _read_serial(self, nbytes=1):
        buf = self._serial_port.read(1)
        while self._serial_port.in_waiting > 0:
            buf += self._serial_port.read(self._serial_port.in_waiting)
        now = time.monotonic()
        if self._state == _ModemState.ONLINE:
            if (self._escape_chars_read == 3):
                if now - self._last_data_read > self.escape_wait:
                    self._set_state(_ModemState.ONLINE_COMMAND)
                    self._write_command_result(_ModemResult.OK)
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
                if self.command_mode_echo:
                    if _bchr(buf[-1]) == self.cr:
                        self._serial_port.write(buf + self.lf)
                    else:
                        self._serial_port.write(buf)

        return len(buf) != 0


    def run(self):
        while True:
            self.run_once()

    def run_for(self, seconds):
        start = time.monotonic()
        while time.monotonic() < start + seconds:
            self.run_once()

    def run_once(self):
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
        while self.cr in self._command_buffer:
            eol = self._command_buffer.find(self.cr)
            line = self._command_buffer[:eol].strip()
            self._command_buffer = self._command_buffer[eol+1:]
            while self.bs in line:
                line = re.sub(b'[^' + self.bs + b']' + self.bs, b'', line)
                line = re.sub(b'^' + self.bs, b'', line)
            while line[:3] == b'+++':
                line = line[3:]
            if line.strip() == b'':
                return
            if m := re.match(b'^[aA][tT](.*)$', line):
                self._process_at_commands(m.group(1).upper())
            else:
                self._write_command_result(_ModemResult.ERROR)


    def _command_ate(self, value):
            assert value in [0,1]
            self.command_mode_echo = bool(value)


    def _command_ath(self, value):
        assert value == 0
        self._set_state(_ModemState.COMMAND)


    def _command_ato(self, value):
        assert (self._state == _ModemState.ONLINE_COMMAND and
                value == 0 or
                self._state in [_ModemState.COMMAND, _ModemState.ONLINE_COMMAND] and
                value == 999)
        if value == 0:
                raise "hell" # not implemented
        elif value == 999:
            self._set_state(_ModemState.ONLINE)

    def _command_atq(self, value):
        assert value in [0,1]
        self.result_code_suppression = value


    def _command_ats(self, value):
        assert value in self._s.keys()
        self._current_s_register = value


    def _command_atv(self, value):
        assert value in [0,1]
        self.verbose_results = value


    def _command_atz(self,value):
        assert value == 0
        self.set_defaults()


    def _command_at_equals(self, value):
        assert type(value) == int and 0 <= value <= 255
        self._s[self._current_s_register] = value


    def _command_at_question(self, value):
        assert value == 0
        register = _tobstr(self._current_s_register)
        value = _tobstr(self._s[self._current_s_register])
        self._write_command_response(value)


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
        verbose = []
        while line != b'' and result == _ModemResult.OK:

            # ignore whitespace and +++ when already in command mode
            if m:= re.match(b'\\s*\\+\\+\\+(.*)$', line):
                line = m.group(1).strip

            # Handle most of the supported AT-commands
            break_out = False
            for cmd in Modem._commands:
                if m:= re.match(cmd + b'(\\d*)(.*)$', line):
                    break_out = True
                    param = _int0(m.group(1))
                    line = m.group(2)
                    try:
                        Modem._commands[cmd](self, param)
                    except:
                        result = _ModemResult.ERROR
                    break
            if break_out:
                continue

            # D: dial a number
            elif m:= re.match(b'D[PT]?(\s*\\+?[\d\s\\*\\#]+)\\;?$', line):
                number = re.sub(b'\s', b'', m.group(1))
                line = b''

                try:
                    self._dialer.dial(number.decode('ascii'))
                except:
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
        global modem

        serial_port = init_serial()
        dialer = DummyDialer()
        modem = Modem(serial_port, dialer)

        modem.run()


    runmodem()
