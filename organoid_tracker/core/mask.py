from typing import Optional, Callable

import mahotas
import numpy
from numpy import ndarray
from scipy.ndimage import binary_dilation

from organoid_tracker.core.bounding_box import BoundingBox
from organoid_tracker.core.images import Image
from organoid_tracker.core.position import Position


class OutsideImageError(Exception):
    """Thrown when a mask falls completely outside an image."""
    pass


class Mask:
    """Class used for drawing and applying masks.

    - First, you set the bounds using one of the set_bounds methods.
    - Second, you create the mask using add_from_labeled, dilate, etc. (or draw your mask directly on get_mask_array)
    - Third, you apply the mask to an image using
    """

    _offset_x: int  # Inclusive
    _offset_y: int  # Inclusive
    _offset_z: int  # Inclusive
    _max_x: int  # Exclusive
    _max_y: int  # Exclusive
    _max_z: int  # Exclusive

    _mask: Optional[ndarray] = None  # Should only contain 1 and 0

    def __init__(self, box: BoundingBox):
        self._offset_x = box.min_x
        self._offset_y = box.min_y
        self._offset_z = box.min_z
        self._max_x = box.max_x
        self._max_y = box.max_y
        self._max_z = box.max_z

    @property
    def offset_x(self):
        return self._offset_x

    @property
    def offset_y(self):
        return self._offset_y

    @property
    def offset_z(self):
        return self._offset_z

    def set_bounds(self, box: BoundingBox):
        """Shrinks the bounding box to the given box. In this way, smaller arrays for the mask can be
        allocated. Setting a bounding box twice or setting it after get_mask_array
        has been called is not allowed."""
        self.set_bounds_exact(box.min_x, box.min_y, box.min_z, box.max_x, box.max_y, box.max_z)

    def set_bounds_around(self, x: float, y: float, z: float, padding_x: float, padding_y: float, padding_z: float):
        """Shrinks the bounding box of the shape that is going to be drawn. In this way, smaller arrays for the mask can be
        allocated. Setting a bounding box twice or setting it after get_mask_array has been called is not allowed.

        If all three paddings are set to 0, an image of exactly 1 pixel will remain."""
        self.set_bounds_exact(x - padding_x, y - padding_y, z - padding_z,
                              x + padding_x + 1, y + padding_y + 1, z + padding_z + 1)

    def set_bounds_exact(self, min_x: float, min_y: float, min_z: float, max_x: float, max_y: float, max_z: float):
        """Shrinks the bounding box of the shape that is going to be drawn. In this way, smaller arrays for the mask can be
        allocated. Setting a bounding box twice or setting it after get_mask_array has been called is not allowed."""
        if self._mask is not None:
            raise ValueError("Mask already created, cannot resize anymore")
        self._offset_x = max(self._offset_x, int(min_x))
        self._offset_y = max(self._offset_y, int(min_y))
        self._offset_z = max(self._offset_z, int(min_z))
        self._max_x = min(self._max_x, int(max_x))
        self._max_y = min(self._max_y, int(max_y))
        self._max_z = min(self._max_z, int(max_z))

    def center_around(self, position: Position):
        """Centers this mask around the given position. So offset_x will become smaller than position.x and max_x will
        become larger, and position.x will be halfway. Same for the y and z axis."""
        size_x = self._max_x - self._offset_x
        size_y = self._max_y - self._offset_y
        size_z = self._max_z - self._offset_z

        self._offset_x = int(position.x - size_x / 2)
        self._offset_y = int(position.y - size_y / 2)
        self._offset_z = int(position.z - size_z / 2)
        self._max_x = self._offset_x + size_x
        self._max_y = self._offset_y + size_y
        self._max_z = self._offset_z + size_z

    def get_mask_array(self) -> ndarray:
        """Gets a 3D array to draw the mask on. Make sure to set appropriate bounds for this array first. Note that to
        save memory the coords of this array are offset by (offset_z, offset_y, offset_x), so pixel (0, 0, 0) in this
        array is actually pixel (offset_x, offset_y, offset_z) when applied to an image.

        This array only contains the numbers 0 and 1. You are allowed to modify this array in order to draw a mask, but
        make sure to only use the values 0 and 1. You can also draw a mask using the add_from_ functions.
        """
        if self._mask is None:
            size_x = self._max_x - self._offset_x
            size_y = self._max_y - self._offset_y
            size_z = self._max_z - self._offset_z
            if size_x <= 0 or size_y <= 0 or size_z <= 0:
                raise OutsideImageError()  # Attempting to create mask of size 0
            self._mask = numpy.zeros((size_z, size_y, size_x), dtype=numpy.uint8)
        return self._mask

    def create_masked_and_normalized_image(self, image: Image):
        """Create normalized subimage (floating point numbers from 0 to 1). Throws OutsideImageError when the mask is
        fully outside the image. Pixels outside the mask are set to NaN."""
        image_for_masking = image.array[int(self._offset_z - image.offset.z):int(self._max_z - image.offset.z),
                            int(self._offset_y - image.offset.y):int(self._max_y - image.offset.y),
                            int(self._offset_x - image.offset.x):int(self._max_x - image.offset.x)].astype(
            dtype=numpy.float32)
        try:
            image_for_masking /= image_for_masking.max()
        except ValueError:
            raise OutsideImageError()

        # Crop mask to same size as subimage
        mask = self._mask[0:image_for_masking.shape[0], 0:image_for_masking.shape[1], 0:image_for_masking.shape[2]]

        # Apply mask
        image_for_masking[mask == 0] = numpy.NAN
        return image_for_masking

    def create_masked_image(self, image: Image) -> ndarray:
        """Create subimage where all pixels outside the mask are set to 0. Raises OutsideImageError if the mask is fully
        outside the given image."""
        image_for_masking: ndarray = image.array[self._offset_z - int(image.offset.z):self._max_z - int(image.offset.z),
                                     self._offset_y - int(image.offset.y):self._max_y - int(image.offset.y),
                                     self._offset_x - int(image.offset.x):self._max_x - int(image.offset.x)]
        if image_for_masking.size == 0:
            raise OutsideImageError()
        image_for_masking = image_for_masking.copy()

        # Crop mask to same size as subimage
        mask = self._mask[0:image_for_masking.shape[0], 0:image_for_masking.shape[1], 0:image_for_masking.shape[2]]

        # Apply mask
        image_for_masking[mask == 0] = 0
        return image_for_masking

    def add_from_labeled(self, labeled_image: ndarray, label: int):
        """This adds all values of the given full size image with the given color (== label) to the mask."""
        array = self.get_mask_array()
        cropped_image = labeled_image[self._offset_z:self._max_z,
                        self._offset_y:self._max_y,
                        self._offset_x:self._max_x]
        array[cropped_image == label] = 1

    def add_from_function(self, func: Callable[[ndarray, ndarray, ndarray], ndarray]):
        """Calls the function (x, y, z) -> bool for all coordinates in the mask, and expands the mask to the coords for
        which the function returns True.

        Note: the function is called with numpy arrays instead of single values, so that the function does not need to
        be called over and over, but just once.

        Example for drawing a sphere of radius r around (0, 0, 0):

            self.add_from_function(lambda x, y, z: x ** 2 + y ** 2 + z ** 2 <= r ** 2)
        """
        array = self.get_mask_array()

        xaxis = numpy.linspace(self._offset_y, self._max_x - 1, array.shape[2])
        yaxis = numpy.linspace(self._offset_y, self._max_y - 1, array.shape[1])
        zaxis = numpy.linspace(self._offset_z, self._max_z - 1, array.shape[0])
        result_xyz = func(xaxis[:, None, None], yaxis[None, :, None], zaxis[None, None, :])
        result_zyx = numpy.moveaxis(result_xyz, [2, 0], [0, 2])
        array[result_zyx == True] = 1

    def dilate_xyz(self, iterations: int = 1):
        """Dilates the image in the xyz direction."""
        mask = self.get_mask_array()
        for i in range(iterations):
            mask = mahotas.dilate(mask)
        self._mask = mask

    def dilate_xy(self, iterations: int = 1):
        """Dilates the mask image in the xy direction."""
        if iterations == 0:
            return
        array = self.get_mask_array()
        temp_out = numpy.empty_like(array[0])
        for layer_index in range(len(array)):
            layer = array[layer_index]
            binary_dilation(layer, iterations=iterations, output=temp_out)
            array[layer_index] = temp_out

    def __repr__(self) -> str:
        return f"<Mask from ({self._offset_x}, {self._offset_y}, {self._offset_z})" \
            f" to ({self._max_x}, {self._max_y}, {self._max_z})>"

    def has_zero_volume(self) -> bool:
        """If this mask has no volume, get_mask_array and related methods will fail."""
        return self._offset_x >= self._max_x or self._offset_y >= self._max_y or self._offset_z >= self._max_z

    def count_pixels(self) -> int:
        """Returns the amount of pixels in the mask. Note: if the mask contains illegal values (values that are not 1
        or 0), this will return an incorrect value. If the """
        if self._mask is None:
            raise ValueError("No mask has been created yet")
        return int(self._mask.sum())


def create_mask_for(image: Image) -> Mask:
    """Creates a mask that will never expand beyond the size of the given image."""
    return Mask(image.bounding_box())
