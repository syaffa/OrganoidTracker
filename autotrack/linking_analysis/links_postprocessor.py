from networkx import Graph

from autotrack.core.experiment import Experiment
from numpy import ndarray

from autotrack.core.particles import Particle
from autotrack.linking import existing_connections
from autotrack.linking_analysis import cell_appearance_finder


def postprocess(experiment: Experiment, margin_xy: int):
    _remove_particles_close_to_edge(experiment, margin_xy)
    _remove_spurs(experiment)


def _remove_particles_close_to_edge(experiment: Experiment, margin_xy: int):
    image_loader = experiment.image_loader()
    example_image = image_loader.get_image_stack(experiment.get_time_point(image_loader.get_first_time_point()))
    for time_point in experiment.time_points():
        for particle in list(experiment.particles.of_time_point(time_point)):
            if particle.x < margin_xy or particle.y < margin_xy or particle.x > example_image.shape[2] - margin_xy\
                    or particle.y > example_image.shape[1] - margin_xy:
                experiment.remove_particle(particle)


def _remove_spurs(experiment: Experiment):
    """Removes all very short tracks that end in a cell death."""
    graph = experiment.links.get_baseline_else_scratch()
    for particle in list(cell_appearance_finder.find_appeared_cells(graph)):
        _check_for_and_remove_spur(experiment, graph, particle)


def _check_for_and_remove_spur(experiment: Experiment, graph: Graph, particle: Particle):
    track_length = 0
    particles_in_track = [particle]

    while True:
        next_particles = existing_connections.find_future_particles(graph, particle)
        if len(next_particles) == 0:
            # End of track
            if track_length < 3:
                # Remove this track, it is too short
                for particle_in_track in particles_in_track:
                    experiment.remove_particle(particle_in_track)
            return
        if len(next_particles) > 1:
            # Cell division
            for next_particle in next_particles:
                _check_for_and_remove_spur(experiment, graph, next_particle)
            return

        particle = next_particles.pop()
        particles_in_track.append(particle)
        track_length += 1