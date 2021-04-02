#!/usr/bin/env python3

# convert.py
# written by m.c.dixon 2020
# function to convert image to byte array

from io import BytesIO
from PIL import Image


def to_byte_array(image: Image) -> bytearray:
    image_byte_array: bytearray = BytesIO()
    try:
        image.save(image_byte_array, "PNG")
    except SystemError:
        return None
    except AttributeError:
        return None
    return image_byte_array.getvalue()
