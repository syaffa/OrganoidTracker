from typing import Dict

import matplotlib.pyplot as plt
from matplotlib.backend_bases import KeyEvent
from matplotlib.figure import Figure

from gui import Window, launch_window
from visualizer import activate
from visualizer.image_visualizer import AbstractImageVisualizer
from core import Experiment
from particle_detection import Detector


def show(experiment: Experiment, detector: Detector, detection_parameters: Dict):
    """Creates a visualizer suited particle positions for an experiment.
    Press S to view all detected positions at the current z"""
    window = launch_window(experiment)
    visualizer = DetectionVisualizer(window, detector, detection_parameters)
    activate(visualizer)


class DetectionVisualizer(AbstractImageVisualizer):
    """Visualizer specialized in displaying particle positions.
    Use the left/right arrow keys to move in time.
    Use the up/down arrow keys to move in the z-direction
    Press D to perform 2D detection in this time point, showing intermediate results.
    Press N to show the next and current time point together in a single image (red=next time point, green=current)
    """
    _detection_parameters = Dict
    _detector: Detector

    def __init__(self, window: Window, detector: Detector, detection_parameters: Dict):
        super().__init__(window)
        self._detection_parameters = detection_parameters
        self._detector = detector

    def _on_key_press(self, event: KeyEvent):
        if event.key == "d":
            image = self._experiment.get_image_stack(self._time_point)[self._z]
            self._detector.detect(image, show_results=True, **self._detection_parameters)

        super()._on_key_press(event)