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
        stillColor = App._colorForState(update_message.CellState.CHANGE_STILL)
        expire = start + renderer.CELL_IDLE_TIME
        for x in xrange(len(self._cells)):
            for y in xrange(len(self._cells[x])):
                if self._cells[x][y].ttl < start:
                    self._surface.SetPixel(x, y, stillColor[0], stillColor[1], stillColor[2])
#                          (r * 0b001001001) / 2,
#                          (g * 0b001001001) / 2,
#                           b * 0b00010001)
                    self._cells[x][y].ttl = expire
        self.idle_time_consumption = (time.time() - start)

        start = time.time()
	redraw_count = len(self._changedCells)
        for cellToRefresh in self._changedCells:
            self._surface.SetPixel(cellToRefresh.plot_x, cellToRefresh.plot_y,
              cellToRefresh.color[0],cellToRefresh.color[1],cellToRefresh.color[2])
        self._changedCells = []
        self.redraw_time_consumption = (time.time() - start)
	return redraw_count

    def _updateDisplay(self):
        pass

def main(argv=[]):	
	logging.getLogger().setLevel(logging.DEBUG if DEBUG_DISPLAY else logging.INFO)

	def quit_handler(signal, frame):
		logging.info("Interrupted")
		a.finish()

	signal.signal(signal.SIGINT, quit_handler)

	matrix = Adafruit_RGBmatrix(LED_MATRIX_ROWS, 1)
	a = LedApp(matrix, None)
	while True:
		try:
			a.refresh()
		except Exception as e:
			logging.exception("Top level exception")
			a.finish()
	a.finish()


if len(sys.argv) > 1 and sys.argv[1] == "debug":
        DEBUG_DISPLAY=True
else:   
        DEBUG_DISPLAY=False

if __name__ == "__main__":
	main()
