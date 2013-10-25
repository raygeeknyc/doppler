"Install tcl tk python-tkinter python-modules."

import errno
import logging
import update_message
import select
import socket
import string
import time

# The minimum change in distance that is seen as a "fast" approach or recession
FAST_THRESHOLD = 20
# The minimum change in distance that is seen as a "slow" approach or recession
SLOW_THRESHOLD = 05
# The minimum change in distance that we see as relevant motion
DISTANCE_MOTION_THRESHOLD = SLOW_THRESHOLD
# How many seconds we leave an object at rest before marking it as STILL
AT_REST_DURATION = 4

# We have 4 columns and 2 rows 
ZONES=[1,1]
MAXIMUM_UPDATES_IN_MESSAGE = 1200  # This is to protect the renderers from excessively long update strings
RENDERER_CONFIG_MAX_LENGTH = 1024

class Plotter:
    def cellStateForChange(self, old_distance, new_distance):
	if (new_distance - old_distance >= FAST_THRESHOLD):
		return update_message.CellState.CHANGE_RECEDE_FAST
	if (new_distance - old_distance >= SLOW_THRESHOLD):
		return update_message.CellState.CHANGE_RECEDE_SLOW
	if (old_distance - new_distance >= FAST_THRESHOLD):
		return update_message.CellState.CHANGE_APPROACH_FAST
	if (old_distance - new_distance >= SLOW_THRESHOLD):
		return update_message.CellState.CHANGE_APPROACH_SLOW
	return update_message.CellState.CHANGE_STILL
	
    def updateIdleCells(self, now):
	"Mark cells which most recently had motion but not recently as STILL."
	idleCellCount = 0
	activeCellCount = 0
	expiredCellCount = 0
	for col in range(0, self.COLUMNS):
		for row in range(0, self.ROWS):
	  		if (self._cells[col][row][1] != update_message.CellState.CHANGE_STILL):
				activeCellCount += 1
	  		if (now - self._cells[col][row][2] >= AT_REST_DURATION):
				expiredCellCount += 1
	  		if (now - self._cells[col][row][2] >= AT_REST_DURATION
	  			and self._cells[col][row][1] != update_message.CellState.CHANGE_STILL
				and not self._cells[col][row][3]):
					idleCellCount += 1
	  				self._cells[col][row][1] = update_message.CellState.CHANGE_STILL
					self._cells[col][row][2] = now
					self.markCellForRefresh(col, row)
	logging.debug("%d idle cells were updated" % idleCellCount)
	logging.debug("%d expired cells and %d non-still cells" % (expiredCellCount, activeCellCount))

    def updateCellState(self, x, y, distance, now):
	if (abs(self._cells[x][y][0] - distance) >= DISTANCE_MOTION_THRESHOLD):
		self._cells[x][y][1] = self.cellStateForChange(self._cells[x][y][0],distance)
		self._cells[x][y][0] = distance
		self._cells[x][y][2] = now
		self.markCellForRefresh(x,y)
		
    def markCellForRefresh(self, x, y):
	self._cells[x][y][3] = True

    def _zoneCoordForLocalCell(self, globalCoordinate):
        "Return a tuple of two tuples which contain the zone coordinate and zone-specific coordinates for a global cell coordinate tuple(x,y)."
	return ((int(globalCoordinate[0] / self.PER_ZONE_CELL_DIMENSIONS[0]), int(globalCoordinate[1] / self.PER_ZONE_CELL_DIMENSIONS[1])), (globalCoordinate[0] % self.PER_ZONE_CELL_DIMENSIONS[0], globalCoordinate[1] % self.PER_ZONE_CELL_DIMENSIONS[1]))

    def __init__(self):
        self._changedCells = []
	self.PER_ZONE_CELL_DIMENSIONS = []
	self.ROWS = None
	self.COLUMNS = None
	self._getRendererConfig((0,0))

    def _getRendererConfig(self, zone):
	first_renderer = self._getRendererAddress(zone[0], zone[1])
	logging.debug("Getting renderer config from %s" % first_renderer)
	first_renderer = self._rendererConnection(first_renderer)
	logging.debug("Sending config request to renderer %s" % str(first_renderer))
	first_renderer.send(update_message.SEND_CONFIG_COMMAND)
	logging.debug("sent config request")
	config = ""
	buffer = ""
	waiting = True
	logging.debug("Getting config")
	while buffer or waiting:
		try:
			buffer = string.strip(first_renderer.recv(RENDERER_CONFIG_MAX_LENGTH))
			if buffer:
				logging.debug("Got config fragment '%s'" % buffer)
				config += buffer
			waiting = False
		except:
			if not waiting:
				break
			pass
	self._closeRenderer(first_renderer)
	logging.debug("Renderer sent %s" % config)
	if not self.PER_ZONE_CELL_DIMENSIONS:
		self._parseConfig(config)

    def initAllCellsStates(self, newDistanceValues):
	"[col][row] = distance."
	now = time.time()
	for col in range(0, self.COLUMNS):
		for row in range(0, self.ROWS):
			self._cells[col][row] = [newDistanceValues[col][row],
			  update_message.CellState.CHANGE_STILL, now, True]
	logging.debug("initAllCellsState set %d cols X %d rows, %d cells" % (len(self._cells), len(self._cells[0]), (len(self._cells) * len(self._cells[0]))))

    def refreshCells(self):
	"Send pending updates, by column and row."

	# This will interleave updates among zones so that all zones with pending
	# updates in local row 0 will be sent those updates before any of row 1
	# are sent. This will reduce blockiness in updates but assumes the local
	# renderers to be faster at receiving their updates than they are at
	# parsing and rendering them.

	currentZone =  self._zoneCoordForLocalCell((0, 0))[0]
	currentZoneUpdates = []
	for row in range(0, self.ROWS):
		for col in range(0, self.COLUMNS):
			if self._cells[col][row][3]:
				# logging.debug("Cell %d,%d refresh flag %s" % (col, row, self._cells[col][row][3]))
				remoteCellCoord = self._zoneCoordForLocalCell((col, row))
				if (len(currentZoneUpdates) >= MAXIMUM_UPDATES_IN_MESSAGE):
					logging.debug("Break on maximum number of updates in message %d" % len(currentZoneUpdates))
					self._sendUpdatesForZone(currentZone, currentZoneUpdates)
					currentZoneUpdates = []
				if (remoteCellCoord[0] != currentZone):
					logging.debug("Break on zone %s -> %s" % (str(currentZone), str(remoteCellCoord[0])))
					self._sendUpdatesForZone(currentZone, currentZoneUpdates)
					currentZoneUpdates = []
					currentZone = remoteCellCoord[0]
	  			remoteCellUpdate = update_message.CellUpdate(self._cells[col][row][1], (remoteCellCoord[1][0], remoteCellCoord[1][1]))
	  			currentZoneUpdates.append(remoteCellUpdate)
				self._cells[col][row][3] = False
	self._sendUpdatesForZone(currentZone, currentZoneUpdates)
	
    def sendTestUpdates(self, localCellStates):
	"Accumulate cellUpdates by zone, send per zone with transformed coordinates."
	if not localCellStates:
	  return
	zone = self._zoneCoordForLocalCell((localCellStates[0].x, localCellStates[0].y))[0]
        logging.debug("ZONE %s" % str(zone))
	zoneUpdates = []
	for localCellState in localCellStates:
	  remoteCellCoord = self._zoneCoordForLocalCell((localCellState.x, localCellState.y))
	  if remoteCellCoord[0] != zone:
	    self._sendUpdatesForZone(zone, zoneUpdates)
	    zoneUpdates = []
	  remoteCellUpdate = update_message.CellUpdate(localCellState.state, (remoteCellCoord[1][0], remoteCellCoord[1][1]))
	  zoneUpdates.append(remoteCellUpdate)
	self._sendUpdatesForZone(zone, zoneUpdates)

    def _sendUpdatesForZone(self, zone, cellStates):
	"Send the cellStates to the server at (zone) if we have a connection to it."
	if cellStates:
		logging.debug("Sending %d updates to zone %s" % (len(cellStates), str(zone)))
		renderer = self._rendererConnection(self._getRendererAddress(zone[0], zone[1]))
		if not renderer:
			logging.error("No connection to renderer for zone %s" % str(zone))
		else:
			self._sendUpdatesToRenderer(renderer, cellStates)
			self._closeRenderer(renderer)
	else:
		logging.debug("Skipping empty updates for zone %s" % str(zone))

    def _closeRenderer(self, renderer):
	logging.debug("Closing connection to renderer %s" % str(renderer))
	renderer.close()
	
    def _sendUpdatesToRenderer(self, renderer, cellStates):
	seriesText = update_message.CellUpdate.seriesToText(cellStates)
	logging.debug("Sending %d characters" % len(seriesText))
	logging.debug("Update message is '%s'...'%s'" % (seriesText[0:min(len(seriesText),10)], seriesText[-min(len(seriesText),10):]))
	renderer.send(seriesText)

    def _getRendererAddress(self, col, row):
	rendererIndex = (update_message.RENDERER_ADDRESS_BASE_OCTET + 
	  ZONES[1] * row + col)
	address = update_message.RENDERER_ADDRESS_BASE + str(rendererIndex)
	return address

    def _rendererConnection(self, address):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setblocking(0)
	tries = 0
	while tries < update_message.MAXIMUM_RENDERER_CONNECT_RETRIES:
		tries += 1
		try:
			logging.debug("Attempt #%d to connect to %s:%d" % (tries, address, update_message.RENDERER_PORT))
			s.connect((address, update_message.RENDERER_PORT))
			return s
		except Exception as e:
			if e.errno == errno.EINPROGRESS or e.errno ==  errno.EALREADY:
		  		_, writeables, in_error = select.select([], [s], [s], update_message.RENDERER_CONNECT_TIMEOUT_SECS) 
		  		if s not in writeables or s in in_error:
		    			logging.error("Socket for %s in error or not writeable" % address)
				else:
					return s
	logging.error("Failed to connect to %s:%d" % (address, update_message.RENDERER_PORT))
	return None
	
    def _parseConfig(self, rendererConfig):
	logging.info("Received renderer config of %s" % rendererConfig)
	self.PER_ZONE_CELL_DIMENSIONS = [int(x) for x in rendererConfig.split(",")]
	self.ROWS=ZONES[1]*self.PER_ZONE_CELL_DIMENSIONS[1]
	self.COLUMNS=ZONES[0]*self.PER_ZONE_CELL_DIMENSIONS[0]
	# cell[x][y]=[distance, state, timestamp, refreshNeeded]
	self._cells=[]
	for col in range(0,self.COLUMNS):
		self._cells.append([])
		self._cells[col]=[]
		for row in range(0,self.ROWS):
			self._cells[col].append([None,None,None,None])

    def finish(self):
	logging.info("TODO closing sockets")

    def testSendUpdates(self):
	testUpdates = []
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (0, 0)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (0, 1)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (0, 2)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (0, 3)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (0, 4)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (self.COLUMNS-3, 0)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (self.COLUMNS-2, 0)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (self.COLUMNS-1, 0)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (0, self.ROWS-3)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (0, self.ROWS-2)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (0, self.ROWS-1)))

	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_APPROACH_FAST, (10, 10)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (10, 11)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (11, 10)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (11, 11)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (12, 12)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (13, 13)))
	self.sendTestUpdates(testUpdates)
	testUpdates = []
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_APPROACH_FAST, (20, 20)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (20, 21)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (21, 20)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (21, 21)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (22, 22)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (23, 23)))
	self.sendTestUpdates(testUpdates)

    def testSetAllCells(self):
	self.setAllCellDistances(100)

    def setAllCellDistances(self, globalDistance):
	allCellDistances = []
	for col in range(0, self.COLUMNS):
		allCellDistances.append([])
		for row in range(0, self.ROWS):
			allCellDistances[col].append(globalDistance)
    	self.initAllCellsStates(allCellDistances)

    def testUpdateCellStates(self):
	now = time.time()
	col = 3
	for row in range(0,10):
		self.updateCellState(col, row, 10, now)
	col += 1
	for row in range(0,10):
		self.updateCellState(col, row, 90, now)
	col += 1
	for row in range(0,10):
		self.updateCellState(col, row, 110, now)
	col += 1
	for row in range(0,10):
		self.updateCellState(col, row, 190, now)
			
