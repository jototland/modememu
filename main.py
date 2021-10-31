import serial
import modem
import zisson
import e164

serial_port = serial.Serial(
    port='COM11',
    baudrate=115200,
    bytesize=8,
    timeout=0,
    stopbits=serial.STOPBITS_ONE
)

dialer = zisson.ZissonDialer('zisson.json')
adapter = e164.SimpleE164Adapter('47', dialer)

modem = modem.Modem(serial_port, adapter)
modem.run()
