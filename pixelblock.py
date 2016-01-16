import update_message

class PixelBlock:
    CELL_WIDTH = 23  # This is a Pixels horizontal pitch
    CELL_HEIGHT = 23  # This is a Pixels vertical pitch
    CELL_MARGIN = 02  # This is the padding within a Pixel
    CELL_PLOT_WIDTH = CELL_WIDTH - CELL_MARGIN * 2
    CELL_PLOT_HEIGHT = CELL_HEIGHT - CELL_MARGIN * 2

    def __init__(self, left, top, when):
      self.col = left
      self.row = top
      self.plot_x = left * PixelBlock.CELL_WIDTH + PixelBlock.CELL_MARGIN
      self.plot_y = top * PixelBlock.CELL_HEIGHT + PixelBlock.CELL_MARGIN
      self.color = _NEUTRAL_COLOR
      self.ttl = when

_BRIGHTRED = (255,50,50)
_BRIGHTBLUE = (50,50,255)
_LIGHTGREY = (45,45,55)
_DIMBLUE = (45,45,120)
_DIMRED = (120,45,45)
_DIMGREY = (20,15,20)

CELL_COLORS = {
    update_message.CellState.CHANGE_APPROACH_SLOW: _DIMBLUE,
    update_message.CellState.CHANGE_APPROACH_FAST: _BRIGHTBLUE,
    update_message.CellState.CHANGE_RECEDE_SLOW: _DIMRED,
    update_message.CellState.CHANGE_RECEDE_FAST: _BRIGHTRED,
    update_message.CellState.CHANGE_REST: _LIGHTGREY,
    update_message.CellState.CHANGE_STILL: _DIMGREY}
_NEUTRAL_COLOR = (0,0,0)
