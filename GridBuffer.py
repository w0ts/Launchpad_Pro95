"""Double-buffered pad colours for the step sequencer editors: only changed pads are sent."""

GRID_SIZE = 8


def _empty_grid():
    return [[0] * GRID_SIZE for _ in range(GRID_SIZE)]


class GridBufferMixin:
    """Draw into self._grid_back_buffer[x][y], then _flush_grid() sends what changed to
    self._matrix (everything when self._force_update is set, which it then clears)."""

    def _reset_grid_buffers(self):
        self._grid_buffer = _empty_grid()
        self._grid_back_buffer = _empty_grid()

    def _fill_grid(self, width, height, value):
        for x in range(width):
            for y in range(height):
                self._grid_back_buffer[x][y] = value

    def _flush_grid(self, width, height):
        for x in range(width):
            for y in range(height):
                if self._grid_back_buffer[x][y] != self._grid_buffer[x][y] or self._force_update:
                    self._grid_buffer[x][y] = self._grid_back_buffer[x][y]
                    self._matrix.get_button(x, y).set_light(self._grid_buffer[x][y])
        self._force_update = False
