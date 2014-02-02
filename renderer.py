"Install tcl tk python-modules pygame."

import collections
import logging
import pygame
from pygame.locals import *
import update_message
import time
import threading
import random
import resource
import select
import signal
import socket
import string
import sys

if len(sys.argv) > 1 and sys.argv[1] == "debug":
	DEBUG_DISPLAY=True
else:
	DEBUG_DISPLAY=False

HOST = ''  # Symbolic name meaning the local host
MAXIMUM_UPDATE_MESSAGE_LEN = 3*1024

CELL_IDLE_TIME = 2.0  # Set cells to idle after this many secs of inactivity

MAINLOOP_DELAY = 0.01  # Dirty way to avoid starving our request thread

# The maximum number of idle cells to age when there are pending updates
MAX_AGED_PER_REDRAW = 900

def MemUsedMB():
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return (usage[2]*resource.getpagesize())/1048576.0

def getPort():
	return update_message.RENDERER_PORT

class PixelBlock:
    CELL_WIDTH = 13  # This is a Pixels horizontal pitch
    CELL_HEIGHT = 13  # This is a Pixels vertical pitch
    CELL_MARGIN = 03  # This is the padding within a Pixel
    CELL_PLOT_WIDTH = CELL_WIDTH - CELL_MARGIN * 2
    CELL_PLOT_HEIGHT = CELL_HEIGHT - CELL_MARGIN * 2

    def __init__(self, left, top):
      self.plot_x = left * PixelBlock.CELL_WIDTH + PixelBlock.CELL_MARGIN
      self.plot_y = top * PixelBlock.CELL_HEIGHT + PixelBlock.CELL_MARGIN
      self.color = _NEUTRAL_COLOR

_BRIGHTRED = (255,50,50)
_BRIGHTBLUE = (50,50,255)
_LIGHTGREY = (45,45,55)
_DIMBLUE = (45,45,120)
_DIMRED = (120,45,45)
_DIMGREY = (20,15,20)

CELL_COLORS = {
    update_message.CellState.CHANGE_APPROACH_SLOW: _DIMBLUE,
    update_message.CellState.CHANGE_APPROACH_FAST: _BRIGHTBLUE,
    update_message.CellState.CHANGE_RECEDE_SLOW: _DIMRED,
    update_message.CellState.CHANGE_RECEDE_FAST: _BRIGHTRED,
    update_message.CellState.CHANGE_REST: _LIGHTGREY,
    update_message.CellState.CHANGE_STILL: _DIMGREY}
_NEUTRAL_COLOR = (0,0,0)


