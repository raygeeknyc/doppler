import time

COLS=1900
ROWS=150

l = []
for x in range(COLS):
        r = []
        for y in range(ROWS):
                r.append(x+y)
        l.append(r)

d = {}
for x in range(COLS):
        r = {}
        for y in range(ROWS):
                r[y] = (x+y)
        d[x] = r

print "list[%d][%d]" % (len(l), len(l[0]))
for iter in range(5):  
        start = time.time()
        for x in range(COLS):
                for y in range(ROWS):
                        a = l[x][y]
        print "list took %f" % (time.time() - start)

        start = time.time()
        for x in range(COLS):
                for y in range(ROWS):
                        a = d[x][y]
        print "dict took %f" % (time.time() - start)
