import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import io
import json
import sqlite3
import os
from backend.database import get_connection

THUMBNAIL_DISPLAY_SIZE = (120, 120)

class PhotoViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Photo Viewer")
        self.geometry("1000x700")

        self.conn = get_connection()
        self.all_photos = self.load_photos()
        self.filtered_photos = self.all_photos

        # Top frame: search
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(top_frame, text="Søk:").pack(side="left")
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
        self.canvas.create_window((0,0), window=self.frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.bind("<Configure>", lambda e: self.refresh_grid())

        self.display_thumbnails()

    def load_photos(self):
        c = self.conn.cursor()
        c.execute("SELECT id, filename, thumbnail, exif_data FROM photos")
        rows = c.fetchall()
        photos = []
        for row in rows:
            photo_id, filename, thumb_bytes, exif_json = row
            img = Image.open(io.BytesIO(thumb_bytes))
            img = img.resize(THUMBNAIL_DISPLAY_SIZE, Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            exif_data = json.loads(exif_json)
            photos.append({
                "id": photo_id,
                "filename": filename,
                "thumbnail": tk_img,
                "exif": exif_data
            })
        return photos

    def display_thumbnails(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

        if not self.filtered_photos:
            ttk.Label(self.frame, text="Ingen treff.").pack()
            return

        cols = max(1, self.winfo_width() // (THUMBNAIL_DISPLAY_SIZE[0] + 20))
        for i, photo in enumerate(self.filtered_photos):
            row, col = divmod(i, cols)

            btn = ttk.Button(
                self.frame,
                image=photo["thumbnail"],
                command=lambda p=photo: self.show_exif(p)
            )
            btn.grid(row=row*2, column=col, padx=5, pady=5)

            lbl = ttk.Label(self.frame, text=photo["filename"].split("\\")[-1][:20])
            lbl.grid(row=row*2+1, column=col, padx=5, pady=0)

    def refresh_grid(self):
        self.display_thumbnails()

    def apply_filter(self):
        term = self.search_var.get().lower()
        if not term:
            self.filtered_photos = self.all_photos
        else:
            self.filtered_photos = [
                p for p in self.all_photos
                if term in p["filename"].lower() or term in json.dumps(p["exif"]).lower()
            ]
        self.display_thumbnails()

    def show_exif(self, photo):
        exif_win = tk.Toplevel(self)
        exif_win.title(photo["filename"])
        exif_win.geometry("600x450")

        # Button to open original
        open_btn = ttk.Button(
            exif_win,
            text="Åpne bilde",
            command=lambda: self.open_image(photo["filename"])
        )
        open_btn.pack(pady=5)

        tree = ttk.Treeview(exif_win)
        tree.pack(fill="both", expand=True)

        def insert_dict(parent, d):
            for k, v in d.items():
                if isinstance(v, dict):
                    node = tree.insert(parent, "end", text=str(k))
                    insert_dict(node, v)
                elif isinstance(v, list):
                    node = tree.insert(parent, "end", text=str(k))
                    for i, item in enumerate(v):
                        tree.insert(node, "end", text=f"[{i}]", values=(str(item),))
                else:
                    tree.insert(parent, "end", text=str(k), values=(str(v),))

        tree["columns"] = ("value",)
        tree.column("value", width=300, anchor="w")
        tree.heading("value", text="Verdi")

        insert_dict("", photo["exif"])

    def open_image(self, filepath):
        """Åpne originalbilde i nytt vindu."""
        if not os.path.exists(filepath):
            tk.messagebox.showerror("Feil", f"Filen finnes ikke:\n{filepath}")
            return

        img = Image.open(filepath)

        # Tilpass til skjerm
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        img.thumbnail((screen_w-100, screen_h-100), Image.LANCZOS)

        win = tk.Toplevel(self)
        win.title(f"Original: {os.path.basename(filepath)}")

        tk_img = ImageTk.PhotoImage(img)
        lbl = tk.Label(win, image=tk_img)
        lbl.image = tk_img
        lbl.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = PhotoViewer()
    app.mainloop()
