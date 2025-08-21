from pydantic import BaseModel
from typing import Optional, List

class SourceFile(BaseModel):
    id: Optional[int] = None
    filename: str
    thumbnail: Optional[bytes] = None
    exif_data: Optional[bytes] = None

    @classmethod
    def get_by_id(cls, sourcefile_id: int) -> Optional["SourceFile"]:
        import database
        return database.get_sourcefile_by_id(sourcefile_id)

    @classmethod
    def get_all(cls) -> List["SourceFile"]:
        import database
        return database.get_all_sourcefiles()

    def add(self):
        import database
        database.add_sourcefile(self.filename, self.thumbnail, self.exif_data)

# Denne metuden er et eksempel på hvordan du kan hente EXIF-data fra databasen
    def get_taken_timestamp(self) -> Optional[str]:
        try:
            import piexif
            if self.exif_data:
                exif_dict = piexif.load(self.exif_data)
                date_bytes = exif_dict["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
                if date_bytes:
                    return date_bytes.decode("utf-8")
        except Exception:
            pass
        return None

    def get_gps_coordinates(self) -> Optional[tuple]:
        try:
            import piexif
            if self.exif_data:
                exif_dict = piexif.load(self.exif_data)
                gps = exif_dict.get("GPS")
                if gps:
                    lat = gps.get(piexif.GPSIFD.GPSLatitude)
                    lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef)
                    lon = gps.get(piexif.GPSIFD.GPSLongitude)
                    lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef)
                    if lat and lat_ref and lon and lon_ref:
                        def convert(coord):
                            return coord[0][0]/coord[0][1] + coord[1][0]/coord[1][1]/60 + coord[2][0]/coord[2][1]/3600
                        latitude = convert(lat)
                        if lat_ref == b'S':
                            latitude = -latitude
                        longitude = convert(lon)
                        if lon_ref == b'W':
                            longitude = -longitude
                        return (latitude, longitude)
        except Exception:
            pass
        return None

if __name__ == "__main__":
    sourcefile = SourceFile.get_by_id(4)
    timestamp = sourcefile.get_taken_timestamp()
    print("piexif.ExifIFD.DateTimeOriginal=",timestamp)
    coordinates = sourcefile.get_gps_coordinates()
    print ("GPS Coordinates:", coordinates) if coordinates else print("Ingen GPS-data tilgjengelig.")
    print("Filsti:", sourcefile.filename)