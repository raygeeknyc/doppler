import Tkinter, random
class PixelBlock:
    CELL_WIDTH = 20
    CELL_HEIGHT = 20
    CELL_PAD = 3

    def __init__(self, top, left):
      self._top = top
      self._left = left

    def setColor(self, rgb):
      self._color = tuple(rgb)

    def getColor(self):
      return self._color

    def draw(self):
      pass

    def getLeftTop(self):
      """Return x,y screen coord tuple."""
      return (self._left * self.CELL_WIDTH + self.CELL_PAD, self._top * self.CELL_HEIGHT + self.CELL_PAD)

    def getRightBottom(self):
      """Return x,y screen coord tuple."""
      return ((self._left + 1) * self.CELL_WIDTH - self.CELL_PAD, (self._top + 1) * self.CELL_HEIGHT - self.CELL_PAD)


class App:
    def __init__(self, master):
        pad = 0
        self._master = master
        self._screen_width = self._master.winfo_screenwidth()
        self._screen_height = self._master.winfo_screenheight()
        print "%d X %d pixels\n" % (self._screen_width, self._screen_height)
        self._master.geometry("{0}x{1}+0+0".format(self._screen_width-pad, self._screen_height-pad))
        self._master.overrideredirect(1)
        self._cols = self._screen_width / PixelBlock.CELL_WIDTH
        self._rows = self._screen_height / PixelBlock.CELL_HEIGHT                                          
        print "%d X %d cells\n" % (self._cols, self._rows)
        self._canvas = Tkinter.Canvas(self._master, width=self._screen_width,
                           height=self._screen_height, cursor="none", background='black')
        self.initializeCells()

    def initializeCells(self):
        self._cells = {}
        for row in range(0, self._rows):
          row_cells = {}
          for col in range(0, self._cols):
            row_cells[col] = PixelBlock(row, col)     
            row_cells[col].setColor([random.randint(0,255) for i in range(0,3)])                            
          self._cells[row] = row_cells
  
    def redraw(self):                          
        for row in range(0, self._rows):
          if (row%10 == 0):                
            print row                                          
          for col in range(0, self._cols):                       
            self._canvas.create_oval(self._cells[row][col].getLeftTop()[0],
                                          self._cells[row][col].getLeftTop()[1],
                                          self._cells[row][col].getRightBottom()[0],
                                          self._cells[row][col].getRightBottom()[1],
                                          fill='#%02x%02x%02x' % self._cells[row][col].getColor()
                                          )
        self._canvas.pack()                                                  
                          
window_base = Tkinter.Tk()
a = App(window_base)  
a.redraw()            
window_base.mainloop()
