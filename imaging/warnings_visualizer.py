from matplotlib.backend_bases import KeyEvent
from matplotlib.figure import Figure
from imaging import Particle, Experiment
from imaging.particle_list_visualizer import ParticleListVisualizer
from typing import List, Optional, Set


def _get_problematic_particles(experiment: Experiment) -> List[Particle]:
    particles = []
    graph = experiment.particle_links_scratch()
    if graph is None:
        # Create scratchpad from main links
        graph = experiment.particle_links()
        if graph is None:
            return []
        experiment.particle_links_scratch(graph.copy())
    for particle, data in graph.nodes(data=True):
        if "error" in data and data["error"] is not None:
            particles.append(particle)
        elif "warning" in data and data["warning"] is not None:
            particles.append(particle)
    return particles


class WarningsVisualizer(ParticleListVisualizer):
    """Shows all errors and warnings in the sample.
    Press E to exit this view (so that you can for example make a correction to the data).
    Press DELETE to delete an error or warning.
    """

    def __init__(self, experiment: Experiment, figure: Figure, start_particle: Optional[Particle]):
        super().__init__(experiment, figure, chosen_particle=start_particle, all_particles=_get_problematic_particles(experiment))

    def get_message_no_particles(self):
        return "No warnings or errors found. Hurray?"

    def get_message_press_right(self):
        return "No warnings or errors found at mouse position." \
               "\nPress the right arrow key to view the first warning in the sample."

    def get_title(self, particle_list: List[Particle], current_particle_index: int):
        particle = particle_list[current_particle_index]
        return "Error or warning " + str(current_particle_index + 1) + "/" + str(len(particle_list)) + \
               "\n" + str(self._get_warning(particle)) + "\n" + str(particle)

    def _get_warning(self, particle: Particle) -> Optional[str]:
        graph = self._experiment.particle_links_scratch()
        for node, data in graph.nodes(data=True):
            if node != particle:
                continue
            if "error" in data:
                return data["error"]
            if "warning" in data:
                return data["warning"]
            return None

    def _delete_warning(self):
        if self._current_particle_index < 0 or self._current_particle_index >= len(self._particle_list):
            return
        particle = self._particle_list[self._current_particle_index]
        self._experiment.particle_links_scratch().add_node(particle, error=None, warning=None)
        self._particle_list.remove(particle)
        if self._current_particle_index >= len(self._particle_list):
            self._current_particle_index-= 1 # Deleted last particle, go back to previous
        self.draw_view()

    def _on_key_press(self, event: KeyEvent):
        if event.key == "e":
            self.goto_full_image()
        elif event.key == "delete":
            self._delete_warning()
        else:
            super()._on_key_press(event)
