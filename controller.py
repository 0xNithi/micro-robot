import time
import logging

filename = ""

def init():
    global filename
    filename = "log/" + time.strftime("%Y_%m_%d-%H_%M_%S") + ".log"

    logging.basicConfig(filename=filename, filemode="a",
                        format="%(asctime)s - %(message)s", level=logging.DEBUG)
    logging.debug("starting initialization")

    ballStorage = {}
    location = {
        "now": "green-staion",
        "from": "green-staion",
        "to": "red-station"
    }

    logging.debug("finished initialization")

def run():
    print(filename)