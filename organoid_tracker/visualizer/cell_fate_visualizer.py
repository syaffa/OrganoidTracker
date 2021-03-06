from typing import Dict, Optional

from organoid_tracker.core import TimePoint
from organoid_tracker.core.position import Position
from organoid_tracker.linking_analysis import cell_fate_finder
from organoid_tracker.linking_analysis.cell_fate_finder import CellFateType, CellFate
from organoid_tracker.visualizer.exitable_image_visualizer import ExitableImageVisualizer


def _cell_fate_to_text(cell_fate: CellFate):
    if cell_fate.type == CellFateType.JUST_MOVING:
        return "~"
    if cell_fate.type == CellFateType.WILL_DIE:
        return "X in " + str(cell_fate.time_points_remaining)
    if cell_fate.type == CellFateType.WILL_SHED:
        return "S in " + str(cell_fate.time_points_remaining)
    if cell_fate.type == CellFateType.WILL_DIVIDE:
        return "Div in " + str(cell_fate.time_points_remaining)
    return "?"


def _cell_fate_to_color(cell_fate: CellFate):
    if cell_fate.type == CellFateType.WILL_DIVIDE:
        return "green"
    if cell_fate.type == CellFateType.WILL_SHED:
        return "blue"
    if cell_fate.type == CellFateType.WILL_DIE:
        return "red"
    return "black"


class CellFateVisualizer(ExitableImageVisualizer):
    """Shows how each cell will develop during the experiment. Note: time points past the current time point are not
    included. Legend:
    ?         unknown cell fate - cell moved out of view, the experiment will end soon or there are unresolved warnings
    X in 13   cell will die in 13 time points
    < in 16   cell will divide in 16 time points
    ~         no events, just movement."""

    _cell_fates: Dict[Position, CellFate] = dict()

    def _calculate_time_point_metadata(self):
        super()._calculate_time_point_metadata()

        # Check what lineages contain errors
        links = self._experiment.links
        if not links.has_links():
            self._cell_fates = dict()
            return

        positions = self._experiment.positions.of_time_point(self._time_point)
        result = dict()
        for position in positions:
            result[position] = cell_fate_finder.get_fate(self._experiment, position)
        self._cell_fates = result

    def _on_position_draw(self, position: Position, color: str, dz: int, dt: int):
        if dt == 0 and abs(dz) <= 3:
            cell_fate = self._cell_fates.get(position)
            if cell_fate is None:
                cell_fate = CellFate(CellFateType.UNKNOWN, None)
            color = _cell_fate_to_color(cell_fate)
            self._ax.annotate(_cell_fate_to_text(cell_fate), (position.x, position.y), fontsize=8 - abs(dz / 2),
                              fontweight="bold", color=color, backgroundcolor=(1,1,1,0.8))
        return True
