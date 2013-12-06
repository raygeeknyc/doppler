"Install tcl tk python-tkinter python-modules."

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

UPDATE_DELAY_MS = 02  # refresh 1/500 sec after events

CELL_IDLE_TIME = 4.0  # Set cells to idle after 4 secs of inactivity

def MemUsedMB():
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return (usage[2]*resource.getpagesize())/1048576.0

def getPort():
	return update_message.RENDERER_PORT

class updateListener:
    pass

class PixelBlock:
    CELL_WIDTH = 15
    CELL_HEIGHT = 15
    CELL_MARGIN = 0

    def __init__(self, left, top):
      self._left = left
      self._top = top
      self._timestamp = None
      self.setColor((0,0,0))

    def setColor(self, rgb):
      self._color = tuple(rgb)
      self._timestamp = time.time()

    def getTimeStamp(self):
      return self._timestamp

    def getTimeSinceUpdated(self):
      if self._timestamp:
          return time.time() - self._timestamp
      else:
          return None

    def getColor(self):
      return self._color

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

    redraw_mem_consumption_1 = 0.0
    redraw_mem_consumption_2 = 0.0

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
        self._changedCells = []
        self.initializeCells()
	self.setAllCellsRandomly()
	self.redraw()
	logging.debug("redraw max mem usage: %f,%f" % (App.redraw_mem_consumption_1, App.redraw_mem_consumption_2))
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
	    if self._cells[col][row].getColor() != App._colorForState(update_message.CellState.CHANGE_STILL):
	      logging.debug("cell %d,%d color is %s" % (col, row, self._cells[col][row].getColor()))

    def ageIdleCells(self):
	idleCount = 0
	nonStillCount = 0
        for col in range(0, self._cols):
          for row in range(0, self._rows):
	    if self._cells[col][row].getTimeSinceUpdated() and self._cells[col][row].getColor() != App._colorForState(update_message.CellState.CHANGE_STILL) and (self._cells[col][row].getTimeSinceUpdated() > CELL_IDLE_TIME):
	      #logging.debug("cell %d,%d age is %d" % (col, row, self._cells[col][row].getTimeSinceUpdated()))
	      nonStillCount += 1
	    if (self._cells[col][row].getTimeSinceUpdated() and
	      self._cells[col][row].getColor() != 
    	      App._colorForState(update_message.CellState.CHANGE_STILL) and
	      self._cells[col][row].getTimeSinceUpdated() > CELL_IDLE_TIME):
		cellUpdate = update_message.CellUpdate(update_message.CellState.CHANGE_STILL, (col, row))
                self.updateCell(cellUpdate)
	        idleCount += 1

    def setAllCellsRandomly(self):
        logging.debug("Setting all cells to random colors")

        for col in range(0, self._cols):
          for row in range(0, self._rows):
            cellState = update_message.CellUpdate.fromText(
              update_message.CellState.STATES[random.randint(0,len(update_message.CellState.STATES)-1)]+
              ","+str(col)+","+str(row))
            self.updateCell(cellState)
  
    def redraw(self):                          
        """Redraw all updated cells, remove cells from the update list."""
	mem = MemUsedMB()
	self._canvas.delete("all")

        for cellToRefresh in self._changedCells:
            self._canvas.create_oval(cellToRefresh.getLeftTop()[0],
                                     cellToRefresh.getLeftTop()[1],
                                     cellToRefresh.getRightBottom()[0],
                                     cellToRefresh.getRightBottom()[1],
                                     fill='#%02x%02x%02x' % cellToRefresh.getColor()
                                    )
	App.redraw_mem_consumption_1 = max((MemUsedMB() - mem), App.redraw_mem_consumption_1)
        self._changedCells = []
        self._canvas.pack()                                                  
        
	App.redraw_mem_consumption_2 = max((MemUsedMB() - mem), App.redraw_mem_consumption_2)
                          
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
	try:
		updateData, addr = self._dataSocket.recvfrom(MAXIMUM_UPDATE_MESSAGE_LEN)
		logging.debug("Received update of %d length" % len(updateData))
	except:
		#TODO: distinguish between resource not available and "real" errors
		updateData = None
		pass

	if updateData:
		cellUpdates = [self.expandCellUpdateMessage(cellMessage) for cellMessage in updateData.split("|")]
		for expandedCellUpdate in cellUpdates:
		  for cellUpdate in expandedCellUpdate:
		    self.updateCell(cellUpdate)

    def getRequests(self, root):
	self.getCellUpdates()
	self.ageIdleCells()
	self.redraw()
	logging.debug("redraw max mem usage: %f,%f" % (App.redraw_mem_consumption_1, App.redraw_mem_consumption_2))
	root.after(UPDATE_DELAY_MS,self.getRequests,root)

    def startConfigService(self):
	self._configThread = threading.Thread(target=self.getConfigRequests)
	self._configThread.daemon = True
	self._configThread.start()

    def expandCellUpdateMessage(self, cellUpdateMessage):
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
	logging.debug("Interrupted")
	window_base.quit()

signal.signal(signal.SIGINT, quit_handler)

a = App(window_base)  
window_base.after(0, a.startConfigService())
window_base.after(0, a.getRequests(window_base))
try:
	window_base.mainloop()
	logging.debug("Ending")
except Exception as e:
	logging.exception("Top level exception")
a.finish()
