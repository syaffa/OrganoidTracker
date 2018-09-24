from os import path
from typing import Optional

import tifffile
from numpy import ndarray
import numpy

from autotrack.core import Experiment, ImageLoader, TimePoint, ImageResolution


def load_images_from_folder(experiment: Experiment, folder: str, file_name_format: str,
                            min_time_point: Optional[int] = None, max_time_point: Optional[int] = None,
                            resolution: Optional[ImageResolution] = None):
    if min_time_point is None:
        min_time_point = 1
    if max_time_point is None:
        max_time_point = 5000

    experiment.name.provide_automatic_name(path.basename(folder).replace("-stacks", ""))
    experiment.image_loader(TiffImageLoader(folder, file_name_format, resolution, min_time_point, max_time_point))

    # Create time points for all discovered image files
    time_point_number = max(1, min_time_point)
    while time_point_number <= max_time_point:
        file_name = path.join(folder, file_name_format % time_point_number)

        if not path.isfile(file_name):
            break

        experiment.get_or_add_time_point(time_point_number)
        time_point_number += 1


class TiffImageLoader(ImageLoader):

    _folder: str
    _file_name_format: str
    _resolution: ImageResolution
    _min_time_point: int
    _max_time_point: int

    def __init__(self, folder: str, file_name_format: str, resolution: Optional[ImageResolution] = None,
                 min_time_point: Optional[int] = None, max_time_point: Optional[int] = None):
        """Creates a loader for multi-page TIFF files. file_name_format is a format string (so containing something
        like %03d), accepting one parameter representing the time point number."""
        self._folder = folder
        self._file_name_format = file_name_format
        self._resolution = resolution
        self._min_time_point = min_time_point
        self._max_time_point = max_time_point

    def load_3d_image(self, time_point: TimePoint) -> Optional[ndarray]:
        if time_point.time_point_number() < self._min_time_point or\
                time_point.time_point_number() > self._max_time_point:
            return None

        file_name = path.join(self._folder, self._file_name_format % time_point.time_point_number())
        if not path.exists(file_name):
            return None
        with tifffile.TiffFile(file_name, movie=True) as f:
            # noinspection PyTypeChecker
            array = f.asarray(maxworkers=None)  # maxworkers=None makes image loader work on half of all cores
            if array.shape[-1] == 3 or array.shape[-1] == 4:
                # Convert RGB to grayscale
                array = numpy.dot(array[...,:3], [0.299, 0.587, 0.114])
            if len(array.shape) == 3:
                return array
            if len(array.shape) == 2:  # Support for 2d images
                outer = numpy.array((array,))
                return outer
            return None

    def get_resolution(self):
        if self._resolution is None:
            raise ValueError("Resolution not set")
        return self._resolution