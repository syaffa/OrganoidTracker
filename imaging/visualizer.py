import numpy

import imaging
from imaging import Experiment, Particle, TimePoint
from matplotlib.figure import Figure, Axes, Text
from matplotlib.backend_bases import KeyEvent, MouseEvent
from typing import Iterable, Optional, Union
import matplotlib.pyplot as plt


class Visualizer:
    """A complete application for visualization of an experiment"""
    _experiment: Experiment

    _fig: Figure
    _ax: Axes

    _key_handler_id: int
    _mouse_handler_id: int

    _pending_command_text: Optional[str]
    _status_text_widget: Optional[Text]
    _controls_enabled: bool = True

    def __init__(self, experiment: Experiment, figure: Figure):
        self._experiment = experiment
        self._fig = figure
        self._ax = self._fig.gca()
        self._key_handler_id = self._fig.canvas.mpl_connect("key_press_event", self._on_key_press_raw)
        self._mouse_handler_id = self._fig.canvas.mpl_connect("button_press_event", self._on_mouse_click)

        self._pending_command_text = None
        self._status_text_widget = None

    def _clear_axis(self):
        """Clears the axis, except that zoom settings are preserved"""
        for image in self._ax.images:
            colorbar = image.colorbar
            if colorbar is not None:
                colorbar.remove()
        for text in self._fig.texts:
            text.remove()
        self._status_text_widget = None

        xlim, ylim = self._ax.get_xlim(), self._ax.get_ylim()
        self._ax.clear()
        if xlim[1] - xlim[0] > 2:
            # Only preserve scale if some sensible value was recorded
            self._ax.set_xlim(*xlim)
            self._ax.set_ylim(*ylim)
            self._ax.set_autoscale_on(False)

        self.update_status(self.__doc__, redraw=False)

    def draw_view(self):
        print("Override the draw_view method to draw the view.")

    def update_status(self, text: Union[str, bytes], redraw=True):
        if self._status_text_widget is not None:
            self._status_text_widget.remove()
        self._status_text_widget = plt.figtext(.02, .02, text)
        if redraw:
            plt.draw()

    def _on_key_press_raw(self, event: KeyEvent):
        # Records commands

        if not self._controls_enabled:
            if event.key == "1":
                self._controls_enabled = True
                self.update_status(self.__doc__)
            return

        if self._pending_command_text is None:
            if event.key == '/':
                # Staring command mode
                self._pending_command_text = ""
                self.update_status("/")
                return
            self._on_key_press(event)
        else:
            if event.key == 'enter':
                # Finish typing command
                text = self._pending_command_text
                self._pending_command_text = None
                if len(text) > 0:
                    if not self._on_command(text):
                        self.update_status("Unknown command: " + text + ". Type /help for help.")
            elif event.key == 'escape':
                # Exit typing command
                self._pending_command_text = None
                self.update_status(self.__doc__)
            else:
                if event.key == 'backspace':
                    if len(self._pending_command_text) > 0:
                        self._pending_command_text = self._pending_command_text[:-1]
                elif len(event.key) > 1:
                    pass  # Pressing "shift", "control", "left", etc.
                else:
                    self._pending_command_text += event.key
                self.update_status("/" + self._pending_command_text)

    def _on_key_press(self, event: KeyEvent):
        pass

    def _on_command(self, text: str) -> bool:
        return False

    def _on_mouse_click(self, event: MouseEvent):
        pass

    def detach(self):
        self._fig.canvas.mpl_disconnect(self._key_handler_id)
        self._fig.canvas.mpl_disconnect(self._mouse_handler_id)

    def create_image(self, time_point: TimePoint, show_next_time_point: bool):
        """Creates an image suitable for display purposes. IF show_next_time_point is set to True, then then a color
        image will be created with the next image in red, and the current image in green."""
        time_point_images = time_point.load_images()
        if time_point_images is None:
            return None
        if show_next_time_point:
            image_shape = time_point_images.shape

            rgb_images = numpy.zeros((image_shape[0], image_shape[1], image_shape[2], 3), dtype='float')
            rgb_images[:,:,:,1] = time_point_images  # Green channel is current image
            try:
                next_time_point = self._experiment.get_next_time_point(time_point)
                next_time_point_images = next_time_point.load_images()
                rgb_images[:,:,:,0] = next_time_point_images # Red channel is next image
            except KeyError:
                pass  # There is no next time point, ignore
            time_point_images = rgb_images / rgb_images.max()
        return time_point_images

    @staticmethod
    def get_closest_particle(particles: Iterable[Particle], x: Optional[int], y: Optional[int], z: Optional[int], max_distance: int = 100000):
        """Gets the particle closest ot the given position. If z is missing, it is ignored. If x or y are missing,
        None is returned.
        """
        if x is None or y is None:
            return None # Mouse outside figure, so x or y are None
        ignore_z = False
        if z is None:
            z = 0
            ignore_z = True
        search_position = Particle(x, y, z)
        return imaging.get_closest_particle(particles, search_position, ignore_z=ignore_z, max_distance=max_distance)


_visualizer = None # Reference to prevent event handler from being garbage collected


def _configure_matplotlib():
    plt.rcParams['keymap.forward'] = []
    plt.rcParams['keymap.back'] = ['backspace']
    plt.rcParams['keymap.fullscreen'] = ['ctrl+f']
    plt.rcParams['keymap.save'] = ['ctrl+s']
    plt.rcParams['keymap.xscale'] = []
    plt.rcParams['keymap.yscale'] = []
    plt.rcParams['keymap.quit'] = ['ctrl+w','cmd+w']
    plt.rcParams['font.family'] = ['serif']
    plt.rcParams['font.serif'] = ['Times New Roman', 'Times']


def activate(visualizer: Visualizer) -> None:
    _configure_matplotlib()

    global _visualizer
    if _visualizer is not None:
        # Unregister old event handlers
        _visualizer.detach()

    _visualizer = visualizer
    _visualizer.draw_view()