class App:
    update_time_consumption = 0.0
    idle_time_consumption = 0.0
    redraw_time_consumption = 0.0
    redraw_cycle_timestamp = 0.0
    redraw_cycle_time = 0.0

    @staticmethod
    def _colorForState(state):
        """Return the color for state."""
        return CELL_COLORS[state]

    def __init__(self, info, surface):
        self._surface = surface
        self._display_info = info
        self._screen_width = displayInfo.current_w
        self._screen_height = displayInfo.current_h
        logging.debug("%d X %d pixels\n" % (self._screen_width, self._screen_height))
        self._cols = self._screen_width / PixelBlock.CELL_WIDTH
        self._rows = self._screen_height / PixelBlock.CELL_HEIGHT                                          
        logging.debug("%d X %d cells\n" % (self._cols, self._rows))
	self._cellUpdates = collections.deque()
        self._agingUpdates = collections.deque()
        self._changedCells = collections.deque()
        self.initializeCells()
	self.setAllCellsRandomly()
	logging.debug("Initial cell states set")
	self.initializeSockets()
	self.startRequestService()

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
        self._cells = []
        for col in range(0, self._cols):
          col_cells = []
          for row in range(0, self._rows):
            col_cells.append(PixelBlock(col, row))
          self._cells.append(col_cells)

    def _dumpCells(self):
        for col in range(0, self._cols):
          for row in range(0, self._rows):
	    if self._cells[col][row].color != App._colorForState(update_message.CellState.CHANGE_STILL):
	      logging.debug("cell %d,%d color is %s" % (col, row, self._cells[col][row].color))

    def setAllCellsRandomly(self):
        logging.debug("Setting all cells to random colors")
	updateData = ""

        for row in range(0, self._rows):
          for col in range(0, self._cols):
	      updateData += (update_message.CellState.STATES[random.randint(0,len(update_message.CellState.STATES)-1)]+
                ","+str(col)+","+str(row)+"|")
	updateData = updateData[:-1]
	cellUpdates = [update_message.CellUpdate.fromText(cellMessage) for cellMessage in updateData.split("|")]
        self._cellUpdates.append(cellUpdates)
  
    def redraw(self):                          
        """Redraw all idle and then updated cells, remove cells from the idle and update lists."""
	App.redraw_cycle_time = time.time() - App.redraw_cycle_timestamp
        App.redraw_cycle_timestamp = time.time()

	start = time.time()
	stillColor = App._colorForState(update_message.CellState.CHANGE_STILL)
	cells_aged = 0
	while len(self._agingUpdates) and (self._agingUpdates[0][0] + CELL_IDLE_TIME) < start:
		if ((cells_aged > MAX_AGED_PER_REDRAW) and len(self._changedCells)):
			break
		idleExpiredTime, idleUpdate = self._agingUpdates.popleft()
		pygame.draw.rect(self._surface, stillColor, (idleUpdate.plot_x, idleUpdate.plot_y, PixelBlock.CELL_PLOT_WIDTH, PixelBlock.CELL_PLOT_HEIGHT))
		cells_aged += 1
	App.idle_time_consumption = (time.time() - start)

	start = time.time()
	while len(self._changedCells):
	    cellToRefresh = self._changedCells.popleft()
	    pygame.draw.rect(self._surface, cellToRefresh.color, (cellToRefresh.plot_x, cellToRefresh.plot_y, PixelBlock.CELL_PLOT_WIDTH, PixelBlock.CELL_PLOT_WIDTH))
	    self._agingUpdates.append((start, cellToRefresh))
	App.redraw_time_consumption = (time.time() - start)

    def getConfigRequest(self):
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
	connection.send(str(self._cols)+","+str(self._rows))

    def getCellUpdates(self):
	start = time.time()
	updateData = None
	if not self._dataSocket:
		logging.error("No data socket")
	try:
		updateData, addr = self._dataSocket.recvfrom(MAXIMUM_UPDATE_MESSAGE_LEN)
	except:
		#TODO: distinguish between resource not available and "real" errors
		pass
	if updateData:
		cellUpdates = [update_message.CellUpdate.fromText(cellMessage) for cellMessage in updateData.split("|")]
		self._cellUpdates.append(cellUpdates)
	App.update_time_consumption = (time.time() - start)

    def updateCells(self):
	now = time.time()
	while len(self._cellUpdates):
		updates = self._cellUpdates.popleft()
		for cellUpdate in updates:
      			self._cells[cellUpdate.x][cellUpdate.y].color = App._colorForState(cellUpdate.state)
		      	self._changedCells.append(self._cells[cellUpdate.x][cellUpdate.y])

    def refresh(self):
	self.updateCells()
	self.redraw()
	logging.info("redraw frequency: %f at %f" % (App.redraw_cycle_time, time.time()))
	logging.info("update recv time: %f" % App.update_time_consumption)
	logging.info("idle cell plot time: %f" % App.idle_time_consumption)
	logging.info("updated cell plot time: %f" % App.redraw_time_consumption)
	pygame.display.update()


    def getRequests(self):
	logging.debug("In request thread")
	while True:
		self.getCellUpdates()
		self.getConfigRequest()

    def startRequestService(self):
	logging.info("Starting request thread")
	self._requestThread = threading.Thread(target=self.getRequests, name="requests")
	self._requestThread.daemon = True
	self._requestThread.start()


logging.getLogger().setLevel(logging.DEBUG)

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

a = App(displayInfo, displaySurface)  
while True:
	try:
		a.refresh()
		time.sleep(MAINLOOP_DELAY)
	except Exception as e:
		logging.exception("Top level exception")
		a.finish()
a.finish()
