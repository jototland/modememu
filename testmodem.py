"""run som simple tests on modem simulator"""
import serial


def _bs(string):
    if isinstance(string, str):
        return string.encode('cp437')
    return string


def _s(string):
    if isinstance(string, bytes):
        return string.decode('cp437')
    return string

class SerialTester:
    """Helper class to test serial lines"""
    def __init__(self, port):
        self._port = port
        self._sendcount = 0


    def send(self, data):
        self._port.write(_bs(data))


    def send_expect_echo(self, data):
        self.send(data)
        self.expect(data)


    def sendline(self, data):
        self.send(_bs(data) + b'\r')


    def sendline_expect_echo(self, data):
        self.send(_bs(data) + b'\r')
        self.expect(_bs(data) + b'\r\n')


    def expect(self, data):
        data = _bs(data)
        read = b''
        while len(read) < len(data) and data.startswith(read):
            read += self._port.read(min(self._port.in_waiting or 1,
                                        len(data) - len(read)))
        if read != data:
            print(f"Expectation failed:")
            print(f"    Expected: {repr(data)}")
            print(f"    Got     : {repr(read)}")


port = serial.Serial(port='COM3', baudrate=9600, bytesize=8, stopbits=1)
s = SerialTester(port)

# pylint: disable=multiple-statements
s.sendline_expect_echo('at'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('   at    '); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('')
s.sendline_expect_echo('   ')
s.sendline_expect_echo('\b')
s.send('a'); s.expect('a')
s.send('t'); s.expect('t')
s.send('\r'); s.expect('\r\n')
s.expect('\r\nOK\r\n')
s.sendline_expect_echo('xy\b\bat'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('\u0000\u0000'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('atat'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('+++at'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('fn92fj9me2,['); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('ata0'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('atb0'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atb1'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atb2'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('ate0'); s.expect('\r\nOK\r\n')
s.sendline('ate1'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('ate2'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('ath'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('ath1'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('atl'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atl0'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atl1'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atl2'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atl3'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atl4'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('atm0'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atm1'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atm2'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atm3'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atm4'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('ato'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('atq'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atq1'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atq2'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('ats2=15'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('at?'); s.expect('\r\n15\r\n'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('ats3=120'); s.expect('x\nOKx\n')
s.send('ats3=13x'); s.expect('ats3=13x\n'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('ats4=120?'); s.expect('\rx120\rx'); s.expect('\rxOK\rx')
s.send('ats4=10\r'); s.expect('ats4=10\rx'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('ats5=30=120?'); s.expect('\r\n120\r\n'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('##xxat'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('ats5=8'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('ats99'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('atdt99999'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atv0'); s.expect('0\r')
s.sendline_expect_echo('atv1'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atx0'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atx1'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atx2'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atx3'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atx4'); s.expect('\r\nOK\r\n')
s.sendline_expect_echo('atx5'); s.expect('\r\nERROR\r\n')
s.sendline_expect_echo('atz'); s.expect('\r\nOK\r\n')

print("Tests completed")
