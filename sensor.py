#!/usr/bin/env python
"Install install freenect libusb libusb=dev libusb-dev libfreenect-demos python-freenect python-numpy python-support python-opencv python-matplotib python-matplotlib"

"Find numpy to change sampling method."

"Test with import sensor;reload(sensor)"

import copy
import errno
import freenect
import logging
import numpy
import random
import plotter
import time

#SAMPLER = numpy.mean
SAMPLER = numpy.median

# The margin to cut out of the right side of the left sensor's map
LEFT_OVERLAP_COLUMNS = 0
# The margin to cut out of the left side of the right sensor's map
RIGHT_OVERLAP_COLUMNS = 0
# The known width of a sensor's depth map
SENSOR_COLUMNS = 640
# The known height of a sensor's depth map
SENSOR_ROWS = 480

# Precompute these for speed, we use them often
LEFT_SENSOR_EDGE = SENSOR_COLUMNS - LEFT_OVERLAP_COLUMNS
RIGHT_SENSOR_EDGE = LEFT_SENSOR_EDGE + SENSOR_COLUMNS

# The total number of columns in the stitched sensor maps
STITCHED_COLUMNS = RIGHT_SENSOR_EDGE + SENSOR_COLUMNS - RIGHT_OVERLAP_COLUMNS
# The total number of rows in the stitched sensor maps
STITCHED_ROWS = SENSOR_ROWS

# When simulating Kinect sensor depths, these are the lower and upper bounds for random values
TEST_CLOSEST_DISTANCE = 50
TEST_FARTHEST_DISTANCE = 1050


def getDummyDepthMap():
	dummy_map = []
	for col in range(0, SENSOR_COLUMNS):
		dummy_map.append([])
		for row in range(0, SENSOR_ROWS):
			dummy_map[col].append(random.randrange(TEST_CLOSEST_DISTANCE, TEST_FARTHEST_DISTANCE))
	return dummy_map, time.time()
			
