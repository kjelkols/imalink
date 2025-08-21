import sqlite3
import json
import io
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

DB_FILE = "photos.db"

class PhotoBrowser(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Photo Browser")
        self.geometry("900x600")

        # Database
        self.conn = sqlite3.connect(DB_FILE)
        self.cur = self.conn.cursor()

        # Layout
        self.setup_ui()

        # Load photos
        self.load_photos()

    def setup_ui(self):
        # Main PanedWindow
        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True)

        # Left: photo list
        self.frame_list = ttk.Frame(pw)
        self.photo_listbox = tk.Listbox(self.frame_list, width=40)
        self.photo_listbox.pack(side=tk.LEFT, fill=tk.Y)

        self.scrollbar = ttk.Scrollbar(self.frame_list, orient=tk.VERTICAL, command=self.photo_listbox.yview)
        self.photo_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.photo_listbox.bind("<<ListboxSelect>>", self.on_select)

        pw.add(self.frame_list, weight=1)

        # Right: thumbnail + EXIF
        self.frame_detail = ttk.Frame(pw)

        self.thumb_label = ttk.Label(self.frame_detail)
        self.thumb_label.pack(pady=10)

        self.exif_text = tk.Text(self.frame_detail, wrap=tk.WORD, width=60)
        self.exif_text.pack(fill=tk.BOTH, expand=True)

        pw.add(self.frame_detail, weight=3)

    def load_photos(self):
        self.cur.execute("SELECT id, path FROM photos ORDER BY id")
        self.photos = self.cur.fetchall()
        for pid, path in self.photos:
            self.photo_listbox.insert(tk.END, f"[{pid}] {path}")

    def on_select(self, event):
        if not self.photo_listbox.curselection():
            return
        index = self.photo_listbox.curselection()[0]
        photo_id, path = self.photos[index]

        # Get thumbnail + exif
        self.cur.execute("SELECT thumb, exif FROM photos WHERE id=?", (photo_id,))
        row = self.cur.fetchone()
        if not row:
            return
        thumb_bytes, exif_json = row

        # Show thumbnail
        try:
            image = Image.open(io.BytesIO(thumb_bytes))
            image = image.resize((200, 200), Image.Resampling.LANCZOS)
            self.tk_thumb = ImageTk.PhotoImage(image)
            self.thumb_label.config(image=self.tk_thumb)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load thumbnail: {e}")

        # Show EXIF
        self.exif_text.delete("1.0", tk.END)
        try:
            exif = json.loads(exif_json)
            if not exif:
                self.exif_text.insert(tk.END, "No EXIF data found.")
            else:
                for key, val in exif.items():
                    self.exif_text.insert(tk.END, f"{key}: {val}\n")
        except Exception as e:
            self.exif_text.insert(tk.END, f"Error reading EXIF: {e}")


if __name__ == "__main__":
    app = PhotoBrowser()
    app.mainloop()
