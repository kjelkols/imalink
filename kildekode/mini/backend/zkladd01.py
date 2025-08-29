import io
import piexif
from PIL import Image

# Import the data model and the data access layer
import database
from models import SourceFile

def vis_thumbnail(thumbnail_bytes: bytes | None):
    """Displays image bytes using PIL."""
    if thumbnail_bytes:
        img = Image.open(io.BytesIO(thumbnail_bytes))
        img.show()
    else:
        print("Ingen thumbnail tilgjengelig.")


def main():
    """
    Fetches a single source file (ID=4) from the database and displays its info.
    """
    id = 4
    print("Henter bilde med ID=4...")
    # Fetch from the database module directly
    sourcefile = database.get_sourcefile_by_id(4)

    if sourcefile:
        print(f"\n--- Generell Info ---")
        print(f"Filsti: {sourcefile.filename}")
        print(f"Tatt dato: {sourcefile.taken_timestamp or 'Ukjent'}")
        print(f"GPS: {sourcefile.gps_coordinates or 'Ukjent'}")

        if sourcefile.thumbnail:
            thumb_kb = len(sourcefile.thumbnail) / 1024
            print(f"Thumbnail-størrelse: {thumb_kb:.2f} KB")
        else:
            print("Thumbnail-størrelse: 0 KB")

        if sourcefile.exif_data:
            exif_kb = len(sourcefile.exif_data) / 1024
            print(f"Total EXIF-størrelse: {exif_kb:.2f} KB")

            print("\n--- Analyse av EXIF-størrelse (Topp 10 største felter) ---")
            try:
                exif_dict = piexif.load(sourcefile.exif_data)
                all_tags = []
                for ifd_name in exif_dict:
                    if ifd_name == "thumbnail":
                        continue
                    for tag, value in exif_dict[ifd_name].items():
                        tag_name = piexif.TAGS.get(ifd_name, {}).get(tag, {}).get('name', f'UnknownTag {tag}')
                        # Only consider bytes values for size calculation, as others are negligible
                        size_in_bytes = len(value) if isinstance(value, bytes) else 0
                        all_tags.append((f"{ifd_name} - {tag_name}", size_in_bytes))

                all_tags.sort(key=lambda x: x[1], reverse=True)

                if not all_tags:
                    print("Fant ingen EXIF-felter å analysere.")
                else:
                    for name, size in all_tags[:10]:
                        if size > 0:
                            print(f" > {name}: {size / 1024:.2f} KB")
            except Exception as e:
                print(f"Kunne ikke analysere EXIF-data: {e}")
        else:
            print("EXIF-størrelse: 0 KB")

        vis_thumbnail(sourcefile.thumbnail)
    else:
        print("Fant ikke bilde med id=4.")


if __name__ == "__main__":
    main()
