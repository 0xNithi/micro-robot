import sys
import time
import logging
from ctypes import *
from pixy import *

class controller:
    def __init__(self):
        port = [None, None]
        self.filename = "log/" + time.strftime("%Y_%m_%d-%H_%M_%S") + ".log"

        logging.basicConfig(filename=self.filename, filemode="a",
                            format="%(asctime)s:%(levelname)s - %(message)s", level=logging.DEBUG)
        logging.info("starting initialization")

        # Init serial port
        for i in range(len(sys.argv)):
            port[i] = sys.argv[i]
        if port[1] == None:
            self.portList()
            port[1] = input('Enter serial port : ')
        try:
            import serial
            
            self.ser = serial.Serial(port=port[1], baudrate=115200, timeout=1)
            logging.info("initialize serial successful")
            while True:
                res = self.ser.read_until().decode("utf-8")
                
                if(res == "Setup Completed!\r\n"):
                    print(res)
                    break
                
        except:
            logging.critical("initialize serial failure")

        # Init pixy camera
        try:
            import pixy
            
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
            "now": "green-staion",
            "from": "green-staion",
            "to": "red-station"
        }

        logging.info("finished initialization")

    def run(self):
        while True:
            if self.ser.is_open:
                self.send("CMD:MLT:40:120")
                self.send("CMD:MBT:40:60")
                while self.send("GET:DC_ISIDLE") != "1\r\n":
                    pass
                self.moveCenter()
                self.send("CMD:MFT:40:65")
                break
        
    def moveCenter(self):
        while True:
            vectors = VectorArray(1)
            line_get_main_features()
            line_get_vectors (1, vectors)
            deltaX = vectors[0].m_x1 - vectors[0].m_x0
            print('[VECTOR: INDEX=%d X0=%d Y0=%d X1=%d Y1=%d]' % (vectors[0].m_index, vectors[0].m_x0, vectors[0].m_y0, vectors[0].m_x1, vectors[0].m_y1))
            if abs(deltaX) >= 0 and abs(deltaX) <= 1:
                break
            else:
                if deltaX < 0:
                    self.send("CMD:MRT:40:1")
                else:
                    self.send("CMD:MLT:40:1")

    def send(self, msg):
    
        self.ser.write((msg).encode())
        logging.info(f"serial: send message {msg}")
        
        while True:
            res = self.ser.read_until().decode("utf-8")
            if(res):
                print(res)
                logging.info(f"serial: recieve message {res}")
                return res
        
    def portList(self):
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        print("Available port: " + str([port.name for port in ports]))

class Vector(Structure):
  _fields_ = [
    ("m_x0", c_uint),
    ("m_y0", c_uint),
    ("m_x1", c_uint),
    ("m_y1", c_uint),
    ("m_index", c_uint),
    ("m_flags", c_uint) ]