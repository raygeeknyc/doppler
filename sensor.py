#!/usr/bin/env python
"Install install freenect libusb libusb=dev libusb-dev libfreenect-demos python-freenect python-numpy python-support python-opencv python-matplotib python-matplotlib"

"Test with import sensor;reload(sensor)"

import copy
import errno
from itertools import chain
import freenect
import logging
import numpy
import random
import plotter
import sys
import time

# When falling back to a SAMPLER, sample an entire mapped pixel or just the center column
SAMPLE_FULL_AREA = True
#SAMPLER = numpy.mean
SAMPLER = numpy.median

# The number of pixels to cut out of the right side of the left sensor's map
LEFT_SENSOR_MARGIN = 15
# The number of pixels to cut out of the right side of the center sensor's map
CENTER_SENSOR_MARGIN = 41
# The number of pixels to cut out of the right side of the right sensor's map
RIGHT_SENSOR_MARGIN = 7
# The known width of a sensor's depth map
SENSOR_COLUMNS = 640
# The known height of a sensor's depth map
SENSOR_ROWS = 480

# Precompute these for speed, we use them often
LEFT_SENSOR_EDGE = SENSOR_COLUMNS - LEFT_SENSOR_MARGIN
CENTER_SENSOR_EDGE = (LEFT_SENSOR_EDGE + SENSOR_COLUMNS) - CENTER_SENSOR_MARGIN
RIGHT_SENSOR_EDGE = (CENTER_SENSOR_EDGE + SENSOR_COLUMNS) - RIGHT_SENSOR_MARGIN

# The total number of columns in the stitched sensor maps
STITCHED_COLUMNS = RIGHT_SENSOR_EDGE
# The total number of rows in the stitched sensor maps
STITCHED_ROWS = SENSOR_ROWS

