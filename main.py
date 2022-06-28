"""the main program"""
import logging
import sys

from init_serial import init_serial
import modem
from phonelog import PhoneLogDialer


if __name__ == "__main__":

    logging.basicConfig(
        format="%(levelname)s %(module)s %(name)s %(asctime)s: %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S")

    serial_port = init_serial()
    dialer = PhoneLogDialer()
    modem = modem.Modem(serial_port, dialer)
    modem.run()
