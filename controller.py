import sys
import time
import logging
import serial
import pixy
import serial.tools.list_ports

from ctypes import *
from pixy import *


class controller:
    def __init__(self):
        port = [None, None]
        filename = "log/" + time.strftime("%Y_%m_%d-%H_%M_%S") + ".log"

        logging.basicConfig(filename=filename, filemode="a",
                            format="%(asctime)s - %(levelname)s | %(message)s", level=logging.DEBUG)
        logging.info("starting initialization")

        # Init serial port
        for i in range(len(sys.argv)):
            port[i] = sys.argv[i]
        if port[1] == None:
            self.portList()
            port[1] = input('Enter serial port : ')
        try:
            self.ser = serial.Serial(port=port[1], baudrate=115200, timeout=1)
            logging.info("initialize serial successful")

            # Wait arduino setup complete
            while self.ser.read_until().decode("utf-8") != "Setup Completed!\r\n":
                pass
        except:
            logging.critical("initialize serial failure")

        # Init pixy camera
        try:
            self.cam = pixy
            self.cam.init()
            self.cam.change_prog("line")
            self.cam.set_lamp(0, 0)
            logging.info("initialize pixy successful")
        except:
            logging.critical("initialize pixy failure")

        # Init defualt variable
        self.ballStorage = []

        logging.info("finished initialization")

    def run(self):
        while True:
            if self.ser.is_open:
                self.goto("redStation", "greenStaion")
                break

    def goto(self, to, From):
        if to == "redStation" and From == "greenStaion":
            self.send("CMD:MLT:30:120")
            self.sendAndWait(["CMD:MBT:30:60", "GET:DC_ISIDLE"], "1\r\n")
        elif to == "blueStation" and From == "redStation":
            self.send("CMD:MBT:30:60")
            self.sendAndWait(["CMD:MLT:30:120", "GET:DC_ISIDLE"], "1\r\n")
            self.sendAndWait(["CMD:RLT:30:90", "GET:DC_ISIDLE"], "1\r\n")
        elif to == "redStation" and From == "blueStation":
            self.sendAndWait(["CMD:MBT:30:180", "GET:DC_ISIDLE"], "1\r\n")
            self.sendAndWait(["CMD:RRT:30:90", "GET:DC_ISIDLE"], "1\r\n")
        self.moveCenter()
        self.rotate()

    def moveCenter(self):
        isCenter = False
        vectors = VectorArray(1)

        while not isCenter:
            line_get_main_features()
            line_get_vectors(1, vectors)
            deltaX = vectors[0].m_x1 - vectors[0].m_x0

            # Move it left or right until the line is centered on the camera
            if abs(deltaX) == 0:
                isCenter = True
            elif deltaX < 0:
                self.send("CMD:MRT:30:0.5:RLS")
            else:
                self.send("CMD:MLT:30:0.5:RLS")

    def rotate(self):
        intersections = IntersectionArray(1)
        vectors = VectorArray(4)
        isFound = False

        self.send("CMD:MFC:15")

        # Find an intersection
        while not isFound:
            line_get_all_features()
            line_get_intersections(1, intersections)

            # If an intersection is found, stop the motor
            if intersections[0].m_y >= 15 and intersections[0].m_n >= 3:
                self.send("CMD:STP")
                self.send("CMD:MBT:30:5")       # Move back for analyze intersection branches
                isFound = True

        isCenter = False

        while not isCenter:
            isFound = False
            # Get an intersection
            while not isFound:
                line_get_all_features()
                line_get_intersections(1, intersections)
                line_get_vectors(4, vectors)
                print('[INTERSECTION: X=%d Y=%d BRANCHES=%d]' % (
                    intersections[0].m_x, intersections[0].m_y, intersections[0].m_n))
                if intersections[0].m_n == 4:
                    isFound = True

            deltaY = vectors[2].m_y0 - vectors[3].m_y1
            if deltaY == 0:
                isCenter = True
            elif deltaY > 0:
                self.send("CMD:RLT:30:1:RLS")
            else:
                self.send("CMD:RRT:30:1:RLS")

    def send(self, cmd):
        self.ser.write((cmd).encode())
        logging.info(f"serial: send command {cmd}")

        while True:
            msg = self.ser.read_until().decode("utf-8")
            if msg:
                logging.info(f"serial: recieve message {msg}")
                return msg

    def sendAndWait(self, cmd, msg):
        self.send(cmd[0])

        while self.send(cmd[1]) != msg:
            pass

    def portList(self):
        ports = serial.tools.list_ports.comports()
        print("Available port: " + str([port.name for port in ports]))


class Vector(Structure):
    _fields_ = [
        ("m_x0", c_uint),
        ("m_y0", c_uint),
        ("m_x1", c_uint),
        ("m_y1", c_uint),
        ("m_index", c_uint),
        ("m_flags", c_uint)]
