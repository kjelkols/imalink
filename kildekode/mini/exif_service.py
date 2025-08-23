import logging
import piexif
from typing import Optional, Tuple, List
from PIL import Image


def get_raw_exif_from_image(image_path: str) -> Optional[bytes]:
    """
    Extracts the raw EXIF data from an image file.
    """
    try:
        with Image.open(image_path) as img:
            return img.info.get('exif')
    except Exception as e:
        logging.warning(f"Could not read EXIF data from {image_path}: {e}")
        return None


def parse_taken_timestamp(exif_data: bytes) -> Optional[str]:
    """Extracts the photo's creation timestamp from EXIF data."""
    if not exif_data:
        return None
    try:
        exif_dict = piexif.load(exif_data)
        date_bytes = exif_dict.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
        if date_bytes:
            return date_bytes.decode("utf-8")
    except (piexif.InvalidImageDataError, ValueError, KeyError) as e:
        logging.warning(f"Could not parse timestamp from EXIF: {e}")
    return None


def parse_gps_coordinates(exif_data: bytes) -> Optional[Tuple[float, float]]:
    """Extracts GPS coordinates from EXIF data and converts them to decimal degrees."""
    if not exif_data:
        return None
    try:
        exif_dict = piexif.load(exif_data)
        gps = exif_dict.get("GPS")
        if gps:
            lat_tuple = gps.get(piexif.GPSIFD.GPSLatitude)
            lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef)
            lon_tuple = gps.get(piexif.GPSIFD.GPSLongitude)
            lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef)

            if all((lat_tuple, lat_ref, lon_tuple, lon_ref)):
                def convert_to_decimal(coord_tuple: tuple) -> float:
                    d = coord_tuple[0][0] / coord_tuple[0][1]
                    m = coord_tuple[1][0] / coord_tuple[1][1]
                    s = coord_tuple[2][0] / coord_tuple[2][1]
                    return d + (m / 60.0) + (s / 3600.0)

                latitude = convert_to_decimal(lat_tuple)
                if lat_ref.decode() == 'S':
                    latitude = -latitude

                longitude = convert_to_decimal(lon_tuple)
                if lon_ref.decode() == 'W':
                    longitude = -longitude

                return latitude, longitude
    except (piexif.InvalidImageDataError, ValueError, KeyError, ZeroDivisionError) as e:
        logging.warning(f"Could not parse GPS from EXIF: {e}")
    return None


def clean_exif_data(exif_data: bytes, tags_to_remove: List[str]) -> bytes:
    """
    Removes a list of specified tags from EXIF data to reduce size.
    Recognized tags: "thumbnail", "MakerNote", "UserComment".
    Returns the modified EXIF data as bytes.
    """
    if not exif_data:
        return exif_data
    try:
        exif_dict = piexif.load(exif_data)

        for tag_name in tags_to_remove:
            if tag_name == "thumbnail":
                exif_dict["thumbnail"] = None
            elif tag_name == "MakerNote":
                if "Exif" in exif_dict and piexif.ExifIFD.MakerNote in exif_dict["Exif"]:
                    del exif_dict["Exif"][piexif.ExifIFD.MakerNote]
            elif tag_name == "UserComment":
                if "Exif" in exif_dict and piexif.ExifIFD.UserComment in exif_dict["Exif"]:
                    del exif_dict["Exif"][piexif.ExifIFD.UserComment]

        return piexif.dump(exif_dict)
    except Exception as e:
        logging.warning(f"Could not clean EXIF data: {e}")
        return exif_data  # Return original data on error