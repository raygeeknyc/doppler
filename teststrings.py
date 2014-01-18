import time
import gc

time.sleep(2.0)

start = time.time()
for i in range(2):
	for x in range(600):
		s = "%d,%d,%s" % (x,i,"q")
print "formats took %f secs" % (time.time() - start)

gc.collect()

start = time.time()
for i in range(2):
	for x in range(600):
		s = str(x) + "," + str(i) + "q"
print "concats took %f secs" % (time.time() - start)
