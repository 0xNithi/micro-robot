import time
import logging


class carc:
    def __init__(self):
        self.filename = "log/" + time.strftime("%Y_%m_%d-%H_%M_%S") + ".log"

        logging.basicConfig(filename=self.filename, filemode="a",
                            format="%(asctime)s - %(message)s", level=logging.DEBUG)
        logging.debug("starting initialization")

        self.ballStorage = {}
        self.location = {
            "now": "green-staion",
            "from": "green-staion",
            "to": "red-station"
        }

        logging.debug("finished initialization")

    def run(self):
        # go to red station
        # loop until drop last ball
            # get ball to robot
            # drop ball to basket
        # go to green station
        print("run")
