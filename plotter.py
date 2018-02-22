"Install tcl tk python-tkinter python-modules."

import collections
import config
import errno
import logging
import update_message
import select
import socket
import string
import time
import zlib

# The minimum change in distance that is seen as a "fast" approach or recession
FAST_APPROACH_THRESHOLD = 22
FAST_RECEDE_THRESHOLD = -22
# The minimum change in distance that is seen as a "slow" approach or recession
SLOW_APPROACH_THRESHOLD = 7
SLOW_RECEDE_THRESHOLD = -7
# The minimum change in absolute distance that we see as motion
DISTANCE_MOTION_THRESHOLD = 6

# How many cell updates to send in one message to a renderer
#MAXIMUM_CELL_UPDATES_PER_MESSAGE = 300  # This should be < 1400 bytes
MAXIMUM_CELL_UPDATES_PER_MESSAGE = 1024

class Plotter:
    def cellStateForChange(self, distance_delta):
	if (distance_delta < FAST_RECEDE_THRESHOLD):
		return update_message.CellState.CHANGE_RECEDE_FAST
	if (distance_delta < SLOW_RECEDE_THRESHOLD):
		return update_message.CellState.CHANGE_RECEDE_SLOW
	if (distance_delta > FAST_APPROACH_THRESHOLD):
		return update_message.CellState.CHANGE_APPROACH_FAST
	if (distance_delta > SLOW_APPROACH_THRESHOLD):
		return update_message.CellState.CHANGE_APPROACH_SLOW
	return update_message.CellState.CHANGE_REST
	
    def updateCellState(self, x, y, distance):
	delta = self._cells[x][y][0] - distance
	if abs(delta) >= DISTANCE_MOTION_THRESHOLD:
		self._cells[x][y][1] = self.cellStateForChange(delta)
		self._cells[x][y][0] = distance
		self._cells[x][y][2] = True

    def _zoneCoordForLocalCell(self, globalCoordinate):
        "Return a tuple of two tuples which contain the zone coordinate and zone-specific coordinates for a global cell coordinate tuple(x,y)."
	return ((int(globalCoordinate[0] / self.PER_ZONE_CELL_DIMENSIONS[0]), int(globalCoordinate[1] / self.PER_ZONE_CELL_DIMENSIONS[1])), (globalCoordinate[0] % self.PER_ZONE_CELL_DIMENSIONS[0], globalCoordinate[1] % self.PER_ZONE_CELL_DIMENSIONS[1]))

    def __init__(self):
	logging.debug("initializing Plotter()")
	self._timeSending = 0
	self._cells = None
	self.PER_ZONE_CELL_DIMENSIONS = []
        self.ZONES = config.ZONES[0]*config.ZONES[1]
	self._zoneUpdates = []
	for col in xrange(config.ZONES[0]):
		col_coll = []
		for row in xrange(config.ZONES[1]):
			col_coll.append(collections.deque())
		self._zoneUpdates.append(col_coll)
	logging.debug("%d,%d renderers" % (config.ZONES[0], config.ZONES[1]))
	self.ROWS = None
	self.COLUMNS = None
	self._setupSocket()
	self._getFirstRendererConfig()

    def _setupSocket(self):
	self._updateSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _getFirstRendererConfig(self):
	for zone_x in xrange(config.ZONES[0]):
		for zone_y in xrange(config.ZONES[1]):
			zone = (zone_x, zone_y)
			try:
                                logging.info("querying config from "+str(zone))
				return self._getRendererConfig(zone)
			except:
				logging.exception("Error getting config for "+str(zone)+" trying next")
				continue
	raise Exception("No renderer configs found in zones: "+zones)

    def _getRendererConfig(self, zone):
	logging.debug("_getRendererConfig()")
	first_renderer_addr = self._getRendererAddress(zone[0], zone[1])
	logging.debug("Getting renderer config from %s" % first_renderer_addr)
	first_renderer = self._configConnection(first_renderer_addr)
	if not first_renderer:
		raise Exception("No renderer found at %s" % first_renderer_addr)
	configuration = ""
	buffer = ""
	waiting = True
	logging.debug("Getting configuration")
	while buffer or waiting:
		try:
			logging.debug("Getting configuration fragment")
			buffer = string.strip(first_renderer.recv(config.RENDERER_CONFIG_MAX_LENGTH))
			if buffer:
				logging.debug("Got configuration fragment '%s'" % buffer)
				configuration += buffer
			waiting = False
		except:
			logging.exception("Exception receiving")
			if not waiting:
				break
			pass
	self._closeRenderer(first_renderer)
	logging.info("Renderer sent %s" % configuration)
	if not self.PER_ZONE_CELL_DIMENSIONS:
		self._parseConfig(configuration)

    def initAllCellsStates(self, newDistanceValues):
	"[col][row] = distance."
	now = time.time()
	for col in range(0, self.COLUMNS):
		for row in range(0, self.ROWS):
			self._cells[col][row] = [newDistanceValues[col][row],
			  update_message.CellState.CHANGE_STILL, now, True]
	logging.debug("initAllCellsState set %d cols X %d rows, %d cells" % (len(self._cells), len(self._cells[0]), (len(self._cells) * len(self._cells[0]))))

    def _buildZoneUpdates(self):
        "Traverse pending updates and batch them by their destination zone."
	for zone_x in xrange(config.ZONES[0]):
		for zone_y in xrange(config.ZONES[1]):
			currentZoneUpdates = self._zoneUpdates[zone_x][zone_y]
			currentZoneUpdates.clear()
			for cell_x in xrange(self.PER_ZONE_CELL_DIMENSIONS[0]):
				x = zone_x * self.PER_ZONE_CELL_DIMENSIONS[0] + cell_x
				for cell_y in xrange(self.PER_ZONE_CELL_DIMENSIONS[1]):
					y = zone_y * self.PER_ZONE_CELL_DIMENSIONS[1] + cell_y
					if self._cells[x][y][2]:
	  					remoteCellUpdate = update_message.CellUpdate(self._cells[x][y][1], (cell_x, cell_y))
	  					currentZoneUpdates.append(remoteCellUpdate)
						self._cells[x][y][2] = False
	

    def _sendZoneUpdates(self):
	"Send pending zone updates."
	for zone_x in xrange(config.ZONES[0]):
		for zone_y in xrange(config.ZONES[1]):
			currentZoneUpdates = self._zoneUpdates[zone_x][zone_y]
			self._sendUpdatesForZone((zone_x, zone_y), currentZoneUpdates)

    def refreshCells(self):
	"Send pending cell updates, by row and column."

	# This does not interleave updates among zones, it builds all updates an then sends them
	# This may result in blockiness in update rendering across all
	# N renderers.
	self._buildZoneUpdates()
	self._sendZoneUpdates()
	logging.debug("Time sending %d" % self._timeSending)
	
    def sendTestUpdates(self, localCellStates):
	"Accumulate cellUpdates by zone, send per zone with transformed coordinates."
	if not localCellStates:
	  return
	zone = self._zoneCoordForLocalCell((localCellStates[0].x, localCellStates[0].y))[0]
        #logging.debug("ZONE %s" % str(zone))
	zoneUpdates = collections.deque()
	for localCellState in localCellStates:
	  remoteCellCoord = self._zoneCoordForLocalCell((localCellState.x, localCellState.y))
	  if remoteCellCoord[0] != zone or len(zoneUpdates) >= MAXIMUM_CELL_UPDATES_PER_MESSAGE:
	    self._sendUpdatesForZone(zone, zoneUpdates)
	    zoneUpdates.clear()
            zone = remoteCellCoord[0]
	  remoteCellUpdate = update_message.CellUpdate(localCellState.state, (remoteCellCoord[1][0], remoteCellCoord[1][1]))
	  zoneUpdates.append(remoteCellUpdate)
	self._sendUpdatesForZone(zone, zoneUpdates)

    def _sendUpdatesForZone(self, zone, cellStates):
	"Send the cellStates to the server at (zone) if we have an address for it."
	if len(cellStates):
		start = time.time()
		if config.broadcasts:
			renderers = config.broadcasts
			logging.info('Broadcasting to %s' % str(renderers))
		else:
			logging.debug('Not broadcasting')
			renderers = [self._getRendererAddress(zone[0], zone[1])]
			logging.debug('Sending to %s' % str(renderers))
		for renderer in renderers:
			logging.debug("Sending %d updates to zone %s address %s" % (len(cellStates), str(zone), renderer))
			if not renderer:
				logging.error("No renderer for zone %s" % str(zone))
			else:
				start = time.time()
				self._sendUpdatesToRenderer(renderer, cellStates)
				self._timeSending += (time.time() - start)
	else:
		logging.debug("Skipping empty updates for zone %s" % str(zone))
		pass

    def _closeRenderer(self, renderer):
	logging.debug("Closing connection to renderer %s" % str(renderer))
	renderer.close()
	
    def _sendUpdatesToRenderer(self, renderer, cellStates):
	seriesText = update_message.CellUpdate.seriesToText(cellStates)
	#logging.debug("Sending %d characters for %d updates" % (len(seriesText), len(cellStates)))
	#logging.debug("Update message is '%s'...'%s'" % (seriesText[0:min(len(seriesText),10)], seriesText[-min(len(seriesText),10):]))
	try:
		self._updateSocket.sendto(zlib.compress(seriesText, 9), (renderer, config.RENDERER_PORT))
	except:
		logging.exception("Error sending to '%s'" % renderer)

    def _getRendererAddress(self, col, row):
	rendererIndex = (config.RENDERER_ADDRESS_BASE_OCTET + 
	  config.ZONES[0] * row + col)
	address = config.RENDERER_ADDRESS_BASE + str(rendererIndex)
        #logging.debug("_getRendererAddress for %d,%d is %s." % (col, row, rendererIndex))
	return address

    def _configConnection(self, address):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setblocking(1)
	tries = 0
	while tries < config.MAXIMUM_RENDERER_CONNECT_RETRIES:
		tries += 1
		try:
			logging.debug("Attempt #%d to connect to %s:%d" % (tries, address, config.RENDERER_PORT))
			s.connect((address, config.RENDERER_PORT))
			logging.debug("connected")
			return s
		except Exception as e:
			if e.errno == errno.EINPROGRESS or e.errno ==  errno.EALREADY:
		  		_, writeables, in_error = select.select([], [s], [s], config.RENDERER_CONNECT_TIMEOUT_SECS) 
		  		if s not in writeables or s in in_error:
		    			logging.error("Socket for %s in error or not writeable" % address)
					return None
				else:
		    			logging.error("Socket for %s error '%s'" % (s, e))
	logging.error("Failed to connect to %s:%d" % (address, config.RENDERER_PORT))
	return None
	
    def _parseConfig(self, rendererConfig):
	logging.info("Received renderer config of %s" % rendererConfig)
	self.PER_ZONE_CELL_DIMENSIONS = [int(x) for x in rendererConfig.split(",")]
	self.ROWS=config.ZONES[1]*self.PER_ZONE_CELL_DIMENSIONS[1]
	self.COLUMNS=config.ZONES[0]*self.PER_ZONE_CELL_DIMENSIONS[0]
	# cell[x][y]=[distance, state, timestamp, refreshNeeded]
	self._cells=[]
	for col in range(0,self.COLUMNS):
		self._cells.append([])
		self._cells[col]=[]
		for row in range(0,self.ROWS):
			self._cells[col].append([None,None,None,None])

    def finish(self):
	logging.info("TODO closing sockets")

    def recordTestUpdates(self,testUpdates, baseCol, baseRow):
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_FAST, (baseCol, baseRow)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (baseCol+1, baseRow+1)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (baseCol+2, baseRow+2)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_RECEDE_SLOW, (baseCol+3, baseRow+3)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_APPROACH_SLOW, (baseCol+1, baseRow-1)))
	testUpdates.append(update_message.CellUpdate(update_message.CellState.CHANGE_APPROACH_SLOW, (baseCol-1, baseRow+1)))

    def testSetAllCells(self):
	self.setAllCellDistances(100)

    def setAllCellDistances(self, globalDistance):
	allCellDistances = []
	for col in range(0, self.COLUMNS):
		allCellDistances.append([])
		for row in range(0, self.ROWS):
			allCellDistances[col].append(globalDistance)
    	self.initAllCellsStates(allCellDistances)

    def testUpdateCellStates(self, baseCol, baseRow):
	col = baseCol
	for row in range(baseRow, baseRow+10):
		self.updateCellState(col, row, 10)
	col += 1
	for row in range(baseRow, baseRow+10):
		self.updateCellState(col, row, 90)
	col += 1
	for row in range(baseRow, baseRow+10):
		self.updateCellState(col, row, 110)
	col += 1
	for row in range(baseRow, baseRow+10):
		self.updateCellState(col, row, 190)
			
