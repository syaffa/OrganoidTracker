import numpy
from numpy.core.multiarray import ndarray

from ai_track.core.image_loader import ImageFilter


class ThresholdFilter(ImageFilter):

    _noise_limit: int  # Scaled 0 to 255

    def __init__(self, noise_limit: float = 0.08):
        """noise_limit = 0.5 would remove all pixels of less than 50% of the max intensity of the image."""
        self._noise_limit = int(noise_limit * 255)

    def filter(self, image_8bit: ndarray):
        image_8bit[image_8bit < self._noise_limit] = 0

    def copy(self) -> ImageFilter:
        return ThresholdFilter(self._noise_limit / 255)

    def get_name(self) -> str:
        return "Threshold"


class GaussianBlurFilter(ImageFilter):
    """Applies a Gaussian blur in 2D."""

    _blur_radius: int

    def __init__(self, blur_radius: int = 5):
        self._blur_radius = blur_radius

    def filter(self, image_8bit: ndarray):
        import cv2

        out = numpy.empty_like(image_8bit[0])
        for z in range(image_8bit.shape[0]):
            slice = image_8bit[z]
            cv2.GaussianBlur(slice, (self._blur_radius, self._blur_radius), 0, out)
            image_8bit[z] = out

    def copy(self) -> ImageFilter:
        return GaussianBlurFilter(self._blur_radius)

    def get_name(self) -> str:
        return "Gaussian blur"
