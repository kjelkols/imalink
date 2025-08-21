from PIL import Image, ExifTags
import json
from fractions import Fraction

def make_serializable(val):
    """
    Recursively convert EXIF values into JSON-serializable types.
    """
    if isinstance(val, bytes):
        return val.decode(errors="ignore")
    elif isinstance(val, (int, float, str)):
        return val
    elif isinstance(val, Fraction):
        return float(val)
    elif hasattr(val, "numerator") and hasattr(val, "denominator"):
        try:
            return float(val)
        except Exception:
            return str(val)
    elif isinstance(val, (list, tuple)):
        return [make_serializable(v) for v in val]
    elif isinstance(val, dict):
        return {str(k): make_serializable(v) for k, v in val.items()}
    else:
        return str(val)

def convert_gps_to_degrees(value):
    """Convert GPS tuple to float degrees."""
    d, m, s = [float(v) for v in value]
    return d + (m / 60.0) + (s / 3600.0)

def ZZZextract_gps(exif_data):
    """Extract and convert GPS data into decimal lat/lon."""
    if "GPSInfo" not in exif_data:
        return None

    gps_info = exif_data["GPSInfo"]

    gps_data = {ExifTags.GPSTAGS.get(k, str(k)): v for k, v in gps_info.items()}
    gps_data = {k: make_serializable(v) for k, v in gps_data.items()}

    lat = lon = None
    if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
        lat = convert_gps_to_degrees(gps_data["GPSLatitude"])
        if gps_data["GPSLatitudeRef"] in ["S", "s"]:
            lat = -lat
    if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
        lon = convert_gps_to_degrees(gps_data["GPSLongitude"])
        if gps_data["GPSLongitudeRef"] in ["W", "w"]:
            lon = -lon

    if lat is not None and lon is not None:
        gps_data["LatitudeDecimal"] = lat
        gps_data["LongitudeDecimal"] = lon

    return gps_data

def extract_gps(exif_data):
    """Extract and convert GPS data into decimal lat/lon + clean fields."""
    if "GPSInfo" not in exif_data:
        return None

    gps_info = exif_data["GPSInfo"]
    gps_data = {ExifTags.GPSTAGS.get(k, str(k)): make_serializable(v) for k, v in gps_info.items()}

    result = {}

    # Latitude
    if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
        lat = convert_gps_to_degrees(gps_data["GPSLatitude"])
        if gps_data["GPSLatitudeRef"].upper() == "S":
            lat = -lat
        result["LatitudeDecimal"] = lat

    # Longitude
    if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
        lon = convert_gps_to_degrees(gps_data["GPSLongitude"])
        if gps_data["GPSLongitudeRef"].upper() == "W":
            lon = -lon
        result["LongitudeDecimal"] = lon

    # Altitude
    if "GPSAltitude" in gps_data:
        result["AltitudeMeters"] = gps_data["GPSAltitude"]

    # Timestamp (if present)
    if "GPSTimeStamp" in gps_data and "GPSDateStamp" in gps_data:
        result["TimestampUTC"] = f"{gps_data['GPSDateStamp']}T" + ":".join(map(str, gps_data["GPSTimeStamp"]))

    # Always keep raw GPS block too (optional)
    result["Raw"] = gps_data  

    return result

def extract_exif(path):
    with Image.open(path) as img:
        exif_raw = img._getexif()
        if not exif_raw:
            return {}

        exif_data = {}
        for tag, value in exif_raw.items():
            tag_name = ExifTags.TAGS.get(tag, str(tag))
            exif_data[tag_name] = make_serializable(value)

        # Add GPS if present
        gps_data = extract_gps(exif_data)
        if gps_data:
            exif_data["GPSParsed"] = gps_data

        return exif_data


if __name__ == "__main__":
    path = "sample.jpg"
    exif_dict = extract_exif(path)

    print("=== Readable EXIF Dictionary ===")
    for key, value in exif_dict.items():
        print(f"{key}: {value}")

    print("\n=== JSON Serialized ===")
    print(json.dumps(exif_dict, indent=2, ensure_ascii=False))