def runTests():
	logging.getLogger().setLevel(logging.INFO)
	plotter = Plotter()
	logging.info("testSetAllCells")
	plotter.testSetAllCells()
	logging.info("%d COLUMNS and %d self.ROWS" % (plotter.COLUMNS, plotter.ROWS))
	logging.debug("%d X %d cells" % (len(plotter._cells), len(plotter._cells[0])))
	plotter.refreshCells()
	time.sleep(2)
	logging.info("testUpdateCellStates")
	plotter.testUpdateCellStates()
	plotter.refreshCells()
	logging.info("testSendUpdates")
	plotter.testSendUpdates()
	plotter.refreshCells()
	time.sleep(1)
	logging.info("updateIdleCells")
	plotter.updateIdleCells(time.time())
	plotter.refreshCells()
	time.sleep(1)
	logging.info("updateIdleCells")
	plotter.updateIdleCells(time.time())
	plotter.refreshCells()
	time.sleep(1)
	logging.info("updateIdleCells")
	plotter.updateIdleCells(time.time())
	plotter.refreshCells()
	time.sleep(1)
	logging.info("updateIdleCells")
	plotter.updateIdleCells(time.time())
	plotter.refreshCells()
	time.sleep(1)
	logging.info("updateIdleCells")
	plotter.updateIdleCells(time.time())
	plotter.refreshCells()
	time.sleep(1)
	logging.info("updateIdleCells")
	plotter.updateIdleCells(time.time())
	plotter.refreshCells()
	time.sleep(1)
	logging.info("updateIdleCells")
	plotter.updateIdleCells(time.time())
	plotter.refreshCells()
	time.sleep(1)
	logging.info("updateIdleCells")
	plotter.updateIdleCells(time.time())
	plotter.refreshCells()
