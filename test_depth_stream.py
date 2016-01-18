import io
import numpy
import random

FRAME_COLS = 640
FRAME_ROWS = 480
FRAME_BUFFER_LENGTH = FRAME_COLS * FRAME_ROWS

DISTANCE_MIN = 0
DISTANCE_MAX = 2000

def getTestFrame():
  frame = []
  for x in range(FRAME_COLS):
    for y in range(FRAME_ROWS):
      frame.append(random.randrange(DISTANCE_MIN, DISTANCE_MAX))
  return frame

  
frame = getTestFrame()

sensor = io.FileIO("/dev/video0", "rb", 0)
incontent = in_file.read(FRAME_BUFFER_LENGTH)

print "frame: %d elements" % len(frame)
print "mean: %d" % numpy.mean(frame)
