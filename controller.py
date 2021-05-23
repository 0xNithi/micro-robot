import sys
import time
import logging
import pixy
import serial

class controller:
    def __init__(self):
        port = [None, None]
        self.filename = "log/" + time.strftime("%Y_%m_%d-%H_%M_%S") + ".log"

        logging.basicConfig(filename=self.filename, filemode="a",
                            format="%(asctime)s - %(message)s", level=logging.DEBUG)
        logging.info("starting initialization")

        # Init serial port
        for i in range(len(sys.argv)):
            port[i] = sys.argv[i]
        if port[1] == None:
            self.portList()
            port[1] = input('Enter serial port : ')
        try:
            self.ser = serial.Serial(port=port[1], baudrate=115200, timeout=1)
        except:
            logging.exception("serial")

        # Init pixy camera
        try:
            self.cam = pixy
            self.cam.init()
            self.cam.change_prog("video");
            self.cam.set_lamp(1, 0);
        except:
            logging.exception("pixy")
        
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
            cmd = input()
            self.ser.write(cmd.encode())
        
    def portList(self):
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        print("Available port: " + str([port.name for port in ports]))