"Install tcl tk python-tkinter python-modules."

import signal
import time
import Tkinter, random
import sys

_BRIGHTRED = (255,50,50)
_BRIGHTGREEN = (50,255,50)
_BRIGHTBLUE = (50,50,255)

_NEUTRAL_COLOR = '#%02x%02x%02x' % (50,50,50)

CELL_COLORS = ['#%02x%02x%02x' % _BRIGHTRED, '#%02x%02x%02x' % _BRIGHTBLUE, '#%02x%02x%02x' % _BRIGHTGREEN]


class App:

    def __init__(self, master):
        pad = 0
        self._master = master
        self._screen_width = self._master.winfo_screenwidth()
        self._screen_height = self._master.winfo_screenheight()
        self._master.geometry("{0}x{1}+0+0".format(self._screen_width-pad, self._screen_height-pad))
        self._master.overrideredirect(1)
        self._cols = self._screen_width / 10
        self._rows = self._screen_height / 10
        self._canvas = Tkinter.Canvas(self._master, width=self._screen_width,
                           height=self._screen_height, cursor="none", background='black')
	self._widgets = []
        self._canvas.pack()                                                  
	self.setupCells()

    def setupCells(self):
	print 'setupCells()'
        for row in range(0, self._rows):
	  self._widgets.append([])
          for col in range(0, self._cols):
	    self._widgets[row].append(self._canvas.create_rectangle(col * 10, row * 10,
              col*10 + 10, row*10+10,
              fill=_NEUTRAL_COLOR
            )
	  )
	print '/setupCells() %d x %d' % (self._cols, self._rows)

    def setAllCellsRandomly(self, master):
	print 'setAllCellsRandomly()'
	start = time.time()
        for row in range(0, self._rows):
          for col in range(0, self._cols):
   	    self._canvas.itemconfig(self._widgets[row][col],
              fill=CELL_COLORS[random.randint(0,len(CELL_COLORS)-1)]
            )
	print '/setAllCellsRandomly() took %f' % (time.time() - start)

window_base = Tkinter.Tk()

def quit_handler(signal, frame):
	window_base.quit()

signal.signal(signal.SIGINT, quit_handler)

a = App(window_base)  
window_base.after(0, a.setAllCellsRandomly(window_base))
try:
	window_base.mainloop()
except Exception as e:
	print("Top level exception")
