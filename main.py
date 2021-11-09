"""the main program"""
import logging
import sys

import ctrlc
import e164
import modem
import zisson
from init_serial import init_serial

if __name__ == "__main__":

    ctrlc.install_ctrl_c_handler()

    logging.basicConfig(
        format="%(levelname)s %(module)s %(name)s %(asctime)s: %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S")

    serial_port = init_serial()
    dialer = zisson.ZissonDialer()
    adapter = e164.SimpleE164Adapter('47', None, dialer)
    modem = modem.Modem(serial_port, adapter)
    try:
        modem.run()
    except KeyboardInterrupt:
        print("Ctrl-Break pressed, exiting...")
