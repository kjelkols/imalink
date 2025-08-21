from models import SourceFile
from PIL import Image
import io

def vis_thumbnail(thumbnail_bytes):
    if thumbnail_bytes:
        img = Image.open(io.BytesIO(thumbnail_bytes))
        img.show()
    else:
        print("Ingen thumbnail tilgjengelig.")

def main():
    sourcefile = SourceFile.get_by_id(1)
    if sourcefile:
        print(f"Filsti: {sourcefile.filename}")
        print(f"Rå EXIF-data: {sourcefile.exif_data}")
        vis_thumbnail(sourcefile.thumbnail)
    else:
        print("Fant ikke bilde med id=1.")

if __name__ == "__main__":
    main()