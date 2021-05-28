import sys
import time
import math
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
                while True:
                    self.moveCenter()
                    self.send("CMD:MFC:20")
                    self.rotate()
                    self.cam.change_prog("color_connected_components")
                    self.cam.set_lamp(1, 1)
                    blocks = BlockArray(3)
                    self.send("CMD:MRT:30:5")
                    while True:
                        count = self.cam.ccc_get_blocks (3, blocks)
                        sigIndex = 0
                        for i in range(count):
                            if blocks[i].m_x > blocks[sigIndex].m_x and blocks[i].m_y <= 100:
                                sigIndex = i
                        print('[BLOCK: SIG=%d X=%3d Y=%3d WIDTH=%3d HEIGHT=%3d]' % (blocks[sigIndex].m_signature, blocks[sigIndex].m_x, blocks[sigIndex].m_y, blocks[sigIndex].m_width, blocks[sigIndex].m_height))
                        if count > 0:
                            r = blocks[sigIndex].m_width / blocks[sigIndex].m_height - 0.1
                            offsetX = ((r - 1) * blocks[sigIndex].m_height / 2)
                            newX = math.floor((blocks[sigIndex].m_x + offsetX))
                            print(f"newX:{newX}")
                            if abs(125 - newX) <= 2:
                                break
                            elif newX > 125:
                                self.send("CMD:MRT:30:0.5:RLS")
                            else:
                                self.send("CMD:MLT:30:0.5:RLS")
                    self.send("CMD:MFC:15")
                    while True:
                        count = self.cam.ccc_get_blocks (3, blocks)
                        sigIndex = 0
                        for i in range(count):
                            if blocks[i].m_x > blocks[sigIndex].m_x and blocks[i].m_y <= 100:
                                sigIndex = i
                        print('[BLOCK: SIG=%d X=%3d Y=%3d WIDTH=%3d HEIGHT=%3d]' % (blocks[sigIndex].m_signature, blocks[sigIndex].m_x, blocks[sigIndex].m_y, blocks[sigIndex].m_width, blocks[sigIndex].m_height))
                        r = blocks[sigIndex].m_width / blocks[sigIndex].m_height - 0.1
                        offsetX = ((r - 1) * blocks[sigIndex].m_height / 2)
                        newX = math.floor(blocks[sigIndex].m_x + offsetX)
                        print(f"newX:{newX}")
                        if count > 0 and blocks[sigIndex].m_height * blocks[sigIndex].m_height >= 3700:
                            self.send("CMD:STP")
                            break
                    if newX >= 100 and newX <= 130:
                        self.sendAndWait("CMD:KPB", "Done")
                        self.send("CMD:MBT:60:7")
                        self.send("CMD:MLT:60:45")
                        self.sendAndWait("CMD:SRS", "Done")
                        break
                    else:
                        self.send("CMD:MBT:30:60")
                break
            
    def test(self):
        while True:
            self.send(input())
            

    def goto(self, to, From):
        if to == "redStation" and From == "greenStaion":
            self.send("CMD:MLT:30:110")
            self.send("CMD:MBT:30:60")
            self.sendAndWait("GET:DC_ISIDLE", "1", True)
        elif to == "blueStation" and From == "redStation":
            self.send("CMD:MBT:30:60")
            self.sendAndWait(["CMD:MLT:30:120", "GET:DC_ISIDLE"], "1")
            self.sendAndWait(["CMD:RLT:30:90", "GET:DC_ISIDLE"], "1")
        elif to == "redStation" and From == "blueStation":
            self.sendAndWait(["CMD:MBT:30:180", "GET:DC_ISIDLE"], "1")
            self.sendAndWait(["CMD:RRT:30:90", "GET:DC_ISIDLE"], "1")

    def moveCenter(self):
        isCenter = False
        vectors = VectorArray(1)
        self.cam.set_lamp(0, 0)

        while not isCenter:
            line_get_main_features()
            count_v = line_get_vectors(1, vectors)
            deltaX = vectors[0].m_x1 - vectors[0].m_x0
            
            print(f"x0:{vectors[0].m_x0} x1:{vectors[0].m_x1} deltaX:{deltaX}")
            
            if count_v > 0:
                # Move it left or right until the line is centered on the camera
                if abs(deltaX) <= 1:
                    isCenter = True
                elif deltaX < 1:
                    self.send("CMD:MRT:30:0.5:RLS")
                else:
                    self.send("CMD:MLT:30:0.5:RLS")

    def rotate(self):
        intersections = IntersectionArray(1)
        vectors = VectorArray(4)
        isFound = False

        # Find an intersection
        while not isFound:
            line_get_all_features()
            line_get_intersections(1, intersections)

            # If an intersection is found, stop the motor
            if intersections[0].m_y >= 15 and intersections[0].m_n >= 3:
                self.send("CMD:STP")
                self.send("CMD:MBT:60:10")
                self.sendAndWait("GET:DC_ISIDLE", "1", True)
                #self.send("CMD:MBT:30:10")       # Move back for analyze intersection branches
                isFound = True

        isCenter = False

        while not isCenter:
            minX = 99
            maxX = -1
            y0 = 0
            y1 = 0
            isFound = False
            
            # Get an intersection
            while not isFound:
                line_get_all_features()
                line_get_intersections(1, intersections)
                v_count = line_get_vectors(4, vectors)
                print('[INTERSECTION: X=%d Y=%d BRANCHES=%d]' % (
                    intersections[0].m_x, intersections[0].m_y, intersections[0].m_n))
            
                if intersections[0].m_n >= 3:
                    for lineIndex in range (0, intersections[0].m_n):
                        print('  [LINE: INDEX=%d ANGLE=%d]' % (intersections[0].getLineIndex(lineIndex), intersections[0].getLineAngle(lineIndex)))
                    for index in range (0, v_count):
                        if minX > vectors[index].m_x0:
                            minX = vectors[index].m_x0
                            y0 = vectors[index].m_y0
                        if minX > vectors[index].m_x1:
                            minX = vectors[index].m_x1
                            y0 = vectors[index].m_y1
                        if maxX < vectors[index].m_x0:
                            maxX = vectors[index].m_x0
                            y1 = vectors[index].m_y0
                        if maxX < vectors[index].m_x1:
                            maxX = vectors[index].m_x1
                            y1 = vectors[index].m_y1
                        print('[VECTOR: INDEX=%d X0=%d Y0=%d X1=%d Y1=%d]' % (vectors[index].m_index, vectors[index].m_x0, vectors[index].m_y0, vectors[index].m_x1, vectors[index].m_y1))
                    isFound = True

            deltaY = y0 - y1
            print(f"y0:{y0} y1:{y1} deltaY:{deltaY}")
            
            if abs(deltaY) <= 1:
                isCenter = True
            elif deltaY > 0:
                self.send("CMD:RLT:30:1:RLS")
            else:
                self.send("CMD:RRT:30:1:RLS")

    def send(self, cmd):
        self.ser.flush()
        self.ser.write((cmd).encode())
        logging.info(f"serial: send command {cmd}")

    def sendAndWait(self, cmd, msg, retransmit=False):
        self.send(cmd)

        while True:
            res = self.ser.read_until("\r\n")
            logging.info(f"serial: recieve message {res}")
            if msg == res.decode()[:-2]:
                break
            if retransmit:
                self.send(cmd)

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
    
class IntersectionLine (Structure):
  _fields_ = [
    ("m_index", c_uint),
    ("m_reserved", c_uint),
    ("m_angle", c_uint) ]
  
class Blocks (Structure):
  _fields_ = [ ("m_signature", c_uint),
    ("m_x", c_uint),
    ("m_y", c_uint),
    ("m_width", c_uint),
    ("m_height", c_uint),
    ("m_angle", c_uint),
    ("m_index", c_uint),
    ("m_age", c_uint) ]