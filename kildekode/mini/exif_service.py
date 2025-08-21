from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def extract_exif(image_path):
    exif_dict = {}
    with Image.open(image_path) as img:
        info = img._getexif() or {}
        for tag, value in info.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_tag = GPSTAGS.get(t, t)
                    gps_data[sub_tag] = value[t]
                exif_dict["GPSParsed"] = gps_data
            else:
                exif_dict[tag_name] = make_serializable(value)
    return exif_dict

def make_serializable(value):
    if isinstance(value, bytes):
        return value.decode(errors="ignore")
    if isinstance(value, (list, tuple)):
        return [make_serializable(v) for v in value]
    if isinstance(value, dict):
        return {k: make_serializable(v) for k, v in value.items()}
    return value