# When simulating Kinect sensor depths, these are the lower and upper bounds for random values
TEST_CLOSEST_DISTANCE = 100
TEST_FARTHEST_DISTANCE = 2040


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

		self._depth_maps = [[], [], []]

		self._depth_timestamps = [None, None, None]
		self._max_depths = 0

		# Get initial depth maps
		self.getSensorDepthMaps()
		self.MAXIMUM_SENSOR_DEPTH_READING = max(self._depth_maps[self._kinect_left][0])

		logging.info('Sensor Depth[%d],[%d]' % (len(self._depth_maps[self._kinect_center]) ,len(self._depth_maps[self._kinect_center][0])))
		logging.info('Maximum sensor depth reading: %d' % self.MAXIMUM_SENSOR_DEPTH_READING)

	def getDepthAtVirtualCell(self, spot_subcol, spot_subrow):
		"Return the value at the mapped cell from the 3 individual sensor depth maps."
		if spot_subcol < LEFT_SENSOR_EDGE:
			depth_map = self._depth_maps[self._kinect_left]
			depth_col = spot_subcol
		elif spot_subcol < CENTER_SENSOR_EDGE:
			depth_map = self._depth_maps[self._kinect_center]
			depth_col = spot_subcol - LEFT_SENSOR_EDGE
		else:
			depth_map = self._depth_maps[self._kinect_right]
			depth_col = spot_subcol - CENTER_SENSOR_EDGE
		#logging.debug("actual cell coord is %d,%d" % (spot_subrow, depth_col))
		#logging.debug("whose value is %d" % depth_map[depth_col][spot_subrow])
		#logging.debug("map is %d,%d" % (len(depth_map), len(depth_map[0])))
		return depth_map[spot_subrow][depth_col]

	def getSensorDepthMap(self, sensor_idx):
		self._depth_maps[sensor_idx], self._depth_timestamps[sensor_idx] = freenect.sync_get_depth(sensor_idx)

	def getSensorDepthMaps(self):
		start = time.time()
		if not self._testing:
			logging.debug("Getting depth maps from 3 sensors")
			self.getSensorDepthMap(self._kinect_left)
			self.getSensorDepthMap(self._kinect_center)
			self.getSensorDepthMap(self._kinect_right)
			logging.debug("done")
		else:
			logging.debug("Getting 3 dummy depth maps")
			self._depth_maps[self._kinect_left], self._depth_timestamps[self._kinect_left] = getDummyDepthMap()
			self._depth_maps[self._kinect_center], self._depth_timestamps[self._kinect_center] = getDummyDepthMap()
			self._depth_maps[self._kinect_right], self._depth_timestamps[self._kinect_right] = getDummyDepthMap()
		logging.info("Got 3 maps in %f secs" % (time.time() - start))

	def plotMappedDepths(self):
		"""
		Send updates to the plotters depth map, from the stitched sensor maps,
		using the min of sensor cells that correspond to each plotter cell.
		Horizontally flip the plotter map since the libfreenect library is flipping the depth stream, as mentioned in release notes.
		It should be OK to flip at this coarse level as we are averaging the sensor points around a given cell so the orientation
		within a cell's sensor cells should not matter.
		"""
		logging.debug("calculating depths for %d,%d cells" % (self.plotter.COLUMNS, self.plotter.ROWS))
		updated = 0
		self._max_depths = 0
		COL_LIMIT = self.plotter.COLUMNS - 1
		for spot_col in range(0, self.plotter.COLUMNS):
			flipped_col = COL_LIMIT - spot_col
			for spot_row in range(0, self.plotter.ROWS):
				spot_area, spot_depth = self.calculateMergedDepth(flipped_col, spot_row)
				if spot_depth != self.MAXIMUM_SENSOR_DEPTH_READING:
					updated += self.plotter.updateCellState(spot_col, spot_row, spot_depth)
		if self._max_depths:
			logging.warning("Unable to find non max readings for %d cells" % self._max_depths)
		logging.info("Updated %d cells" % updated)
				
	def calculateMergedDepth(self, col, row):
		"Calculate the depth at a plotter map's cell using the center spot or the specified SAMPLER if the spot is at the maximum reading."
		global SAMPLER

		spot_col_start = int(col * self.COLUMN_SCALING_FACTOR)
		spot_row_start = int(row * self.ROW_SCALING_FACTOR)

		# First try to just return the top left spot within the cell.
		spot_depth = self.getDepthAtVirtualCell(spot_col_start, spot_row_start)
		if spot_depth != self.MAXIMUM_SENSOR_DEPTH_READING:
			return (1, int(spot_depth))
		else:  # Use a sampler
			samples_for_cell = []
			spot_row_end = spot_row_start + int(self.ROW_SCALING_FACTOR) + 1
			if not SAMPLE_FULL_AREA:  # Sample the center column
				spot_col_center = spot_col_start + int((self.COLUMN_SCALING_FACTOR+1) / 2)
				for spot_row in range(spot_row_start, spot_row_end):
					sample = self.getDepthAtVirtualCell(spot_col_center, spot_row)
					if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
						samples_for_cell.append(sample)
			else:  # Sample the entire mapped cell
				spot_col_end = spot_col_start + int(self.COLUMN_SCALING_FACTOR) + 1
				for spot_subcol in range(spot_col_start, spot_col_end):
					for spot_subrow in range(spot_row_start, spot_row_end):
						sample = self.getDepthAtVirtualCell(spot_subcol, spot_subrow)
						if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
							samples_for_cell.append(sample)
			# If we had no "good" samples, we may have a legit "MAX" sensor reading.
			if len(samples_for_cell) == 0:
				samples_for_cell.append(self.MAXIMUM_SENSOR_DEPTH_READING)
				self._max_depths += 1
			spot_depth = int(SAMPLER(samples_for_cell))
			return (len(samples_for_cell), spot_depth)

	def updateDepthMaps(self):
		self.getSensorDepthMaps()
		self.plotMappedDepths()

	def initPlotter(self):
		self.plotter = plotter.Plotter()
		# The ratio of stitched sensor input width to plotter point width, known to be > 1.0
		self.COLUMN_SCALING_FACTOR = float(STITCHED_COLUMNS + 1) / (self.plotter.COLUMNS + 1)
		# The ratio of stitched sensor input height to plotter point height, known to be > 1.0
		self.ROW_SCALING_FACTOR = float(STITCHED_ROWS + 1) / (self.plotter.ROWS + 1)

		typical_distance = self.calculateMergedDepth(self.plotter.COLUMNS / 2, self.plotter.ROWS / 2)[1]
		logging.debug("initial distance %s" % str(typical_distance))
		logging.info("x,y sensor:display scaling factor %f,%f" % (self.COLUMN_SCALING_FACTOR, self.ROW_SCALING_FACTOR))
		self.plotter.setAllCellDistances(typical_distance)

logging.getLogger().setLevel(logging.INFO)
logging.info("Starting up with %d x %d renderers" % (plotter.ZONES[0], plotter.ZONES[1]))
logging.info("STITCHED_COLUMNS, STITCHED_ROWS = %d, %d" % (STITCHED_COLUMNS, STITCHED_ROWS))
stitcher=Stitcher(0,1,2,0,0,testing=False)
stitcher.initPlotter()
while True:
	start = time.time()
	stitcher.updateDepthMaps()
	logging.info("Update took %f secs" % (time.time() - start))
	now = time.time()
	stitcher.plotter.refreshCells()
	logging.info("Refresh took %f secs" % (time.time() - now))
