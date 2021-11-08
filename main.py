"""the main program"""
from init_serial import init_serial
import modem
import zisson
import e164

serial_port = init_serial()
dialer = zisson.ZissonDialer()
adapter = e164.SimpleE164Adapter('47', None, dialer)

modem = modem.Modem(serial_port, adapter)

if __name__ == "__main__":

    try:
        modem.run()
    except KeyboardInterrupt:
        print("Ctrl-c pressed, exiting...")
