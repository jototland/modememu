# This is a simple modem emulator.
# It is not complete, and probably not useful for anyone else.

# Interesting links about modems:
# https://en.wikipedia.org/wiki/Command_and_Data_modes_(modem)
# https://en.wikipedia.org/wiki/Hayes_command_set
# http://www.messagestick.net/modem/hayes_modem.html
# https://support.usr.com/support/3453b/3453b-crg/chap%201-installing%20your%20modem.html

# Documentation for pyserial:
# https://pyserial.readthedocs.io/en/latest/pyserial_api.html#native-ports

# Virtual serial port driver:
# http://com0com.sourceforge.net/
# Signed version at:
# https://code.google.com/archive/p/powersdr-iq/downloads

import serial
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


def _bchr(n): # convert number to byte
    return (n).to_bytes(1, byteorder='big')


class _ModemState(enum.Enum):
    # These values are arbitrary
    COMMAND = 1
    ONLINE = 2
    ONLINE_COMMAND = 3

class _ModemResult(enum.Enum):
    # These values are fairly standard for Hayes compatible modems
    OK = 0
    CONNECT = 1
    RING = 2
    NO_CARRIER = 3
    ERROR = 4
    NO_DIALTONE = 6
    BUSY = 7
    NO_ANSWER = 8

class _ModemResultCodes(enum.Enum):
    # These values are fairly standard for Hayes compatible modems
    ENABLED = 0
    ONLY_CR = 1
    DISABLED = 2

_BUFSIZE = 4096      # number of bytes we try to read each time
_SHORT_WAIT = 0.05   # seconds to wait when we read no data

