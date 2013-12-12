#!/usr/bin/env python
# arg = kinect device index, from 0
# arg = threshold above which we consider a sensor spots depth to be changed
import copy
import freenect
import numpy as np
import sys

if len(sys.argv) != 3:
	print >> sys.stderr, "usage %s kinect-device-index threshold" % sys.argv[0]
	sys.exit(255)

CELL_SCALING_FACTOR = 05
threshold = int(sys.argv[2])
old_depth, timestamp = freenect.sync_get_depth(int(sys.argv[1]))
height = len(old_depth)
width = len(old_depth[0])
print 'Kinect device %d, Depth map %d X %d\n' % (int(sys.argv[1]), height, width)
print 'Cell map %d X %d\n' % (width/CELL_SCALING_FACTOR, height/CELL_SCALING_FACTOR)
min_depth = 9999
max_depth = -1
while 1:
    cell_map = [[0]*(width/CELL_SCALING_FACTOR)]*(height/CELL_SCALING_FACTOR)
    depth, timestamp = freenect.sync_get_depth(int(sys.argv[1]))
    for row in depth:
	row_min = min(row)
	row_max = max(row)
	min_depth = min(row_min, min_depth)
	max_depth = max(row_max, max_depth)
    print "min:max depth %d : %d\n" % (min_depth, max_depth)
    delta = []
    shifts = 0
    for row in range(0, len(depth)):
      print 'old:',
      for v in old_depth[row]:
          print '%d,' % v,
      print ''
      print 'new:',
      for v in depth[row]:
          print '%d,' % v,
      print ''
      delta.append([])
      for col in range(0, len(depth[row])):
        delta[row].append(int(old_depth[row][col]) - int(depth[row][col]))
        if abs(delta[row][col]) >= threshold:
	  cell_map[int(row/CELL_SCALING_FACTOR)][int(col/CELL_SCALING_FACTOR)] += 1
          shifts += 1
    print "\nMap of %d X %d pixel aggregate shifts\n\n" % (len(depth[0]), len(depth))
    for cell_row in range(0, len(cell_map)):
      for cell_col in range(0, len(cell_map[0])):
        if cell_map[cell_row][cell_col] == 0:
          sys.stdout.write('.')
        elif cell_map[cell_row][cell_col] > 9:
          sys.stdout.write('+')
        else:
          sys.stdout.write(str(cell_map[cell_row][cell_col]).strip())
      print '\n'
    print "%d shifts >= %d" % (shifts, threshold)
    old_depth = copy.deepcopy(depth)
