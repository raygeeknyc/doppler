"Install tcl tk python-tkinter python-modules."

import collections
import logging
import update_message
import time
import threading
import Tkinter, random
import resource
import select
import signal
import socket
import string
import sys

HOST = ''                 # Symbolic name meaning the local host
MAXIMUM_CONFIG_MESSAGE_LEN = 512
MAXIMUM_UPDATE_MESSAGE_LEN = 3*1024

UPDATE_DELAY_MS = 10  # refresh 100 sec after events
MAX_REFRESH_RATE = 0.1  # UNUSED - Sleep this long after redrawing cells
CELL_IDLE_TIME = 4.0  # Set cells to idle after this many secs of inactivity

def MemUsedMB():
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return (usage[2]*resource.getpagesize())/1048576.0

def getPort():
	return update_message.RENDERER_PORT

class updateListener:
    pass

class PixelBlock:
    CELL_WIDTH = 14
    CELL_HEIGHT = 14
    CELL_MARGIN = 04

    def __init__(self, left, top):
      self.x = left
      self.y = top
      self.color = _NEUTRAL_COLOR
      self.image = None

    def setColor(self, rgb):
      self.color = tuple(rgb)

    def getColor(self):
      return self.color

    def draw(self):
      pass

    def getLeftTop(self):
      """Return x,y screen coord tuple."""
      return (self.x * self.CELL_WIDTH + self.CELL_MARGIN, self.y * self.CELL_HEIGHT + self.CELL_MARGIN)

    def getRightBottom(self):
      """Return x,y screen coord tuple."""
      return ((self.x + 1) * self.CELL_WIDTH - self.CELL_MARGIN, (self.y + 1) * self.CELL_HEIGHT - self.CELL_MARGIN)


_BRIGHTRED = (255,0,0)
_BRIGHTBLUE = (0,0,255)
_LIGHTGREY = (45,45,55)
_DIMBLUE = (50,50,150)
_DIMRED = (150,50,50)
_DIMGREY = (20,15,20)
_NEUTRAL_COLOR = (0,0,0)

CELL_COLORS = {
    update_message.CellState.CHANGE_APPROACH_SLOW: _DIMBLUE,
    update_message.CellState.CHANGE_APPROACH_FAST: _BRIGHTBLUE,
    update_message.CellState.CHANGE_RECEDE_SLOW: _DIMRED,
    update_message.CellState.CHANGE_RECEDE_FAST: _BRIGHTRED,
    update_message.CellState.CHANGE_REST: _LIGHTGREY,
    update_message.CellState.CHANGE_STILL: _DIMGREY}