def repeatTests(reps):
	for i in range(0, reps):
		print i
		runTests()

def runTests():
	logging.getLogger().setLevel(logging.DEBUG)
	plotter = Plotter()
	logging.info("testSetAllCells")
	plotter.testSetAllCells()
	logging.info("%d COLUMNS and %d ROWS" % (plotter.COLUMNS, plotter.ROWS))
	logging.debug("%d X %d cells" % (len(plotter._cells), len(plotter._cells[0])))
	plotter.refreshCells()
	logging.info("testUpdateCellStates")
	plotter.testUpdateCellStates(19,7)
	plotter.testUpdateCellStates(3,8)
	plotter.testUpdateCellStates(10, plotter.ROWS-26)
	plotter.testUpdateCellStates(20, 5)
	plotter.testUpdateCellStates(plotter.COLUMNS-5, 5)
	start = time.time()
	plotter.refreshCells()
	logging.info("refresh took %d" % (time.time() - start))
	logging.info("recordTestUpdates")
	testUpdates = []
	plotter.recordTestUpdates(testUpdates,10,10)
	plotter.recordTestUpdates(testUpdates,20,8)
	plotter.recordTestUpdates(testUpdates,20,10)
	plotter.recordTestUpdates(testUpdates,25,10)
	plotter.recordTestUpdates(testUpdates,20,15)

	plotter.recordTestUpdates(testUpdates,23,11)
	plotter.recordTestUpdates(testUpdates,24,12)

	plotter.recordTestUpdates(testUpdates,25,11)
	plotter.recordTestUpdates(testUpdates,25,10)

	plotter.recordTestUpdates(testUpdates,25,21)
	plotter.recordTestUpdates(testUpdates,25,10)

	plotter.recordTestUpdates(testUpdates,15,11)
	plotter.recordTestUpdates(testUpdates,15,10)

	plotter.recordTestUpdates(testUpdates,16,11)
	plotter.recordTestUpdates(testUpdates,16,10)

	plotter.recordTestUpdates(testUpdates,16,11)
	plotter.recordTestUpdates(testUpdates,16,10)

	plotter.recordTestUpdates(testUpdates,16,11)
	plotter.recordTestUpdates(testUpdates,16,10)

	plotter.recordTestUpdates(testUpdates,17,11)
	plotter.recordTestUpdates(testUpdates,17,10)

	plotter.recordTestUpdates(testUpdates,17,11)
	plotter.recordTestUpdates(testUpdates,17,10)

	plotter.recordTestUpdates(testUpdates,18,11)
	plotter.recordTestUpdates(testUpdates,18,10)

	plotter.recordTestUpdates(testUpdates,plotter.COLUMNS-6, 3)

	start = time.time()
	plotter.sendTestUpdates(testUpdates)
	logging.info("sendTestUpdates took %d" % (time.time() - start))
