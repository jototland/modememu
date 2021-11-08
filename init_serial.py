"""initializes serial port as given in serial.json"""
import json
import re

import serial


def init_serial():
    """initializes serial port as given in serial.json"""
    with open('serial.json', encoding='utf8') as json_file:
        data = json.load(json_file)

    port = data['port']
    baudrate = data['baudrate'] if 'baudrate' in data else 115200
    bytesize = data['bytesize'] if 'bytesize' in data else 8
    stopbits = data['stopbits'] if 'stopbits' in data else 1

    assert re.match(r'COM\d+', port)
    assert baudrate in [50, 75, 110, 134, 150, 200, 300,
                        600, 1200, 1800, 2400, 4800, 9600,
                        19200, 38400, 57600, 115200]
    assert bytesize == 8
    assert stopbits in [1, 1.5, 2]


    return serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        stopbits=stopbits,
    )
