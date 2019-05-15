from typing import Tuple, Dict, Any

import numpy
from matplotlib.figure import Figure
from numpy import ndarray

from autotrack.core import TimePoint
from autotrack.core.experiment import Experiment
from autotrack.core.position_collection import PositionCollection
from autotrack.core.resolution import ImageResolution
from autotrack.gui import dialog
from autotrack.gui.window import Window
from autotrack.linking_analysis import cell_density_calculator


def get_menu_items(window: Window) -> Dict[str, Any]:
    return {
         "Graph//Cell density-Average cell density over time...": lambda: _show_cell_density(window),
    }


def _show_cell_density(window: Window):
    experiment = window.get_experiment()

    times_h, densities_um1, densities_stdev_um1 = _get_all_average_densities(experiment)
    dialog.popup_figure(window.get_gui_experiment(), lambda figure: _draw_cell_density(figure, times_h, densities_um1,
                                                                                       densities_stdev_um1))


def _draw_cell_density(figure: Figure, times_h: ndarray, densities_um1: ndarray, densities_stdev_um1: ndarray):
    axes = figure.gca()
    axes.plot(times_h, densities_um1)
    axes.fill_between(times_h, densities_um1 - densities_stdev_um1, densities_um1 + densities_stdev_um1,
                      color="lightblue")
    axes.set_xlabel("Time (h)")
    axes.set_ylabel("Density (μm$^{-1}$)")
    axes.set_title("Average cell density over time")
    axes.set_ylim(0, max(densities_um1) * 1.2)


def _get_all_average_densities(experiment: Experiment) -> Tuple[ndarray, ndarray, ndarray]:
    """Returns three lists: time (hours) vs average density (um^-1) and its standard deviation."""
    resolution = experiment.images.resolution()
    positions = experiment.positions

    times_h = []
    densities_um1 = []
    densities_stdev_um1 = []
    for time_point in experiment.time_points():
        density_avg_um, density_stdev_um = _get_average_density_um(positions, time_point, resolution)
        if density_avg_um > 0:
            times_h.append(time_point.time_point_number() * resolution.time_point_interval_h)
            densities_um1.append(density_avg_um)
            densities_stdev_um1.append(density_stdev_um)

    return numpy.array(times_h), numpy.array(densities_um1), numpy.array(densities_stdev_um1)


def _get_average_density_um(positions: PositionCollection, time_point: TimePoint, resolution: ImageResolution
                            ) -> Tuple[float, float]:
    """Gets the average density and the std dev for the whole organoid at the given time point."""
    densities = list()
    for position in positions.of_time_point(time_point):
        density = cell_density_calculator.get_density(positions.of_time_point(time_point), position, resolution)

        densities.append(density)

    if len(densities) == 0:
        return 0, 0
    return float(numpy.mean(densities)), float(numpy.std(densities, ddof=1))