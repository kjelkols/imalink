import logging
from pydantic import BaseModel, Field
from typing import Optional, Tuple

from services import exif as exif_service

class SourceFile(BaseModel):
    id: Optional[int] = None
    filename: str
    image_hash: Optional[str] = None
    thumbnail: Optional[bytes] = Field(default=None, repr=False)
    exif_data: Optional[bytes] = Field(default=None, repr=False)

    @property
    def taken_timestamp(self) -> Optional[str]:
        """Delegates timestamp parsing to the exif_service."""
        if self.exif_data:
            return exif_service.parse_taken_timestamp(self.exif_data)
        return None

    @property
    def gps_coordinates(self) -> Optional[Tuple[float, float]]:
        """Delegates GPS parsing to the exif_service."""
        if self.exif_data:
            return exif_service.parse_gps_coordinates(self.exif_data)
        return None


if __name__ == "__main__":
    import database

    logging.basicConfig(level=logging.INFO)

    print("Fetching source file with ID 4...")
    sourcefile = database.get_sourcefile_by_id(4)

    if sourcefile:
        print(f"File path: {sourcefile.filename}")
        print(f"Timestamp: {sourcefile.taken_timestamp or 'N/A'}")
        print(f"GPS Coordinates: {sourcefile.gps_coordinates or 'N/A'}")

        print("\nSourceFile object:")
        print(sourcefile)
        print (len(sourcefile.exif_data) if sourcefile.exif_data else "No EXIF data")
    else:
        print("Source file with ID 4 not found.")
 