#!/usr/bin/env python
"Install install freenect libusb libusb=dev libusb-dev libfreenect-demos python-freenect python-numpy python-support python-opencv python-matplotib python-matplotlib"

"Test with import sensor;reload(sensor)"

import collections
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

import sensor

# The maximum update frequency
TARGET_FPS = 4
# this throttles the update/refresh cycle to protect the renderers from being overwhelmed
_MAX_REFRESH_FREQUENCY = 1.0/TARGET_FPS

# When falling back to a SAMPLER, sample an entire mapped pixel or just the center column
SAMPLE_FULL_AREA = False
SAMPLER = None
#SAMPLER = numpy.median
#SAMPLER = numpy.mean

# The known width of a sensor's depth map
SENSOR_COLUMNS = 640
# The known height of a sensor's depth map
SENSOR_ROWS = 480

# Precompute these for speed, we use them often

# When simulating Kinect sensor depths, these are the lower and upper bounds for random values
TEST_CLOSEST_DISTANCE = 100
TEST_FARTHEST_DISTANCE = 2040

class Stitcher(sensor.BaseStitcher):
	def _initializeDepthMaps(self):
                super(Stitcher, self)._initializeDepthMaps()

		self._depth_maps = [[]]

		self._depth_timestamps = [[None]]

		# Get initial depth maps
		self.getSensorDepthMaps()

	def __init__(self, testing = True):
                super(Stitcher, self).__init__(testing)

	def getDepthAtVirtualCell(self, spot_subcol, spot_subrow):
		"Return the value at the mapped cell from the 3 individual sensor depth maps."
		if spot_subcol < LEFT_SENSOR_EDGE:
			return self._depth_maps[self._kinect_left][spot_subrow][spot_subcol]
		elif spot_subcol < CENTER_SENSOR_EDGE:
			return self._depth_maps[self._kinect_center][spot_subrow][spot_subcol - LEFT_SENSOR_EDGE]
		else:
			return self._depth_maps[self._kinect_right][spot_subrow][spot_subcol - CENTER_SENSOR_EDGE]

	def getSensorDepthMaps(self):
		start = time.time()
		if not self._testing:
			logging.debug("Getting depth map from 1 sensor")
			self.getSensorDepthMap(0)
		else:
			logging.debug("Getting 1 dummy depth map")
			self._depth_maps[0], self._depth_timestamps[0] = sensor.getDummyDepthMap()
		logging.debug("Got 1 maps in %f secs" % (time.time() - start))

	def plotMappedDepths(self):
		"""
		Send updates to the plotters depth map, from the stitched sensor maps,
		using the min of sensor cells that correspond to each plotter cell.
		Horizontally flip the plotter map since the libfreenect library is flipping the depth stream, as mentioned in release notes.
		It should be OK to flip at this coarse level as we are averaging the sensor points around a given cell so the orientation
		within a cell's sensor cells should not matter.
		"""
		for spot_col in xrange(self.plotter.COLUMNS):
			flipped_col = self.COL_LIMIT - spot_col
			for spot_row in xrange(self.plotter.ROWS):
				spot_area, spot_depth = self.calculateMergedDepth(flipped_col, spot_row)
				if spot_depth != self.MAXIMUM_SENSOR_DEPTH_READING:
					self.plotter.updateCellState(spot_col, spot_row, spot_depth)
				
	def calculateMergedDepth(self, col, row):
		"Calculate the depth at a plotter map's cell using the center spot or the specified SAMPLER if the spot is at the maximum reading."
		global SAMPLER

		spot_col_start = int(col * self.COLUMN_SCALING_FACTOR)
		spot_row_start = int(row * self.ROW_SCALING_FACTOR)

		# First try to just return the top left spot within the cell.
		spot_depth = self.getDepthAtVirtualCell(spot_col_start, spot_row_start)
		if spot_depth != self.MAXIMUM_SENSOR_DEPTH_READING:
			return (1, int(spot_depth))
		elif SAMPLER == None:  # Take the first non MAX reading in this cell
			spot_row_end = spot_row_start + int(self.ROW_SCALING_FACTOR) + 1
			if not SAMPLE_FULL_AREA:  # Look for a reading in the center column
				spot_col_center = spot_col_start + int((self.COLUMN_SCALING_FACTOR+1) / 2)
				for spot_row in range(spot_row_start, spot_row_end):
					sample = self.getDepthAtVirtualCell(spot_col_center, spot_row)
					if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
						return (1, int(sample))
			else:  # Look for a reading in the entire mapped cell
				spot_col_end = spot_col_start + int(self.COLUMN_SCALING_FACTOR) + 1
				for spot_subcol in range(spot_col_start, spot_col_end):
					for spot_subrow in range(spot_row_start, spot_row_end):
						sample = self.getDepthAtVirtualCell(spot_subcol, spot_subrow)
						if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
							return (1, int(sample))
		else:  # Use a sampler to average the readings in this cell
			self._samples_for_cell.clear()
			spot_row_end = spot_row_start + int(self.ROW_SCALING_FACTOR) + 1
			if not SAMPLE_FULL_AREA:  # Sample the center column
				spot_col_center = spot_col_start + int((self.COLUMN_SCALING_FACTOR+1) / 2)
				for spot_row in range(spot_row_start, spot_row_end):
					sample = self.getDepthAtVirtualCell(spot_col_center, spot_row)
					if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
						self._samples_for_cell.append(sample)
			else:  # Sample the entire mapped cell
				spot_col_end = spot_col_start + int(self.COLUMN_SCALING_FACTOR) + 1
				for spot_subcol in range(spot_col_start, spot_col_end):
					for spot_subrow in range(spot_row_start, spot_row_end):
						sample = self.getDepthAtVirtualCell(spot_subcol, spot_subrow)
						if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
							self._samples_for_cell.append(sample)
		# If we had no "good" samples, we may have a legit "MAX" sensor reading.
		if not len(self._samples_for_cell):
			return (1, self.MAXIMUM_SENSOR_DEPTH_READING)
		spot_depth = int(SAMPLER(self._samples_for_cell))
		return (len(self._samples_for_cell), spot_depth)

	def updateDepthMaps(self):
		self.getSensorDepthMaps()
		self.plotMappedDepths()

	def initPlotter(self):
		self.plotter = plotter.Plotter()
		# The ratio of stitched sensor input width to plotter point width, known to be > 1.0
		self.COLUMN_SCALING_FACTOR = float(SENSOR_COLUMNS + 1) / (self.plotter.COLUMNS + 1)
		# The ratio of stitched sensor input height to plotter point height, known to be > 1.0
		self.ROW_SCALING_FACTOR = float(SENSOR_ROWS + 1) / (self.plotter.ROWS + 1)
		typical_distance = self.calculateMergedDepth(self.plotter.COLUMNS / 2, self.plotter.ROWS / 2)[1]
		logging.debug("initial distance %s" % str(typical_distance))
		logging.info("x,y sensor:display scaling factor %f,%f" % (self.COLUMN_SCALING_FACTOR, self.ROW_SCALING_FACTOR))
		self.plotter.setAllCellDistances(typical_distance)
		self.COL_LIMIT = self.plotter.COLUMNS - 1

