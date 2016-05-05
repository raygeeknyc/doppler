import collections
import config
import logging
import pixelblock
from pixelblock import PixelBlock
from rgbmatrix import Adafruit_RGBmatrix
import renderer
import update_message
import time
import random
import renderer
from renderer import App
import resource
import select
import signal
import socket
import string
import sys
import zlib

LED_MATRIX_ROWS = 16
LED_MATRIX_COLS = 32

class LedApp(App):
    def _initializeDisplay(self, surface, unused_info):
	logging.debug("Initializing LED display")
        self._surface = surface
        self._surface.Clear()
        self._screen_width = LED_MATRIX_COLS
        self._screen_height = LED_MATRIX_ROWS
        self._cols = self._screen_width
        self._rows = self._screen_height

    def _draw(x, y, RGB):
        self._surface.SetPixel(x, y, RGB[0], RGB[1], RGB[2])

    def _updateDisplay(self):
        pass

def main(argv=[]):	
	logging.getLogger().setLevel(logging.DEBUG if DEBUG_DISPLAY else logging.INFO)
	logging.info("running")

	def quit_handler(signal, frame):
		logging.info("Interrupted")
		a.finish()

	signal.signal(signal.SIGINT, quit_handler)

	logging.debug("Creating matrix")
	matrix = Adafruit_RGBmatrix(LED_MATRIX_ROWS, 1)
	logging.debug("Starting renderer")
	a = LedApp(matrix, None)
	while True:
		try:
			a.refresh()
		except Exception as e:
			logging.exception("Top level exception")
			a.finish()
	a.finish()


if __name__ == "__main__":
	if len(sys.argv) > 1 and sys.argv[1] == "debug":
		print("debugging")
		DEBUG_DISPLAY=True
	else:   
		DEBUG_DISPLAY=False
	main()
