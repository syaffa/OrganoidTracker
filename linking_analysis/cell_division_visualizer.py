from matplotlib.backend_bases import KeyEvent
from matplotlib.figure import Figure
from imaging import Particle, Experiment
from imaging.particle_list_visualizer import ParticleListVisualizer
from linking_analysis import mother_finder
from typing import List, Optional


def _get_mothers(experiment: Experiment) -> List[Particle]:
    graph = experiment.particle_links()
    if graph is None:
        return []
    all_mothers = list(mother_finder.find_mothers(graph))
    return all_mothers


class CellDivisionVisualizer(ParticleListVisualizer):
    """Shows cells that are about to divide.
    Use the left/right arrow keys to move to the next cell division.
    Press M to exit this view."""

    def __init__(self, experiment: Experiment, figure: Figure, mother: Optional[Particle]):
        super().__init__(experiment, figure, chosen_particle=mother, all_particles=_get_mothers(experiment))

    def get_message_no_particles(self):
        return "No mothers found. Is the linking data missing?"

    def get_message_press_right(self):
        return "No mother found at mouse position.\nPress the right arrow key to view the first mother in the sample."

    def get_title(self, _all_mothers: List[Particle], _mother_index: int):
        mother = _all_mothers[_mother_index]
        recognized_str = ""
        if self._was_recognized(mother) is False:
            recognized_str = "    (NOT RECOGNIZED)"
        return "Mother " + str(self._current_particle_index + 1) + "/" + str(len(self._particle_list))\
               + recognized_str + "\n" + str(mother)

    def _was_recognized(self, mother: Particle) -> Optional[bool]:
        """Gets if a mother was correctly recognized by the scratch graph. Returns None if there is no scratch graph."""
        main_graph = self._experiment.particle_links()
        scratch_graph = self._experiment.particle_links_scratch()
        if main_graph is None or scratch_graph is None:
            return None

        try:
            connections_main = main_graph[mother]
            connections_scratch = scratch_graph[mother]
            return set(connections_main) == set(connections_scratch)
        except KeyError:
            return False

    def _on_key_press(self, event: KeyEvent):
        if event.key == "m":
            self.goto_full_image()
        else:
            super()._on_key_press(event)