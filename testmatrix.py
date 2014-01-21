import time

ROWS = 100
COLS = 55

l = []
for y in range(ROWS):
	for x in range(COLS):
		l.append(x+y)
print "%d elements" % (len(l))

m = []
for y in range(ROWS):
	r = []
	for x in range(COLS):
		r.append(x+y)
	m.append(r)

print "%d rows x %d cols" % (len(m),len(m[0]))

start = time.time()
for o in range(len(l)):
	s = l[(y*COLS)+x]
print 'Time to traverse list: %f' % (time.time() - start)

start = time.time()
for y in range(ROWS):
	for x in range(COLS):
		s = m[y][x]
print 'Time to traverse 2D matrix: %f' % (time.time() - start)