class Modem:
    def __init__(self, serial_port):
        self._serial_port = serial_port
        self._state = _ModemState.COMMAND
        self._debug = True
        self._command_buffer = b''
        self._data_buffer = b''
        self._last_data_read = 0.0
        self._escape_chars_read = 0
        self._current_s_register = 12
        self.set_defaults()


    def set_defaults(self):
        self.command_mode_echo = True
        self.verbose_results = True
        self.resultCodes = _ModemResultCodes.ENABLED
        self._s = {
            2: ord('+'),    # escape character
            3: ord('\r'),   # line termination character
            4: ord('\n'),   # response formatting character
            5: ord('\b'),   # command line editing character
            12: 50          # guard time for escape sequence in 1/50 seconds
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

        
    def _write_command_result(self, result, diagnostics=b''):
        if diagnostics != b'':
            diagnostics = b' (' + diagnostics.strip() + b')'
        if self.resultCodes == _ModemResultCodes.ENABLED:
            if self.verbose_results:
                self._serial_port.write(
                    self.cr + self.lf +
                    result.name.replace('_', ' ').encode('ascii') +
                    diagnostics + self.cr + self.lf)
            else:
                self._serial_port.write(
                    str(result.value).encode('ascii') + self.cr)
        elif self.resultCodes == _ModemResultCodes.ONLY_CR:
            self._serial_port.write(self.cr)
        elif self.resultCodes == _ModemResultCodes.DISABLED:
            self._serial_port.write(b'')
        else:
            assert False, "_ModemResultCodes can only be ENABLED, ONLY_CR or DISABLED"


    def _write_command_response(self, bs):
        assert type(bs) == bytes
        if self.verbose_results:
            self._serial_port.write(self.cr + self.lf + bs + self.cr + self.lf)
        else:
            self._serial_port.write(bs + self.cr + self.lf)
        

    def _read_serial(self, nbytes=1):
        buf = b''
        while (data := self._serial_port.read(_BUFSIZE)) != b'':
            buf += data
        now = time.monotonic()
        if self._state == _ModemState.ONLINE:
            if (self._escape_chars_read == 3):
                if now - self._last_data_read > self.escape_wait:
                    self._state = _ModemState.ONLINE_COMMAND
                    self._write_command_result(_ModemResult.OK, b"escape sequence read")
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
                    self._data_buffer +- (self.escape + self._escape_chars_read) + buf
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
                    self._serial_port.write(buf)
                    if buf[-1] == self.cr:
                        self._serial_port.write(self.lf)

        return len(buf) != 0


    def run(self):
        while True:
            if not self._read_serial():
                time.sleep(_SHORT_WAIT)
                continue
            if self._state == _ModemState.COMMAND:
                self._process_command_buffer()
            elif self._state == _ModemState.ONLINE_COMMAND:
                if self._data_buffer != b'':
                    pass # FIXME: does nothing as of now
                self._process_command_buffer()
            elif self._state == _ModemState.ONLINE:
                pass # FIXME: does nothing as of now
            else:
                assert False, "Illegal value of Modem.state"


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
                self._write_command_result(_ModemResult.ERROR, b'unrecognizable command')


    def _at_command_e(self, value):
            assert value in [0,1]
            self.command_mode_echo = bool(value)
            return b'echo ' + _onoff(value)


    def _at_command_h(self, value):
        assert value == 0
        self._state = _ModemState.COMMAND
        self._serial_port.dtr = 0
        return b"on hook"


    def _at_command_o(self, value):
        assert (self._state == _ModemState.ONLINE_COMMAND and
                value == 0 or
                self._state in [_ModemState.COMMAND, _ModemState.ONLINE_COMMAND] and
                value == 999)
        if value == 0:
                pass # not implemented
        elif value == 999:
            self._write_command_result(_ModemResult.OK)
            self._serial_port.dtr = True
            self._state = _ModemState.ONLINE
            return b"simulated data connection"
            

    def _at_command_q(self, value):
        assert value in [0,1,2]
        self.resultCodes = _ModemResultCodes(value)
        return (b'result codes: ' +
                self.resultCodes.name.replace('_', ' ').lower().encode('ascii'))


    def _at_command_s(self, value):
        assert value in self._s.keys()
        self._current_s_register = value
        return b'S[' + _tobstr(value) + b']'


    def _at_command_v(self, value):
        assert value in [0,1]
        self.verbose_results = value
        return b'verbose ' + _onoff(value)


    def _at_command_z(self,value):
        assert value == 0
        self.set_defaults()
        return b'reset to factory defaults'


    def _at_command_equals(self, value):
        assert type(value) == int and 0 <= value <= 255
        self._s[self._current_s_register] = value
        return b"S[" + _tobstr(self._current_s_register) + b']=' + _tobstr(value)


    def _at_command_question(self, value):
        assert value == 0
        register = _tobstr(self._current_s_register)
        value = _tobstr(self._s[self._current_s_register])
        self._write_command_response(value)
        return b'S[' + register + b']=' + value        


    _commands = {}
    _commands[b'E'] = _at_command_e
    _commands[b'H'] = _at_command_h
    _commands[b'O'] = _at_command_o
    _commands[b'Q'] = _at_command_q
    _commands[b'S'] = _at_command_s
    _commands[b'V'] = _at_command_v
    _commands[b'Z'] = _at_command_z
    _commands[b'\\='] = _at_command_equals
    _commands[b'\\?'] = _at_command_question


    def _process_at_commands(self, line):
        result = _ModemResult.OK
        verbose = []
        while line != b'' and result == _ModemResult.OK:

            # ignore whitespace and +++ when already in command mode
            if m:= re.match(b'\\s*\\+\\+\\+(.*)$', line):
                line = m.group(1).strip

            # Handle most commands
            break_out = False
            for cmd in Modem._commands:
                if m:= re.match(cmd + b'(\\d*)(.*)$', line):
                    break_out = True
                    param = _int0(m.group(1))
                    line = m.group(2)
                    try:
                        verbose.append(Modem._commands[cmd](self, param))
                    except AssertionError:
                        result = _ModemResult.ERROR
                        verbose.append(_illval(param))
                    except:
                        result = _ModemResult.ERROR
                        verbose.append(b'unknown error')
                    break
            if break_out:
                continue
                
            # D: dial a number
            elif m:= re.match(b'D[PT]?(\s*\\+?[\d\s\\*\\#]+)\\;?$', line):
                number = re.sub(b'\s', b'', m.group(1))
                verbose.append(b"dialled " + number + b" for voice only")
                line = b''
                # if it actually connects to something that looks like data
                # from another modem, such as a telnet server,
                # we should also send CONNECT later.
                # But no CONNECT for voice calls.

            # otherwise: unknown command
            else:
                result = _ModemResult.ERROR
                verbose.append(b"unregognizable command")
                break

        self._write_command_result(result, b", ".join(verbose))

if __name__ == "__main__":

    def runmodem():
        global modem

        serial_port = serial.Serial(
            port="COM11",
            baudrate=115200,
            bytesize=8,
            timeout=0,
            stopbits=serial.STOPBITS_ONE
            )

        modem = Modem(serial_port)
        while True:
            modem.run()


    runmodem()
