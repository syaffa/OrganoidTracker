"""Extracting the tracks as measured by Guizela to a Graph object"""

from imaging import Particle
from manual_tracking.track_lib import Track
from networkx import Graph
from typing import List
import os
import pickle
import sys
import numpy


def extract_from_tracks(tracks_dir : str, max_frame: int = 5000) -> Graph:
    """Extracts all positions from the track files in tracks_dir, saves them to output_dir"""

    _fix_python_path_for_pickle()
    graph = Graph()

    tracks = _read_track_files(tracks_dir, graph, max_frame=max_frame)
    _read_lineage_file(tracks_dir, graph, tracks, max_frame=max_frame)

    return graph


def _read_track_files(tracks_dir: str, graph: Graph, max_frame: int = 5000) -> List[Track]:
    """Adds all tracks to the graph, and returns the original tracks"""
    track_files = os.listdir(tracks_dir)
    print("Found " + str(len(track_files)) + " files to analyse")

    track_index = 0
    tracks = []
    while True:
        track_file = os.path.join(tracks_dir, "track_%05d.p" % track_index)
        if not os.path.exists(track_file):
            break

        if track_index % 10 == 0:
            print("Reading track " + str(track_index))

        # Note that the first track will get id 0, the second id 1, etc. This is required for the lineages file
        tracks.append(_extract_links_from_track(track_file, graph, max_frame=max_frame))

        track_index += 1

    return tracks


def _read_lineage_file(tracks_dir: str, graph: Graph, tracks: List[Track], max_frame: int = 5000) -> None:
    """Connects the lineages in the graph based on information from the lineages.p file"""
    print("Reading lineages file")
    lineage_file = os.path.join(tracks_dir, "lineages.p")
    with open(lineage_file, "rb") as file_handle:
        lineages = pickle.load(file_handle, encoding = 'latin1')
        for lineage in lineages:
            mother_track = tracks[lineage[0]]
            child_track_1 = tracks[lineage[1]]
            child_track_2 = tracks[lineage[2]]

            first_frame_after_division = numpy.amin(child_track_1.t)
            if first_frame_after_division > max_frame:
                continue

            mother_last_snapshot = _get_cell_in_frame(mother_track, first_frame_after_division - 1)
            child_1_first_snapshot = _get_cell_in_frame(child_track_1, first_frame_after_division)
            child_2_first_snapshot = _get_cell_in_frame(child_track_2, first_frame_after_division)

            graph.add_edge(mother_last_snapshot, child_1_first_snapshot)
            graph.add_edge(mother_last_snapshot, child_2_first_snapshot)


def _get_cell_in_frame(track: Track, frame_number: int) -> Particle:
    position = track.get_pos(frame_number)
    particle = Particle(position[0], position[1], position[2])
    particle.with_frame_number(frame_number)
    return particle


def _extract_links_from_track(track_file: str, graph: Graph, max_frame: int = 5000) -> Track:
    with open(track_file, "rb") as file_handle:
        track = pickle.load(file_handle, encoding = 'latin1')
        current_particle = None

        for frame in track.t:
            if frame > max_frame:
                break

            previous_particle = current_particle
            current_particle = _get_cell_in_frame(track, frame)
            graph.add_node(current_particle)

            if previous_particle is not None:
                graph.add_edge(previous_particle, current_particle)

        return track


def _fix_python_path_for_pickle():
    # Inserts the current directory once to the Python module path
    # This makes Pickle able to find the necessary modules
    path = os.path.dirname(os.path.abspath(__file__))
    try :
        sys.path.index(path)
    except ValueError:
        print("Adding to Python path: " + path)
        sys.path.insert(0, path)