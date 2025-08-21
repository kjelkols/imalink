import logging
import piexif
from typing import Optional, Tuple


def parse_taken_timestamp(exif_data: bytes) -> Optional[str]:
    """Extracts the photo's creation timestamp from EXIF data."""
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