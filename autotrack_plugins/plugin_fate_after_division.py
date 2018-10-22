from typing import Dict, Any, Optional, List

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from networkx import Graph

from autotrack.core import UserError
from autotrack.core.experiment import Experiment
from autotrack.core.particles import Particle
from autotrack.gui import Window, dialog
from autotrack.linking import cell_cycle, mother_finder

# Were no divisions found because a cell really didn't divide, or did the experiment simply end before the cell divided?
# If the experiment continues for at least this many time points, then we can safely assume that the cell did not
# divide.
_DIVISION_LOOKAHEAD = 100


def get_menu_items(window: Window) -> Dict[str, Any]:
    return {
        "Graph/Cell cycle-Chance of division...": lambda: _show_chance_of_division(window.get_experiment())
    }


def _show_chance_of_division(experiment: Experiment):
    links = experiment.links.get_baseline_else_scratch()
    if links is None:
        raise UserError("No linking data found", "For this graph on cell divisions, it is required to have the cell"
                                                 " links loaded.")

    max_time_point_number = experiment.last_time_point_number()

    dialog.popup_figure(experiment.name, lambda figure: _draw_histogram(figure, links, max_time_point_number))


def _draw_histogram(figure: Figure, links: Graph, max_time_point_number: int):
    time_points_per_bin = 10
    bins = _classify_cell_divisions(links, time_points_per_bin, max_time_point_number)
    if len(bins) == 0:
        raise UserError("No cell cycles found",
                        "The linking data contains no full cell cycles, so we cannot plot anything.")

    dividing_cell_fractions = [bin.dividing_fraction() for bin in bins]
    nondividing_cell_fractions = [bin.nondividing_fraction() for bin in bins]
    unknown_fate_cell_fractions = [bin.unknown_fraction() for bin in bins]
    dividing_plus_unknown_cell_fractions = [bin.dividing_fraction() + bin.unknown_fraction() for bin in bins]
    time_point_numbers = [bin.min_time_point_number for bin in bins]

    axes = figure.gca()
    axes.bar(time_point_numbers, dividing_cell_fractions,
             align="edge", width=time_points_per_bin, label="Dividing", color="orange")
    axes.bar(time_point_numbers, unknown_fate_cell_fractions, bottom=dividing_cell_fractions,
             align="edge", width=time_points_per_bin, label="Unknown", color="lightgray")
    axes.bar(time_point_numbers, nondividing_cell_fractions, bottom=dividing_plus_unknown_cell_fractions,
             align="edge", width=time_points_per_bin, label="Nondividing", color="blue")
    for some_bin in bins:
        axes.text(some_bin.min_time_point_number + time_points_per_bin/2, 0.05,
                  f"{some_bin.total_number_of_cells()} cells", horizontalalignment='center', fontsize=8)
    axes.set_xlabel("Duration of previous cell cycle (time points)")
    axes.set_ylabel("Cell fate (fractions)")
    axes.set_title("Fate of cells after a division")
    axes.legend()

    x_start = time_point_numbers[0]
    x_end = time_point_numbers[-1] + time_points_per_bin + 1
    axes.set_xticks(range(x_start, x_end, time_points_per_bin))


def _will_divide(graph: Graph, particle: Particle, max_time_point_number: int) -> Optional[bool]:
    """Checks if a cell will undergo a division later in the experiment. Returns None if not sure, because we are near
    the end of the experiment. max_time_point_number is the number of the last time point in the experiment."""
    next_division = cell_cycle.get_next_division(graph, particle)
    if next_division is None:
        # Did the experiment end, or did the cell really stop dividing?
        if particle.time_point_number() + _DIVISION_LOOKAHEAD > max_time_point_number:
            return None  # We are not sure
        return False  # Cell with not divide
    return True  # Cell will divide in the future


class _Bin:
    """A single bin in the histogram."""
    _dividing_count: int = 0
    _nondividing_count: int = 0
    _unknown_count: int = 0

    min_time_point_number: int

    def __init__(self, min_time_point_number: int):
        self.min_time_point_number = min_time_point_number

    def dividing_fraction(self):
        return self._dividing_count / self.total_number_of_cells()

    def nondividing_fraction(self):
        return self._nondividing_count / self.total_number_of_cells()

    def unknown_fraction(self):
        return self._unknown_count / self.total_number_of_cells()

    def total_number_of_cells(self):
        return self._dividing_count + self._nondividing_count + self._unknown_count

    def add_data_point(self, will_divide: Optional[bool]):
        if will_divide is None:
            self._unknown_count += 1
        elif will_divide:
            self._dividing_count += 1
        else:
            self._nondividing_count += 1

    def is_empty(self):
        return self.total_number_of_cells() == 0


def _classify_cell_divisions(links: Graph, time_points_per_bin: int, max_time_point_number: int) -> List[_Bin]:
    """Classifies each cell division in the data: is it the last cell division in a lineage, or will there be more after
    this? The cell divisions are returned in bins. No empty bins are returned."""
    bins = list()

    for cell_division in mother_finder.find_families(links):
        previous_cell_cycle_length = cell_cycle.get_age(links, cell_division.mother)
        if previous_cell_cycle_length is None:
            continue  # Cannot plot without knowing the length of the previous cell cycle

        bin_index = previous_cell_cycle_length // time_points_per_bin  # Integer division
        while bin_index >= len(bins):
            bins.append(_Bin(len(bins) * time_points_per_bin))  # Resize bin array so that it will fit
        bin = bins[bin_index]

        for daughter in cell_division.daughters:
            will_divide = _will_divide(links, daughter, max_time_point_number)
            bin.add_data_point(will_divide)
    return [bin for bin in bins if not bin.is_empty()]