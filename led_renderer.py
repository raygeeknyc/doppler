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

    def redraw(self):                          
        """Redraw all idle and then updated cells, remove cells from the idle and update lists."""
        self.redraw_cycle_time = time.time() - self.redraw_cycle_timestamp
        self.redraw_cycle_timestamp = time.time()

        start = time.time()
        stillColor = pixelblock.NEUTRAL_COLOR
        expire = start + renderer.CELL_IDLE_TIME
        for x in xrange(len(self._cells)):
            for y in xrange(len(self._cells[x])):
                if self._cells[x][y].ttl < start:
                    self._surface.SetPixel(x, y, stillColor[0], stillColor[1], stillColor[2])
                    self._cells[x][y].ttl = expire
        self.idle_time_consumption = (time.time() - start)

        start = time.time()
	redraw_count = len(self._changedCells)
        for cellToRefresh in self._changedCells:
            self._surface.SetPixel(cellToRefresh.col, cellToRefresh.row,
              cellToRefresh.color[0], cellToRefresh.color[1], cellToRefresh.color[2])
        self._changedCells = []
        self.redraw_time_consumption = (time.time() - start)
	return redraw_count

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