def main(argv):
	print("singlesensor:main()")
	logging.getLogger().setLevel(logging.INFO)
	logging.info("Starting up with %d x %d renderers" % (plotter.ZONES[0], plotter.ZONES[1]))
	logging.info("SENSOR_COLUMNS, SENSOR_ROWS = %d, %d" % (SENSOR_COLUMNS, SENSOR_ROWS))
	logging.info("Target rate is %f, which is a frequency of %f" % (TARGET_FPS, _MAX_REFRESH_FREQUENCY))
	testing = len(argv) > 1 and argv[1] == "debug"
	testing = False
	stitcher=Stitcher(testing=testing)
	stitcher.initPlotter()
	while True:
		start = time.time()
		stitcher.updateDepthMaps()
		logging.debug("Update took %f secs" % (time.time() - start))
		now = time.time()
		stitcher.plotter.refreshCells()
		logging.debug("Refresh took %f secs" % (time.time() - now))
		frequency = time.time() - start
		if frequency < _MAX_REFRESH_FREQUENCY:                                  
			time.sleep((_MAX_REFRESH_FREQUENCY - frequency))                
		frequency = time.time() - start
		logging.info("effective frequency is %f which is %f FpS" % (frequency, (1/frequency)))

if __name__ == "__main__":
	main(sys.argv)
main(sys.argv)
