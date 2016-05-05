"apt-get install tcl tk python-pygame"

import collections
import config
import logging
import pixelblock
from pixelblock import PixelBlock
import pygame
from pygame.locals import *
import update_message
import time
import random
import resource
import select
import signal
import socket
import string
import sys
import zlib

HOST = ''  # Symbolic name meaning the local host
MAXIMUM_UPDATE_MESSAGE_LEN = 8*1024

CELL_IDLE_TIME = 2  # Set cells to idle after this many secs of inactivity

# The shapes that we know how to render
_CIRCLE = 1
_RECT = 2

# Set the shape of a plotted pixel to _CIRCLE or _RECT
PIXEL_SHAPE = _RECT
PIXEL_SHAPE = _CIRCLE

def MemUsedMB():
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return (usage[2]*resource.getpagesize())/1048576.0

def getPort():
	return config.RENDERER_PORT

class App:
    @staticmethod
    def _colorForState(state):
        """Return the color for state."""
        return pixelblock.CELL_COLORS[state]

    def _initializeDisplay(self, surface, info):
	logging.debug("initializing video display")
        self._surface = surface
        self._display_info = info
        self._screen_width = info.current_w
        self._screen_height = info.current_h
        self._cols = self._screen_width / PixelBlock.CELL_WIDTH
        self._rows = self._screen_height / PixelBlock.CELL_HEIGHT

    def _plot_circle(self, color, topLeft):
        pygame.draw.circle(self._surface, color,
            (topLeft[0] * PixelBlock.CELL_WIDTH + (PixelBlock.CELL_WIDTH / 2), topLeft[1] * PixelBlock.CELL_HEIGHT + (PixelBlock.CELL_HEIGHT / 2)),
            (PixelBlock.CELL_PLOT_WIDTH/2))

    def _plot_rect(self, color, topLeft):
	pygame.draw.rect(self._surface, color, (topLeft[0] * PixelBlock.CELL_WIDTH + PixelBlock.CELL_MARGIN,
            topLeft[1] * PixelBlock.CELL_HEIGHT + PixelBlock.CELL_MARGIN,
            PixelBlock.CELL_PLOT_WIDTH, PixelBlock.CELL_PLOT_HEIGHT))

    def __init__(self, surface, info):
        self.update_time_consumption = 0.0
        self.idle_time_consumption = 0.0
        self.redraw_time_consumption = 0.0
        self.redraw_cycle_timestamp = 0.0
        self.redraw_cycle_time = 0.0
        self._plot = self._plot_circle if (PIXEL_SHAPE == _CIRCLE) else self._plot_rect
	self._initializeDisplay(surface, info)
        logging.info("%d X %d pixels\n" % (self._screen_width, self._screen_height))
        logging.info("%d X %d cells\n" % (self._cols, self._rows))
	self._cellUpdates = []
        self._changedCells = []
        self.initializeCells()
	self.setAllCellsRandomly()
	logging.debug("Initial cell states set")
	self.initializeSockets()

    def initializeSockets(self):
	self._dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	self._dataSocket.bind((HOST, getPort()))
	self._dataSocket.setblocking(0)

	self._configSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	self._configSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	self._configSocket.setblocking(1)
	self._configSocket.bind((HOST, getPort()))
	self._configSocket.setblocking(0)
	self._configSocket.listen(1)
	logging.debug("listening on port: %d" % getPort())

    def finish(self):
	logging.info("Finishing. Closing all sockets")
	try:
		if self._dataSocket:
			logging.debug("Closing data connection")
			self._dataSocket.close()
	except:
		logging.exception("Error shutting down data socket")

	try:
			logging.debug("Closing config socket")
			self._configSocket.close()
	except:
		logging.exception("Error closing config socket")
	logging.info("Ending")
	sys.exit(0)

    def initializeCells(self):
        """Set up the cells, no color set."""
        expire = time.time() + CELL_IDLE_TIME
	self._cells = [[PixelBlock(col, row, expire)
			for row in xrange(self._rows)]
		       for col in xrange(self._cols)]

    def _dumpCells(self):
        for col in xrange(self._cols):
          for row in xrange(self._rows):
	    if self._cells[col][row].color != App._colorForState(update_message.CellState.CHANGE_STILL):
	      logging.debug("cell %d,%d color is %s" % (col, row, self._cells[col][row].color))

    def setAllCellsRandomly(self):
        logging.debug("Setting all cells in %d,%d to random colors" % (self._cols, self._rows))
	updateData = []

        for row in xrange(self._rows):
          for col in xrange(self._cols):
	      updateData.append("{0},{1},{2}".format(
			      update_message.CellState.STATES[random.randint(0,len(update_message.CellState.STATES)-1)],
			      col, row))
        for cellMessage in updateData:
          self._cellUpdates.append(update_message.CellUpdate.fromText(cellMessage))
  
    def _draw(x, y, RGB):
        self._plot(RGB, (x, y))

    def _plotExpiredCells(self, stillColor):
        self._surface.lock()
        start = time.time()
        for x in xrange(len(self._cells)):
            for y in xrange(len(self._cells[x])):
                if (self._cells[x][y].ttl) and (self._cells[x][y].ttl < start):
                    self._draw(x, y, stillColor)
                    self._cells[x][y].ttl = 0
        self._surface.unlock()

    def redraw(self):                          
        """Redraw all idle cells and updated cells, clear the updated list."""
	logging.debug("redraw()")
        self.redraw_cycle_time = time.time() - self.redraw_cycle_timestamp
        self.redraw_cycle_timestamp = time.time()

        start = time.time()
        stillColor = App._colorForState(update_message.CellState.CHANGE_STILL)
        self._plotExpiredCells(stillColor)
        self.idle_time_consumption = (time.time() - start)

        start = time.time()
	redraw_count = len(self._changedCells)
        self._surface.lock()
        for cellToRefresh in self._changedCells:
            self._draw(cellToRefresh.col, cellToRefresh.row, cellToRefresh.color)
        self._surface.unlock()
        self._changedCells = []
        self.redraw_time_consumption = (time.time() - start)
	return redraw_count

    def getConfigRequest(self):
	logging.debug("getConfigRequest()")
	configConn = None
	configAddr = None
	try:
		configConn, configAddr = self._configSocket.accept()
		logging.info("Connection accepted from '%s'" % str(configAddr))
	except:
       		pass
	if configConn:
		logging.info("Sending config")
		self._sendRendererConfig(configConn)
		configConn.close()

    def _sendRendererConfig(self, connection):
	"Send our client the number of cols and rows we render."
	if not connection:
		logging.error("No connection.")
		return
	logging.info("Sending {0},{1}".format(self._cols, self._rows))
	connection.send("{0},{1}".format(self._cols, self._rows))

    def getCellUpdates(self):
	logging.debug("getCellUpdates()")
	start = time.time()
	updateData = None
	if not self._dataSocket:
		logging.error("No data socket")
	try:
		updateData, addr = self._dataSocket.recvfrom(MAXIMUM_UPDATE_MESSAGE_LEN)
		updateData = zlib.decompress(updateData)
	except:
		#TODO: distinguish between resource not available and "real" errors
		pass
	if updateData:
        	for cellMessage in updateData.split("|"):
			self._cellUpdates.append(update_message.CellUpdate.fromText(cellMessage))
	self.update_time_consumption = (time.time() - start)

    def updateCells(self):
	logging.debug("updateCells()")
	now = time.time()
        expireAt = now + CELL_IDLE_TIME
	for cellUpdate in self._cellUpdates:
                x,y = cellUpdate.x, cellUpdate.y
      		self._cells[x][y].color = App._colorForState(cellUpdate.state)
      		self._cells[x][y].ttl = expireAt
	      	self._changedCells.append(self._cells[x][y])
	self._cellUpdates = []

    def _updateDisplay(self):
	pygame.display.update()

    def refresh(self):
	logging.debug("refresh()")
	self.updateCells()
	updated_count = self.redraw()
	logging.debug("redraw frequency: %f of %d cells at %f" % (self.redraw_cycle_time, updated_count, time.time()))
	logging.debug("update recv time: %f" % self.update_time_consumption)
	logging.debug("idle cell plot time: %f" % self.idle_time_consumption)
	logging.debug("updated cell plot time: %f" % self.redraw_time_consumption)
        self._updateDisplay()
	self.getCellUpdates()
	self.getConfigRequest()

def main(argv=[]):	
	logging.getLogger().setLevel(logging.INFO if DEBUG_DISPLAY else logging.INFO)

	pygame.init()
	pygame.mouse.set_visible(False)

	displayInfo = pygame.display.Info()
	if DEBUG_DISPLAY:
		displaySurface = pygame.display.set_mode((displayInfo.current_w, displayInfo.current_h))
	else:
		displaySurface = pygame.display.set_mode((displayInfo.current_w, displayInfo.current_h), pygame.FULLSCREEN)

	def quit_handler(signal, frame):
		logging.info("Interrupted")
		a.finish()

	signal.signal(signal.SIGINT, quit_handler)

	a = App(displaySurface, displayInfo)  
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
