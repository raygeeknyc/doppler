class CellState(object):
    CHANGE_RECEDE_SLOW = "r"
    CHANGE_RECEDE_FAST = "R"
    CHANGE_APPROACH_SLOW = "a"
    CHANGE_APPROACH_FAST = "A"
    CHANGE_REST = "s"
    CHANGE_STILL = "S"

    STATES = [
    CHANGE_RECEDE_SLOW,
    CHANGE_RECEDE_FAST,
    CHANGE_APPROACH_SLOW,
    CHANGE_APPROACH_FAST,
    CHANGE_REST,
    CHANGE_STILL]

class CellUpdate(object):
    def __init__(self, cell_state, coords):
      """state, (x,y)."""
      self._x = coords[0]
      self._y = coords[1]
      self._state = cell_state

    @property
    def state(self):
      return self._state

    @property
    def x(self):
      return self._x

    @property
    def y(self):
      return self._y

    @staticmethod
    def seriesToText(cellSeries):
        return "|".join(str(cellUpdate) for cellUpdate in cellSeries)
	  
    @staticmethod
    def fromText(text_update):
      """state,x,y"""
      try:
        (state,x,y) = text_update.split(",")
        return CellUpdate(state, (int(x), int(y)))
      except Exception as e:
	print "Error parsing text: %s" % str(e)
	return None

    def __str__(self):
      return "{},{},{}".format(self._state, self._x, self._y)
