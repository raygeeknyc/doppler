"Install tcl tk python-tkinter python-modules."

import logging
import update_message
import Tkinter, random
import select
import signal
import socket
import string

HOST = ''                 # Symbolic name meaning the local host
MAXIMUM_UPDATE_MESSAGE_LEN = 256*1024

def getPort():
	return update_message.RENDERER_PORT

class updateListener:
    pass

class PixelBlock:
    CELL_WIDTH = 30
    CELL_HEIGHT = 30
    CELL_MARGIN = 2

    def __init__(self, left, top):
      self._left = left
      self._top = top

    def setColor(self, rgb):
      self._color = tuple(rgb)

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
_DIMBLUE = (50,50,150)
_DIMRED = (150,50,50)
_DIMGREY = (25,20,25)
_NEUTRAL_COLOR = (0,0,0)

CELL_COLORS = {
    update_message.CellState.CHANGE_APPROACH_SLOW: _DIMBLUE,
    update_message.CellState.CHANGE_APPROACH_FAST: _BRIGHTBLUE,
    update_message.CellState.CHANGE_RECEDE_SLOW: _DIMRED,
    update_message.CellState.CHANGE_RECEDE_FAST: _BRIGHTRED,
    update_message.CellState.CHANGE_STILL: _DIMGREY}


class App:

    @staticmethod
    def _colorForState(state):
        """Return the color for state, neutral if the state is unknown."""
        try:
          return CELL_COLORS[state]
        except KeyError:
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
	self.initializeSocket()
	self.setAllCellsRandomly()
	self.redraw()
	logging.debug("Initial cell states set")

    def initializeSocket(self):
	self._conn = None
	self._addr = None
	self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	self._socket.setblocking(1)
	self._socket.bind((HOST, getPort()))
	logging.debug("listening on port: %d" % getPort())
	self._socket.setblocking(0)
	self._socket.listen(1)

    def finish(self):
	logging.debug("Finishing. Closing all sockets")
	try:
		if self._conn:
			logging.debug("Shutting down connection")
			self._conn.shutdown(socket.SHUT_RDWR)
			logging.debug("Closing connection")
			self._conn.close()
	except:
		logging.exception("Error shutting down connection")
	try:
		if self._socket:
			logging.debug("Closing socket")
			self._socket.close()
	except:
		logging.exception("Error closing socket")

    def updateCell(self, cellState):
      """Change the cell described by cellState."""
      try:
        self._cells[cellState.x][cellState.y].setColor(App._colorForState(cellState.state))
        self._changedCells.append(self._cells[cellState.x][cellState.y])
      except:
        logging.exception("Error at %d,%d = %s" % (cellState.x,cellState.y,cellState.state))
    
    def initializeCells(self):
        """Set up the cells, initially color them randomly."""
        self._cells = {}
        for col in range(0, self._cols):
          col_cells = {}
          for row in range(0, self._rows):
            col_cells[row] = PixelBlock(col, row)     
          self._cells[col] = col_cells

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

        logging.debug("Updating %d cells" % len(self._changedCells))
        for cellToRefresh in self._changedCells:
            self._canvas.create_oval(cellToRefresh.getLeftTop()[0],
                                     cellToRefresh.getLeftTop()[1],
                                     cellToRefresh.getRightBottom()[0],
                                     cellToRefresh.getRightBottom()[1],
                                     fill='#%02x%02x%02x' % cellToRefresh.getColor()
                                    )
        self._changedCells = []
        self._canvas.pack()                                                  
                          
    def _sendRendererConfig(self):
	"Send our client the number of cols and rows we render."
	if not self._conn:
		logging.error("No connection.")
		return
	logging.info("sending Configuration")
	self._conn.send(str(self._cols)+","+str(self._rows))
	return

    def getUpdates(self, root):
	data = None
	if not self._conn:
		try:
			self._conn, self._addr = self._socket.accept()
		except:
            		pass
	else:

		data = ""
		buffer = ""
        	waiting = True
        	logging.debug("Waiting for request")
	        while buffer or waiting:
                	try:
				logging.debug("Getting request fragment")
				buffer = string.strip(self._conn.recv(MAXIMUM_UPDATE_MESSAGE_LEN))
				logging.debug("Received fragment of %d characters" % len(buffer))
               		        if buffer:
					logging.debug("request fragment is '%s'...'%s'" % (buffer[:10], buffer[-10:]))
                                	data += buffer
				if waiting:
					logging.debug("Stopping waiting, fragment is '%s'" % buffer)
	                        	waiting = False
				if data == update_message.SEND_CONFIG_COMMAND:
					logging.debug("Send config request was received")
					self._sendRendererConfig()
					data = ""
                	except:
                        	if not waiting:
					logging.debug("error after waiting, end of request")
                                	break
				else:
					logging.debug("Error while waiting")
                        	pass
		self._conn.close()
		logging.debug("Total request length is %d" % len(data))
		self._conn = None
		self._addr = None
		if data:
			cellUpdates = [self.expandCellUpdateMessage(cellMessage) for cellMessage in data.split("|")]
			for expandedCellUpdate in cellUpdates:
			  for cellUpdate in expandedCellUpdate:
			    self.updateCell(cellUpdate)
			self.redraw()
	root.after(UPDATE_DELAY_MS,self.getUpdates,root)


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
		logging.exception("Error parsing cell updates '%s'" % cellUpdateMessage)
	return affectedCellStates

logging.getLogger().setLevel(logging.INFO)
window_base = Tkinter.Tk()
def quit_handler(signal, frame):
	logging.debug("Interrupted")
	window_base.quit()

signal.signal(signal.SIGINT, quit_handler)

UPDATE_DELAY_MS = 10  # refresh 1/100 sec after events
a = App(window_base)  
window_base.after(0, a.getUpdates(window_base))
try:
	window_base.mainloop()
	logging.debug("Ending")
except Exception as e:
	logging.exception("Top level exception")
a.finish()
