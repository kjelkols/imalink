import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import io
import os
import piexif  # For on-the-fly EXIF parsing

# Use our modern data access layer
import database
from models import SourceFile

THUMBNAIL_DISPLAY_SIZE = (120, 120)

class PhotoViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Photo Viewer")
        self.geometry("1000x700")

        # This list will hold dictionaries containing the PhotoImage and the SourceFile object
        self.all_photos = self.load_photos()
        self.filtered_photos = self.all_photos

        # Top frame: search
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(top_frame, text="Søk (filnavn):").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self.apply_filter())

        # Canvas with scrollbar for thumbnails
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.frame = ttk.Frame(self.canvas)

        self.frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.bind("<Configure>", self.refresh_grid)

        self.display_thumbnails()

    def load_photos(self):
        """
        Loads photos using the new data access layer.
        """
        print("Loading photos from database...")
        source_files = database.get_all_sourcefiles()
        photos = []
        for sf in source_files:
            if not sf.thumbnail:
                continue
            try:
                img = Image.open(io.BytesIO(sf.thumbnail))
                tk_img = ImageTk.PhotoImage(img)
                photos.append({
                    "tk_image": tk_img,
                    "source_file": sf  # Store the entire SourceFile object
                })
            except Exception as e:
                print(f"Could not load thumbnail for {sf.filename}: {e}")
        print(f"Loaded {len(photos)} photos.")
        return photos

    def display_thumbnails(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

        if not self.filtered_photos:
            ttk.Label(self.frame, text="Ingen bilder funnet.").pack()
            return

        cols = max(1, self.winfo_width() // (THUMBNAIL_DISPLAY_SIZE[0] + 20))
        for i, photo_data in enumerate(self.filtered_photos):
            row, col = divmod(i, cols)
            sf = photo_data["source_file"]

            btn = ttk.Button(
                self.frame,
                image=photo_data["tk_image"],
                command=lambda p=sf: self.show_exif(p)
            )
            btn.grid(row=row * 2, column=col, padx=5, pady=5)

            lbl = ttk.Label(self.frame, text=os.path.basename(sf.filename)[:20])
            lbl.grid(row=row * 2 + 1, column=col, padx=5, pady=0)

    def refresh_grid(self, event=None):
        self.display_thumbnails()

    def apply_filter(self):
        term = self.search_var.get().lower()
        if not term:
            self.filtered_photos = self.all_photos
        else:
            self.filtered_photos = [
                p for p in self.all_photos
                if term in p["source_file"].filename.lower()
            ]
        self.display_thumbnails()

    def show_exif(self, source_file: SourceFile):
        exif_win = tk.Toplevel(self)
        exif_win.title(source_file.filename)
        exif_win.geometry("600x450")

        open_btn = ttk.Button(
            exif_win,
            text="Åpne bilde",
            command=lambda: self.open_image(source_file.filename)
        )
        open_btn.pack(pady=5)

        tree = ttk.Treeview(exif_win)
        tree.pack(fill="both", expand=True)
        tree["columns"] = ("value",)
        tree.column("#0", width=150, minwidth=100, stretch=tk.NO)
        tree.column("value", width=400, anchor="w")
        tree.heading("#0", text="Tag", anchor="w")
        tree.heading("value", text="Verdi", anchor="w")

        if source_file.exif_data:
            try:
                exif_dict = piexif.load(source_file.exif_data)
                for ifd_name in exif_dict:
                    if ifd_name == "thumbnail":
                        continue
                    ifd_node = tree.insert("", "end", text=ifd_name, open=True)
                    for tag, value in exif_dict[ifd_name].items():
                        tag_name = piexif.TAGS.get(ifd_name, {}).get(tag, {}).get('name', f'UnknownTag {tag}')
                        if isinstance(value, bytes) and len(value) > 50:
                            val_str = f"{value[:50]!r}... (len={len(value)})"
                        else:
                            val_str = str(value)
                        tree.insert(ifd_node, "end", text=tag_name, values=(val_str,))
            except Exception as e:
                tree.insert("", "end", text="Error", values=(f"Could not parse EXIF: {e}",))
        else:
            tree.insert("", "end", text="Info", values=("No EXIF data available.",))

    def open_image(self, filepath):
        if not os.path.exists(filepath):
            messagebox.showerror("Feil", f"Filen finnes ikke:\n{filepath}")
            return

        try:
            img = Image.open(filepath)
            img.thumbnail((self.winfo_screenwidth() - 100, self.winfo_screenheight() - 100))

            win = tk.Toplevel(self)
            win.title(f"Original: {os.path.basename(filepath)}")

            tk_img = ImageTk.PhotoImage(img)
            lbl = tk.Label(win, image=tk_img)
            lbl.image = tk_img
            lbl.pack(fill="both", expand=True)
        except Exception as e:
            messagebox.showerror("Feil", f"Kunne ikke åpne bildet:\n{e}")

if __name__ == "__main__":
    database.init_db()
    app = PhotoViewer()
    app.mainloop()
