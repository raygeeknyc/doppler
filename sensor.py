#!/usr/bin/env python
"Install freenect, python-freenect libusb libusb-dev python-numpy python-support python-opencv python-matplotlib"

"Test with import sensor;reload(sensor)"

import collections
import copy
import errno
import freenect
import logging
import numpy
import cv2
import random
import plotter
import sys
import time

# The maximum update frequency
TARGET_FPS = None
# this throttles the update/refresh cycle to protect the renderers from being overwhelmed
_MAX_REFRESH_FREQUENCY = None

# When falling back to a SAMPLER, sample an entire mapped pixel or just the center column
SAMPLE_FULL_AREA = None
SAMPLER = None
#SAMPLER = numpy.median
#SAMPLER = numpy.mean

# The known width of a sensor's depth map
SENSOR_COLUMNS = 640
# The known height of a sensor's depth map
SENSOR_ROWS = 480

# When simulating Kinect sensor depths, these are the lower and upper bounds for random values
TEST_CLOSEST_DISTANCE = 100
TEST_FARTHEST_DISTANCE = 2040


def _getDummyDepthMap():
	start = time.time()
	dummy_map = numpy.random.random((SENSOR_COLUMNS, SENSOR_ROWS)) * (TEST_FARTHEST_DISTANCE - TEST_CLOSEST_DISTANCE) + TEST_CLOSEST_DISTANCE
	return dummy_map, time.time()
			
class BaseStitcher(object):
	def _initializeDepthMaps(self):
                pass

	def _initializeSensors(self, sensor_count):
		self._kinects = []
		logging.debug("initializing %d sensors" % sensor_count)
		for sensor in range(sensor_count):
			self._kinects.append(cv2.VideoCapture(sensor))
		logging.debug("sensors initialized")

	def __init__(self, testing):
		self._testing = testing
		self._initializeSensors(1)
		self._initializeDepthMaps()
		logging.debug("%d maps" % len(self._depth_maps))
		# self.MAXIMUM_SENSOR_DEPTH_READING = self._depth_maps[0].max()
		self.MAXIMUM_SENSOR_DEPTH_READING = max(self._depth_maps[0][0])
		logging.debug("max %s" % str(self.MAXIMUM_SENSOR_DEPTH_READING))
		logging.info('Sensor Depth[%d][%d]' % (len(self._depth_maps[0]) ,len(self._depth_maps[0][0])))
		logging.info('Maximum sensor depth reading: %d' % self.MAXIMUM_SENSOR_DEPTH_READING)
		self._samples_for_cell = collections.deque()  # This often created collection is stored as an attribute purely for performance

	def _getDepthAtVirtualCell(self, spot_subcol, spot_subrow):
		"Return the value at the mapped cell from the 3 individual sensor depth maps."
                raise NotImplementedError()

	def _getSensorRgbMap(self, sensor_idx):
		ret, frame = self._kinects[sensor_idx].read()  // webcam version
		self._depth_timestamps[sensor_idx] = time.time()
		logging.debug("read returned %s" % str(ret))
		if ret:
			logging.debug("frame is %d x %d pixels" % (len(frame), len(frame[0])))
			self._depth_maps[sensor_idx] = frame
		else:
			self._depth_maps[sensor_idx] = None
`
	def _getSensorDepthMap(self, sensor_idx):
		self._depth_maps[sensor_idx], self.depth_timestamps[sensor_idx] = freenect.sync_get_depth(sensor_idx)

	def _getSensorDepthMaps(self):
                raise NotImplementedError()

	def plotMappedPixels(self):
		"""
		Send updates to the plotters depth map, from the stitched sensor maps,
		using the min of sensor cells that correspond to each plotter cell.
		"""
		for spot_col in xrange(self.plotter.COLUMNS):
			flipped_col = self.COL_LIMIT - spot_col
			for spot_row in xrange(self.plotter.ROWS):
				spot_area, spot_depth = self.calculateMergedDepth(flipped_col, spot_row)
				if spot_depth != self.MAXIMUM_SENSOR_DEPTH_READING:
					self.plotter.updateCellState(spot_col, spot_row, spot_depth)
				
	def _plotMappedDepths(self):
		"""
		Send updates to the plotters depth map, from the stitched sensor maps,
		using the min of sensor cells that correspond to each plotter cell.
		Horizontally flip the map as the sensor returns them flipped, as
		reported in the freenect release notes.
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
		spot_depth = self._getDepthAtVirtualCell(spot_col_start, spot_row_start)
		if spot_depth != self.MAXIMUM_SENSOR_DEPTH_READING:
			return (1, int(spot_depth))
		elif SAMPLER == None:  # Take the first non MAX reading in this cell
			spot_row_end = spot_row_start + int(self.ROW_SCALING_FACTOR) + 1
			if not SAMPLE_FULL_AREA:  # Look for a reading in the center column
				spot_col_center = spot_col_start + int((self.COLUMN_SCALING_FACTOR+1) / 2)
				for spot_row in range(spot_row_start, spot_row_end):
					sample = self._getDepthAtVirtualCell(spot_col_center, spot_row)
					if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
						return (1, int(sample))
			else:  # Look for a reading in the entire mapped cell
				spot_col_end = spot_col_start + int(self.COLUMN_SCALING_FACTOR) + 1
				for spot_subcol in range(spot_col_start, spot_col_end):
					for spot_subrow in range(spot_row_start, spot_row_end):
						sample = self._getDepthAtVirtualCell(spot_subcol, spot_subrow)
						if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
							return (1, int(sample))
		else:  # Use a sampler to average the readings in this cell
			self._samples_for_cell.clear()
			spot_row_end = spot_row_start + int(self.ROW_SCALING_FACTOR) + 1
			if not SAMPLE_FULL_AREA:  # Sample the center column
				spot_col_center = spot_col_start + int((self.COLUMN_SCALING_FACTOR+1) / 2)
				for spot_row in range(spot_row_start, spot_row_end):
					sample = self._getDepthAtVirtualCell(spot_col_center, spot_row)
					if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
						self._samples_for_cell.append(sample)
			else:  # Sample the entire mapped cell
				spot_col_end = spot_col_start + int(self.COLUMN_SCALING_FACTOR) + 1
				for spot_subcol in range(spot_col_start, spot_col_end):
					for spot_subrow in range(spot_row_start, spot_row_end):
						sample = self._getDepthAtVirtualCell(spot_subcol, spot_subrow)
						if sample != self.MAXIMUM_SENSOR_DEPTH_READING:
							self._samples_for_cell.append(sample)
		# If we had no "good" samples, we may have a legit "MAX" sensor reading.
		if not len(self._samples_for_cell):
			return (1, self.MAXIMUM_SENSOR_DEPTH_READING)
		spot_depth = int(SAMPLER(self._samples_for_cell))
		return (len(self._samples_for_cell), spot_depth)

	def updateDepthMaps(self):
		self.getSensorDepthMaps()
		self._plotMappedDepths()

	def initPlotter(self):
		pass
