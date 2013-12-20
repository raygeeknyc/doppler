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
MAXIMUM_UPDATE_MESSAGE_LEN = 256*1024

MIN_IDLE_UPDATE_FREQ = 1.0  # Only check for idle updates this frequently
UPDATE_DELAY_MS = 01  # refresh 1/1000 sec after events

CELL_IDLE_TIME = 5.0  # Set cells to idle after this many secs of inactivity

def MemUsedMB():
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return (usage[2]*resource.getpagesize())/1048576.0

def getPort():
	return update_message.RENDERER_PORT

class updateListener:
    pass

class PixelBlock:
    CELL_WIDTH = 11
    CELL_HEIGHT = 11
    CELL_MARGIN = 3

    def __init__(self, left, top):
      self._left = left
      self._top = top
      self.timestamp = None
      self.color = _NEUTRAL_COLOR
      self.image = None

    def setColor(self, rgb, timestamp=None):
      self.color = tuple(rgb)
      if timestamp == None:
      	self.timestamp = time.time()
      else:
        self.timestamp = timestamp

    def getTimeSinceUpdated(self):
      if self.timestamp:
          return time.time() - self.timestamp
      else:
          return None

    def getColor(self):
      return self.color

    def draw(self):
      pass

    def getX(self):
      """Return the X coord, not the X screen coord."""
      return self._left

    def getY(self):
       """Return the Y coord, not the Y screen coord."""
       return self._top

    def getLeftTop(self):
      """Return x,y screen coord tuple."""
      return (self._left * self.CELL_WIDTH + self.CELL_MARGIN, self._top * self.CELL_HEIGHT + self.CELL_MARGIN)

    def getRightBottom(self):
      """Return x,y screen coord tuple."""
      return ((self._left + 1) * self.CELL_WIDTH - self.CELL_MARGIN, (self._top + 1) * self.CELL_HEIGHT - self.CELL_MARGIN)


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
        self._changedCells = []  # keep this as a list, 10X+ faster than Queue
        self._agingCells = collections.deque()
        self._idleCells = collections.deque()
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

    def updateCell(self, cellState, timestamp=None):
      """Change the cell described by cellState."""
      try:
        self._cells[cellState.x][cellState.y].setColor(App._colorForState(cellState.state), timestamp)
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

    def ageIdleCells(self):
	"""Find previously updated cells which have been idle and put them on an aged queue."""
	while True:
		while len(self._agingCells) == 0:
			time.sleep(MIN_IDLE_UPDATE_FREQ)
     	 	agingCell = self._agingCells.popleft()
		remainingIdleTime =  CELL_IDLE_TIME - agingCell.getTimeSinceUpdated()
  		if remainingIdleTime > MIN_IDLE_UPDATE_FREQ:
			logging.info("Fetched non-expired update. waiting for %f" % remainingIdleTime)
			time.sleep(remainingIdleTime)
			logging.debug("woke at %f" % time.time())
		self._idleCells.append(agingCell)

    def setAllCellsRandomly(self):
        logging.debug("Setting all cells to random colors")

        for col in range(0, self._cols):
          for row in range(0, self._rows):
            cellState = update_message.CellUpdate.fromText(
              update_message.CellState.STATES[random.randint(0,len(update_message.CellState.STATES)-1)]+
              ","+str(col)+","+str(row))
            self.updateCell(cellState)
  
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
	while len(self._idleCells) > 0:
		idleCell = self._idleCells.popleft()
	    	self._canvas.itemconfig(idleCell.image, fill='#%02x%02x%02x' % stillColor)
	App.idle_time_consumption = (time.time() - start)

	start = time.time()
        for cellToRefresh in self._changedCells:
	    self._canvas.itemconfig(cellToRefresh.image, fill='#%02x%02x%02x' % cellToRefresh.color)
	    self._agingCells.append(cellToRefresh)
	App.redraw_time_consumption = (time.time() - start)
        self._changedCells = []
        self._canvas.pack()                                                  
                          
    def _sendRendererConfig(self):
	"Send our client the number of cols and rows we render."
	if not self._configConn:
		logging.error("No connection.")
		return
	logging.info("sending Configuration")
	self._configConn.send(str(self._cols)+","+str(self._rows))
	return

    def getConfigRequests(self):
	while True:
		configData = None
		if not self._configConn:
			try:
				self._configConn, self._configAddr = self._configSocket.accept()
			except:
      	      			pass
		else:
			configData = ""
			buffer = ""
       	 		waiting = True
      		  	logging.debug("Waiting for request")
			while buffer or waiting:
       		        	try:
					logging.debug("Getting config request fragment")
					buffer = string.strip(self._configConn.recv(MAXIMUM_CONFIG_MESSAGE_LEN))
					logging.debug("Received config fragment of %d characters" % len(buffer))
       		        	        if buffer:
						logging.debug("config request fragment is '%s'...'%s'" % (buffer[:10], buffer[-10:]))
      		                         	configData += buffer
					if waiting:
						logging.debug("Stopping waiting, config fragment is '%s'" % buffer)
			                       	waiting = False
					if configData == update_message.SEND_CONFIG_COMMAND:
						logging.debug("Send config request was received")
						self._sendRendererConfig()
						configData = ""
       		         	except:
      		                	if not waiting:
						logging.debug("error after waiting, end of config request")
       		                         	break
					else:
						logging.debug("Error while waiting for config request")
       			                 	pass
			self._configConn.close()
			logging.debug("Received config request length is %d" % len(configData))
			self._configConn = None
			self._configAddr = None

    def getCellUpdates(self):
	start = time.time()
	updateData = None
	try:
		updateData, addr = self._dataSocket.recvfrom(MAXIMUM_UPDATE_MESSAGE_LEN)
		logging.debug("Received update of %d length" % len(updateData))
	except:
		#TODO: distinguish between resource not available and "real" errors
		pass

	if updateData:
		cellUpdateTime = time.time()
		cellUpdates = [self.parseCellUpdateMessage(cellMessage) for cellMessage in updateData.split("|")]
		for cellUpdate in cellUpdates:
		    self.updateCell(cellUpdate, cellUpdateTime)
	App.update_time_consumption = (time.time() - start)

    def getRequests(self, root):
	self.getCellUpdates()
	self.redraw()
	logging.info("update time: %f" % App.update_time_consumption)
	logging.info("redraw frequency: %f" % App.redraw_cycle_time)
	logging.info("redraw time: %f" % App.redraw_time_consumption)
	logging.info("idle time: %f" % App.idle_time_consumption)
	root.after(UPDATE_DELAY_MS,self.getRequests,root)

    def startIdleService(self):
	self._ageIdleCellsThread = threading.Thread(target=self.ageIdleCells)
	self._ageIdleCellsThread.daemon = True
	self._ageIdleCellsThread.start()

    def startConfigService(self):
	self._configThread = threading.Thread(target=self.getConfigRequests)
	self._configThread.daemon = True
	self._configThread.start()

    def parseCellUpdateMessage(self, cellUpdateMessage):
	try:
		cellState = None
		(state,x,y) = cellUpdateMessage.split(",")
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

logging.getLogger().setLevel(logging.INFO)
window_base = Tkinter.Tk()
def quit_handler(signal, frame):
	logging.debug("Interrupted")
	window_base.quit()

signal.signal(signal.SIGINT, quit_handler)

a = App(window_base)  
window_base.after(0, a.startConfigService())
window_base.after(0, a.startIdleService())
window_base.after(0, a.getRequests(window_base))
try:
	window_base.mainloop()
	logging.debug("Ending")
except Exception as e:
	logging.exception("Top level exception")
a.finish()
