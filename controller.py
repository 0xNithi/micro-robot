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
        self.location = {
            "from": "greenStaion",
            "to": "redStation"
        }

        logging.info("finished initialization")

    def run(self):
        while True:
            if self.ser.is_open:
                self.goto("redStation", "greenStaion")
                break

    def goto(self, to, From):
        if to == "redStation" and From == "greenStaion":
            #self.send("CMD:MLT:30:120")
            #self.sendAndWait(["CMD:MBT:30:60", "GET:DC_ISIDLE"], "1\r\n")
            #self.moveCenter()
            self.rotateCenter()

    def moveCenter(self):
        isCenter = False
        vectors = VectorArray(1)

        while not isCenter:
            line_get_main_features()
            line_get_vectors(1, vectors)
            deltaX = vectors[0].m_x1 - vectors[0].m_x0
            print('[VECTOR: INDEX=%d X0=%d Y0=%d X1=%d Y1=%d]' % (
                vectors[0].m_index, vectors[0].m_x0, vectors[0].m_y0, vectors[0].m_x1, vectors[0].m_y1))

            if abs(deltaX) == 0:
                isCenter = True
            elif deltaX < 0:
                self.send("CMD:MRT:30:0.5:RLS")
            else:
                self.send("CMD:MLT:30:0.5:RLS")
                
    def rotateCenter(self):
        intersections = IntersectionArray(1)
        
        while True:
        #    self.send("CMD:MFC:15")
            line_get_all_features()
            line_get_intersections(1, intersections)
            print('[INTERSECTION: X=%d Y=%d BRANCHES=%d]' % (intersections[0].m_x, intersections[0].m_y, intersections[0].m_n))
            if intersections[0].m_y >= 15 and intersections[0].m_n >= 3:
                self.send("CMD:STP")
        #        self.send("CMD:MBT:30:5")
                for lineIndex in range (0, intersections[0].m_n):
                    print('  [LINE: INDEX=%d ANGLE=%d]' % (intersections[0].getLineIndex(lineIndex), intersections[0].getLineAngle(lineIndex)))
                break
        
        while True:
            lineAngle = []
            index = 0
            while True:
                line_get_all_features()
                line_get_intersections(1, intersections)
                print('[INTERSECTION: X=%d Y=%d BRANCHES=%d]' % (intersections[0].m_x, intersections[0].m_y, intersections[0].m_n))
                if intersections[0].m_n == 4:
                    for lineIndex in range(0, 4):
                        lineAngle.append(abs(intersections[0].getLineAngle(lineIndex)))
                        print('  [LINE: INDEX=%d ANGLE=%d]' % (intersections[0].getLineIndex(lineIndex), intersections[0].getLineAngle(lineIndex)))
                    lineAngle.sort()
                    break
            for lineIndex in range(0, 4):
                if lineAngle[1] == abs(intersections[0].getLineAngle(lineIndex)):
                    index = lineIndex
            if abs(intersections[0].getLineAngle(index)) <= 1:
                break
            elif intersections[0].getLineAngle(index) < 1:
                self.send("CMD:RLT:30:1:RLS")
            else:
                self.send("CMD:RRT:30:1:RLS")

    def send(self, cmd):
        self.ser.write((cmd).encode())
        logging.info(f"serial: send command {cmd}")

        while True:
            res = self.ser.read_until().decode("utf-8")
            if(res):
                print(res)
                logging.info(f"serial: recieve message {res}")
                return res

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
