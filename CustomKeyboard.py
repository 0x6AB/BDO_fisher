import struct
import random
import serial
from time import sleep
import sys
import glob

class CustomKeyboard:
    serial_port = None
    debug = False

    def __init__(self, port, port_rate=115200, debug=False, key=1234):
        self.KEY = key
        self.serial_port = serial.Serial(port=port, baudrate=port_rate)
        self.debug = debug
        if self.debug:
            print("Open connect, port_rate =", port_rate)

    def __del__(self):
        self.serial_port.close()
        if self.debug:
            print("Closed connect")

    def __print_debug_data__(self):
        while self.serial_port.inWaiting() > 0:
            line = self.serial_port.readline()
            if line:
                print(line.decode().strip())

    def send_text(self, data):
        self.serial_port.write(b"\x01"+struct.pack("H", self.KEY)+b"\x00\x00\x00"+data.encode('ascii'))
        if self.debug:
            sleep(0.05)
            self.__print_debug_data__()

    def emulated_click(self, key):
        self.serial_port.write(b"\x02"+struct.pack("H", self.KEY)+struct.pack("H", random.randint(31, 50))+b"\x00"+key.encode('ascii'))
        if self.debug:
            sleep(0.05)
            self.__print_debug_data__()

    def emulated_text(self, text, timing=random.randint(31, 50), floating_border=random.randint(5, 15)):
        self.serial_port.write(b"\x03"+struct.pack("H", self.KEY)+struct.pack("H", timing)+struct.pack("B", floating_border)+text.encode('ascii'))
        if self.debug:
            sleep(0.05)
            self.__print_debug_data__()


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result