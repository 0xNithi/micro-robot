import os
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
        os.system("/etc/init.d/udev restart")
        
        filename = "log/" + time.strftime("%Y_%m_%d-%H_%M_%S") + ".log"
        logging.basicConfig(filename=filename, filemode="a",
                            format="%(asctime)s - %(levelname)s | %(message)s", level=logging.DEBUG)
        logging.info("starting initialization")

        self.initCamera()
        self.initSerial()

        # Init default variable
        self.speed = {
            "low": 30,
            "normal": 40,
            "high": 50
        }
        self.storage = 0
        self.station = {
            "red": 7,
            "blue": 7
        }
        self.signature = ["nothing", "red", "blue", "yellow"]
        self.location = {
            "now": "green",
            "to": "red",
            "from": "green"
        }

        logging.info("finished initialization")

    def initCamera(self):
        # Initial pixy camera
        try:
            pixy.init()
            pixy.set_lamp(0, 0)
            logging.info("initialize pixy successful")
        except:
            logging.critical("initialize pixy failure")

    def initSerial(self):
        # Initial serial port
        port = [None, None]
        for i in range(len(sys.argv)):
            port[i] = sys.argv[i]
        if port[1] == None:
            print("Available port: " +
                  str([port.name for port in serial.tools.list_ports.comports()]))
            port[1] = input('Enter serial port : ')

        try:
            self.ser = serial.Serial(port=port[1], baudrate=115200, timeout=1)

            # Wait arduino setup complete
            while self.ser.read_until().decode("utf-8") != "Setup Completed!\r\n":
                pass
            logging.info("initialize serial successful")
        except:
            logging.critical("initialize serial failure")

    def run(self):
        gameover = False
        collectNext = False

        while not gameover:
            if not collectNext:
                self.move(self.location["to"], self.location["from"])

            if self.storage > 0 and self.location["to"] != self.location["from"] and not collectNext:
                self.dropBall()
                self.storage = 0

                self.location["to"] = self.location["now"]
                self.location["from"] = self.location["now"]
            elif self.storage < 3 and self.station[self.location["now"]] > 0:
                if not collectNext:
                    self.sendAndRepeat(
                        [f"CMD:MRT:{self.speed['low']}:12", "GET:DC_ISIDLE"], "1")

                print("Scan Ball")
                logging.info("scan ball")
                ball = self.signature[self.scanBall(1).m_signature]
                print(f"Found {ball} ball")
                logging.info(f"found {ball} ball")

                if ball == "nothing":
                    self.station[self.location["now"]] = 0
                    collectNext = False
                else:
                    print("Aim Ball")
                    if ball == "yellow":
                        lamp = 0
                    else:
                        lamp = 1
                    logging.info(f"aim ball")
                    self.aimBall(lamp)
                    if not collectNext:
                        self.send(f"CMD:MFT:{self.speed['low']}:4.5")
                    print("Cellect Ball")
                    logging.info(f"collect ball")
                    self.collectBall()
                    self.storage += 1
                    self.station[self.location["now"]] -= 1

                    if ball == self.location["now"] or ball == "yellow":
                        # Move to the basket on the left side of the station
                        self.send(f"CMD:MLT:{self.speed['low']}:15")
                        self.sendAndRepeat(
                            [f"CMD:MBT:{self.speed['low']}:10", "GET:DC_ISIDLE"], "1")
                        self.sendAndRecieve(
                            f"CMD:OPT:MFBL:{self.speed['low']}")
                        self.send(f"CMD:MLT:{self.speed['low']}:35")
                        self.sendAndRecieve("CMD:SRS")

                        self.storage -= 1

                        self.location["to"] = self.location["now"]
                        self.location["from"] = self.location["now"]

                        collectNext = False
                    else:
                        self.sendAndRecieve("CMD:BRS")
                        collectNext = True
                        if self.storage == 3:
                            collectNext = False
                            self.location["to"] = ball
                            self.location["from"] = self.location["now"]
                            self.resetStation()

                if self.storage == 0 and self.station["red"] == 0 and self.station["blue"] == 0:
                    self.location["to"] = "green"
                    self.location["from"] = self.location["now"]
                    self.resetStation()
                    gameover = True
                elif self.station[self.location["now"]] == 0 and self.storage != 3:
                    if self.location["now"] == "red":
                        self.location["to"] = "blue"
                    else:
                        self.location["to"] = "red"
                    self.location["from"] = self.location["now"]
                    self.resetStation()

        self.move("green", self.location["now"])

    def move(self, to, From):
        print(f"Change station to {to} from {From}")
        logging.info(f"change station to {to} from {From}")

        if to == "red" and From == "green":
            self.sendAndRepeat(
                [f"CMD:MLT:{self.speed['high']}:110", "GET:DC_ISIDLE"], "1")
        elif to == "red" and From == "red":
            self.send(f"CMD:MRT:{self.speed['low']}:35")
            self.sendAndRepeat(
                [f"CMD:MBT:{self.speed['low']}:10", "GET:DC_ISIDLE"], "1")
        elif to == "blue" and From == "red":
            self.sendAndRepeat(
                [f"CMD:MBT:{self.speed['high']}:70", "GET:DC_ISIDLE"], "1")
            self.sendAndRepeat(
                [f"CMD:RLT:{self.speed['normal']}:91", "GET:DC_ISIDLE"], "1")
            self.sendAndRepeat(
                [f"CMD:MFT:{self.speed['high']}:150", "GET:DC_ISIDLE"], "1")
        elif to == "green" and From == "red":
            self.send(f"CMD:MRT:{self.speed['high']}:115")
        elif to == "blue" and From == "blue":
            self.send(f"CMD:MRT:{self.speed['low']}:35")
            self.sendAndRepeat(
                [f"CMD:MBT:{self.speed['low']}:10", "GET:DC_ISIDLE"], "1")
        elif to == "red" and From == "blue":
            self.sendAndRepeat(
                [f"CMD:MBT:{self.speed['high']}:180", "GET:DC_ISIDLE"], "1")
            self.sendAndRepeat(
                [f"CMD:MRT:{self.speed['high']}:50", "GET:DC_ISIDLE"], "1")
            self.sendAndRepeat(
                [f"CMD:RRT:{self.speed['normal']}:90", "GET:DC_ISIDLE"], "1")
        elif to == "green" and From == "blue":
            self.sendAndRepeat(
                [f"CMD:MBT:{self.speed['high']}:180", "GET:DC_ISIDLE"], "1")
            self.sendAndRepeat(
                [f"CMD:MRT:{self.speed['high']}:52", "GET:DC_ISIDLE"], "1")
            self.send(f"CMD:MBT:{self.speed['high']}:115")

        self.location["now"] = to

        if to != "green":
            self.sendAndRecieve(f"CMD:OPT:MFBL:{self.speed['low']}")
            self.sendAndRepeat(
                [f"CMD:MFT:{self.speed['low']}:2", "GET:DC_ISIDLE"], "1")
            self.sendAndRecieve(f"CMD:OPT:MRBL:{self.speed['low']}")

    def resetStation(self):
        print("Reset station")
        logging.info("reset station")
        pixy.set_lamp(0, 0)

        self.send(f"CMD:MLT:{self.speed['low']}:15")
        self.sendAndRepeat(
            [f"CMD:MBT:{self.speed['low']}:10", "GET:DC_ISIDLE"], "1")
        self.sendAndRecieve(
            f"CMD:OPT:MFBL:{self.speed['low']}")
        self.sendAndRepeat(
            [f"CMD:MFT:{self.speed['low']}:2", "GET:DC_ISIDLE"], "1")
        self.sendAndRecieve(f"CMD:OPT:MRBL:{self.speed['low']}")

    def scanBall(self, lamp=1):
        pixy.change_prog("color_connected_components")
        pixy.set_lamp(lamp, lamp)

        blocks = BlockArray(3)

        success = 0
        last_candidate = ""

        while success < 5:
            count = pixy.ccc_get_blocks(3, blocks)
            sigIndex = 0
            if count > 0:
                for j in range(count):
                    if blocks[j].m_x > blocks[sigIndex].m_x and blocks[j].m_y <= 100:
                        sigIndex = j
            if last_candidate == blocks[sigIndex].m_signature:
                success += 1
            else:
                success = 0

            last_candidate = blocks[sigIndex].m_signature

        return blocks[sigIndex]

    def aimBall(self, lamp=1):
        isAim = True

        while isAim:
            ball = self.scanBall(lamp)
            if ball.m_signature > 0:
                r = ball.m_width / \
                    ball.m_height
                offsetX = ((r - 1) * ball.m_height / 2)
                newX = math.floor((ball.m_x + offsetX))

                if abs(130 - newX) == 0:
                    isAim = False
                elif newX > 130:
                    self.send(f"CMD:MRT:{self.speed['low']}:0.1:RLS")
                else:
                    self.send(f"CMD:MLT:{self.speed['low']}:0.1:RLS")

    def collectBall(self):
        pixy.set_lamp(0, 0)
        self.sendAndRecieve(f"CMD:KPB")

    def dropBall(self):
        logging.info("drop ball")
        self.send(f"CMD:MFT:{self.speed['low']}:2")
        self.sendAndRepeat(
            [f"CMD:MLT:{self.speed['low']}:8", "GET:DC_ISIDLE"], "1")
        self.sendAndRecieve("CMD:GTE:OPN")
        time.sleep(3)
        self.sendAndRecieve("CMD:GTE:CLS")
        self.sendAndRepeat(
            [f"CMD:MBT:{self.speed['low']}:10", "GET:DC_ISIDLE"], "1")
        self.sendAndRepeat(
            [f"CMD:MLT:{self.speed['low']}:30", "GET:DC_ISIDLE"], "1")

    def send(self, cmd):
        self.ser.write((cmd + '\n').encode())
        logging.info(f"serial: send command {cmd}")

    def sendAndRecieve(self, cmd):
        self.ser.flushInput()
        self.send(cmd)

        while True:
            msg = self.ser.read_until("\r\n")
            if msg:
                logging.info(f"serial: recieve message {msg}")
                return msg

    def sendAndRepeat(self, cmd, msg):
        self.send(cmd[0])

        while self.sendAndRecieve(cmd[1]).decode()[:-2] != msg:
            pass

    def test(self):
        while True:
            self.send(input())