class App:

    update_time_consumption = 0.0
    idle_time_consumption = 0.0
    redraw_time_consumption = 0.0
    redraw_cycle_timestamp = 0.0
    redraw_cycle_time = 0.0

    @staticmethod
    def _colorForState(state):
        """Return the color for state, neutral if the state is unknown."""
        try:
          return CELL_COLORS[state]
        except KeyError:
	  logging.error("Getting color for unknown state '%s'" % str(state))
          return _NEUTRAL_COLOR

    def __init__(self, master):
        pad = 0
        self._master = master
        self._screen_width = self._master.winfo_screenwidth()
        self._screen_height = self._master.winfo_screenheight()
        logging.debug("%d X %d pixels\n" % (self._screen_width, self._screen_height))
        self._master.geometry("{0}x{1}+0+0".format(self._screen_width-pad, self._screen_height-pad))
        self._master.overrideredirect(1)
        self._cols = self._screen_width / PixelBlock.CELL_WIDTH
        self._rows = self._screen_height / PixelBlock.CELL_HEIGHT                                          
        logging.debug("%d X %d cells\n" % (self._cols, self._rows))
        self._canvas = Tkinter.Canvas(self._master, width=self._screen_width,
                           height=self._screen_height, cursor="none", background='black')
        self._canvas.pack()                                                  
	self._cellUpdates = collections.deque()
        self._agingUpdates = []
        self._changedCells = []
        self.initializeCells()
	self.setAllCellsRandomly()
	self.setupPixels()
	logging.debug("Initial cell states set")
	self.initializeSockets()

    def initializeSockets(self):
	self._dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	self._dataSocket.bind((HOST, getPort()))
	self._dataSocket.setblocking(0)

	self._configConn = None
	self._configAddr = None
	self._configSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	self._configSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	self._configSocket.setblocking(1)
	self._configSocket.bind((HOST, getPort()))
	self._configSocket.setblocking(0)
	self._configSocket.listen(1)
	logging.debug("listening on port: %d" % getPort())

    def finish(self):
	logging.debug("Finishing. Closing all sockets")
	try:
		if self._dataSocket:
			logging.debug("Closing data connection")
			self._dataSocket.close()
	except:
		logging.exception("Error shutting down data socket")

	try:
		if self._configConn:
			logging.debug("Shutting down config connection")
			self._configConn.shutdown(socket.SHUT_RDWR)
			logging.debug("Closing config connection")
			self._configConn.close()
	except:
		logging.exception("Error shutting down config connection")
	try:
		if self._configSocket:
			logging.debug("Closing config socket")
			self._configSocket.close()
	except:
		logging.exception("Error closing config socket")

    def updateCell(self, cellState):
      """Change the cell described by cellState."""
      try:
        self._cells[cellState.x][cellState.y].setColor(App._colorForState(cellState.state))
        self._changedCells.append(self._cells[cellState.x][cellState.y])
      except:
        logging.exception("Error at %d,%d = %s" % (cellState.x,cellState.y,cellState.state))
    
    def initializeCells(self):
        """Set up the cells, no color set."""
        self._cells = {}
        for col in range(0, self._cols):
          col_cells = {}
          for row in range(0, self._rows):
            col_cells[row] = PixelBlock(col, row)     
          self._cells[col] = col_cells

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
	cellUpdates = [self.parseCellUpdateMessage(cellMessage) for cellMessage in updateData.split("|")]
	logging.debug("Generated %d cell updates: '%s'" % (len(cellUpdates), cellUpdates))
        self._cellUpdates.append(cellUpdates)
  
    def setupPixels(self):
        for col in range(0, self._cols):
          for row in range(0, self._rows):
	    cell = self._cells[col][row]
	    cell.image = self._canvas.create_rectangle(cell.getLeftTop()[0],
                          cell.getLeftTop()[1],
                          cell.getRightBottom()[0],
                          cell.getRightBottom()[1],
                          fill='#%02x%02x%02x' % cell.color
                         )

    def redraw(self):                          
        """Redraw all idle and then updated cells, remove cells from the idle and update lists."""
	App.redraw_cycle_time = time.time() - App.redraw_cycle_timestamp
        App.redraw_cycle_timestamp = time.time()

	start = time.time()
	stillColor = App._colorForState(update_message.CellState.CHANGE_STILL)
	while len(self._agingUpdates) > 0 and (self._agingUpdates[0][0] + CELL_IDLE_TIME) < start:
		idleExpiredTime, idleUpdates = self._agingUpdates.pop(0)

		for idleUpdate in idleUpdates:
	    		self._canvas.itemconfig(self._cells[idleUpdate.x][idleUpdate.y].image, fill='#%02x%02x%02x' % stillColor)
		self._canvas.update_idletasks()
	App.idle_time_consumption = (time.time() - start)

	start = time.time()
	prior_row = 0
	for cellToRefresh in self._changedCells:
	    self._canvas.itemconfig(cellToRefresh.image, fill='#%02x%02x%02x' % cellToRefresh.color)
	self._changedCells = []
	App.redraw_time_consumption = (time.time() - start)

    def getConfigRequest(self):
	configData = None
	if not self._configConn:
		try:
			self._configConn, self._configAddr = self._configSocket.accept()
		except:
       			pass
	if self._configConn:
       	       	try:
			logging.debug("Sending config")
			self._sendRendererConfig()
		except Exception as e:
			logging.error("Error %s sending config" % e)
		self._configConn.close()
		self._configConn = None
		self._configAddr = None

    def _sendRendererConfig(self):
	"Send our client the number of cols and rows we render."
	if not self._configConn:
		logging.error("No connection.")
		return
	logging.info("sending Configuration")
	self._configConn.send(str(self._cols)+","+str(self._rows))
	return

    def getCellUpdates(self):
	start = time.time()
	updateData = None
	try:
		updateData, addr = self._dataSocket.recvfrom(MAXIMUM_UPDATE_MESSAGE_LEN)
	except:
		#TODO: distinguish between resource not available and "real" errors
		pass
	if updateData:
		self._cellUpdates.append([self.parseCellUpdateMessage(cellMessage) for cellMessage in updateData.split("|")])
	App.update_time_consumption = (time.time() - start)

    def updateCells(self):
	now = time.time()
	while len(self._cellUpdates) > 0:
		updates = self._cellUpdates.popleft()
		for cellUpdate in updates:
			self.updateCell(cellUpdate)
		self._agingUpdates.append((now, updates))

    def refresh(self, root):
	self.updateCells()
	self.redraw()
	logging.info("redraw frequency: %f at %f" % (App.redraw_cycle_time, time.time()))
	logging.info("update recv time: %f" % App.update_time_consumption)
	logging.info("idle cell plot time: %f" % App.idle_time_consumption)
	logging.info("updated cell plot time: %f" % App.redraw_time_consumption)
	#time.sleep(MAX_REFRESH_RATE)
	root.after(UPDATE_DELAY_MS,self.refresh,root)

    def getRequests(self):
	while True:
		self.getCellUpdates()
		self.getConfigRequest()

    def startRequestService(self):
	self._updateThread = threading.Thread(target=self.getRequests)
	self._updateThread.daemon = True
	self._updateThread.start()

    def parseCellUpdateMessage(self, cellUpdateMessage):
	try:
		cellState = None
		(state,col,row) = cellUpdateMessage.split(",")
		return update_message.CellUpdate.fromText(state+","+str(col)+","+str(row))
	except:
		logging.warning("Error parsing cell update '%s'" % cellUpdateMessage)
		return None  # drop this update

    def expandCellUpdateMessage(self, cellUpdateMessage):
	# Not currently used by the plotter and expensive. See parseCellUpdate
	try:
		affectedCellStates = []
		(state,x,y) = cellUpdateMessage.split(",")
		if (x == "*"):
		  xStart = 0
		  xEnd = self._cols
		else:
		  xStart = int(x)
		  xEnd = int(x)+1
		if (y == "*"):
		  yStart = 0
		  yEnd = self._rows
		else:
		  yStart = int(y)
		  yEnd = int(y)+1
		for col in range(xStart, xEnd):
		  for row in range(yStart, yEnd):
		    affectedCellStates.append(update_message.CellUpdate.fromText(state+","+str(col)+","+str(row)))
	except:
		logging.warning("Error parsing cell update '%s'" % cellUpdateMessage)
		return []  # drop this update
	return affectedCellStates

logging.getLogger().setLevel(logging.DEBUG)
window_base = Tkinter.Tk()

def quit_handler(signal, frame):
	logging.info("Interrupted")
	window_base.quit()

signal.signal(signal.SIGINT, quit_handler)

logging.info("creating window %f" % time.time())
a = App(window_base)  
logging.info("Starting threads %f" % time.time())
a.startRequestService()
logging.info("Scheduling refresh %f" % time.time())
window_base.after(10, a.refresh(window_base))
try:
	window_base.mainloop()
	logging.info("Ending")
except Exception as e:
	logging.exception("Top level exception")
a.finish()