class Stitcher(object):
	def __init__(self, kinect_left_index, kinect_center_index, kinect_right_index, overlap_cols_margin_left, overlap_cols_margin_right, testing = True):
	
		self._testing = testing

		self._kinect_left = kinect_left_index
		self._kinect_center = kinect_center_index
		self._kinect_right = kinect_right_index

		self._depth_left = []
		self._depth_center = []
		self._depth_right = []

		# Get initial depth maps
		self.getSensorDepthMaps()

		logging.info('Sensor Depth[%d],[%d]' % (len(self._depth_center) ,len(self._depth_center[0])))

	def getDepthAtVirtualCell(self, spot_subcol, spot_subrow):
		"Return the value at the mapped cell from the 3 individual sensor depth maps."
		if spot_subcol < LEFT_SENSOR_EDGE:
			depth_map = self._depth_left
			depth_col = spot_subcol
		elif spot_subcol < RIGHT_SENSOR_EDGE:
			depth_map = self._depth_center
			depth_col = spot_subcol - LEFT_SENSOR_EDGE
		else:
			depth_map = self._depth_right
			depth_col = spot_subcol - (LEFT_SENSOR_EDGE + SENSOR_COLUMNS)
		#logging.debug("actual cell coord is %d,%d" % (depth_col, spot_subrow))
		#logging.debug("whose value is %d" % depth_map[depth_col][spot_subrow])
		#logging.debug("map is %d,%d" % (len(depth_map), len(depth_map[0])))
		return depth_map[spot_subrow][depth_col]

	def getSensorDepthMaps(self):
		if len(self._depth_left):
			self._old_depth_left, self._old_depth_timestamp_left = self._depth_left, self._depth_timestamp_left
			self._old_depth_center, self._old_depth_timestamp_center = self._depth_center, self._depth_timestamp_center
			self._old_depth_right, self._old_depth_timestamp_right = self._depth_right, self._depth_timestamp_right
		if not self._testing:
			logging.debug("Getting depth maps from 3 sensors")
			logging.debug("sensor %d"  % self._kinect_left)
			self._depth_left, self._depth_timestamp_left = freenect.sync_get_depth(self._kinect_left)
			logging.debug("done")
			logging.debug("sensor %d"  % self._kinect_center)
			self._depth_center, self._depth_timestamp_center = freenect.sync_get_depth(self._kinect_center)
			logging.debug("done")
			logging.debug("sensor %d"  % self._kinect_right)
			self._depth_right, self._depth_timestamp_right = freenect.sync_get_depth(self._kinect_right)
			logging.debug("done")
		else:
			logging.debug("Getting 3 dummy depth maps")
			start = time.time()
			self._depth_left, self._depth_timestamp_left = getDummyDepthMap()
			self._depth_center, self._depth_timestamp_center = getDummyDepthMap()
			self._depth_right, self._depth_timestamp_right = getDummyDepthMap()
			logging.debug("Generated maps in %f secs" % (time.time() - start))

	def plotMappedDepths(self, now):
		"""
		Send updates to the plotters depth map, from the stitched sensor maps,
		using the min of sensor cells that correspond to each plotter cell.
		Horizontally flip the plotter map since the libfreenect library is flipping the depth stream, as mentioned in release notes.
		It should be OK to flip at this coarse level as we are averaging the sensor points around a given cell so the orientation
		within a cell's sensor cells should not matter.
		"""
		logging.debug("calculating depths for %d,%d cells" % (self.plotter.COLUMNS, self.plotter.ROWS))
		for spot_col in range(0, self.plotter.COLUMNS):
			flipped_col = self.plotter.COLUMNS - 1 - spot_col
			spot_row = 0.0
			for spot_row in range(0, self.plotter.ROWS):
				#logging.debug("virtual cell %d,%d" % (flipped_col, spot_row))
				spot_area, spot_depth = self.calculateMergedDepth(flipped_col, spot_row)
				#logging.debug("Plotter cell %d,%d: area %d, depth %d" % (spot_col, spot_row, spot_area, spot_depth))
				self.plotter.updateCellState(spot_col, spot_row, spot_depth, now)
				
	def calculateMergedDepth(self, col, row):
		"Calculate the depth at a plotter map's cell using the median of sensor cells that correspond to each plotter cell."
		global SAMPLER
		#logging.debug("Calculating merged depth for %d,%d" % (col, row))
		spot_col_start = int(col * self.COLUMN_SCALING_FACTOR)
		spot_col_end = spot_col_start + int(self.COLUMN_SCALING_FACTOR)
		#logging.debug("Cell col maps to (%d:%d)" % (spot_col_start, spot_col_end))
		spot_samples = []
		# for spot_subcol in range(min(STITCHED_COLUMNS-1,spot_col_start), min(spot_col_end+1, STITCHED_COLUMNS-1)):
		for spot_subcol in range(spot_col_start, spot_col_end+1):
			spot_row_start = int(row * self.ROW_SCALING_FACTOR)
			spot_row_end = spot_row_start + int(self.ROW_SCALING_FACTOR)
			#logging.debug("Cell row maps to (%d:%d)" % (spot_row_start, spot_row_end))
			# for spot_subrow in range(min(spot_row_start, STITCHED_ROWS-1), min(spot_row_end+1, STITCHED_ROWS-1)):
			for spot_subrow in range(spot_row_start, spot_row_end+1):
				#logging.debug("Getting depth for %d,%d" % (spot_subcol, spot_subrow))
				spot_samples.append(self.getDepthAtVirtualCell(spot_subcol, spot_subrow))
				#logging.debug("spot depth now %d" % spot_depth)
		spot_depth = SAMPLER(spot_samples)
		return (len(spot_samples), spot_depth)

	def updateDepthMaps(self):
		now = time.time()
		self.getSensorDepthMaps()
		self.plotMappedDepths(now)

	def initPlotter(self):
		self.plotter = plotter.Plotter()
		# The ratio of stitched sensor input width to plotter point width, known to be > 1.0
		self.COLUMN_SCALING_FACTOR = float(STITCHED_COLUMNS + 1) / (self.plotter.COLUMNS + 1)
		# The ratio of stitched sensor input height to plotter point height, known to be > 1.0
		self.ROW_SCALING_FACTOR = float(STITCHED_ROWS + 1) / (self.plotter.ROWS + 1)

		typical_distance = self.calculateMergedDepth(self.plotter.COLUMNS / 2, self.plotter.ROWS / 2)[1]
		logging.debug("initial distance %s" % str(typical_distance))
		self.plotter.setAllCellDistances(typical_distance)

logging.getLogger().setLevel(logging.INFO)
logging.info("Starting up with %d x %d renderers" % (plotter.ZONES[0], plotter.ZONES[1]))
logging.debug("STITCHED_COLUMNS, STITCHED_ROWS = %d, %d" % (STITCHED_COLUMNS, STITCHED_ROWS))
stitcher=Stitcher(0,1,2,0,0,testing=False)
stitcher.initPlotter()
while True:
	start = time.time()
	stitcher.updateDepthMaps()
	logging.info("Update took %f secs" % (time.time() - start))
	now = time.time()
	stitcher.plotter.refreshCells()
	logging.info("Refresh took %f secs" % (time.time() - now))
	now = time.time()
	stitcher.plotter.updateIdleCells(now)
	logging.info("Idle took %f secs" % (time.time() - now))
