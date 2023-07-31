import tkinter
import customtkinter
import os
from Auto_Tagger import Tagger, Downloader, File, tag_mode_t
import threading
from PIL import Image
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from io import BytesIO


class Settings:
    def __init__(self):
        self.blacklist_path = "blacklist.json"
        self.dir = os.getcwd()


class App(customtkinter.CTk):
    def __init__(self):
        self.settings = Settings()
        self.tagger = Tagger()
        self.downloader = Downloader()
        super().__init__()

        self.update_blacklist()

        # configure window
        self.title("Auto-Tagger")
        self.geometry(f"{1100}x{580}")

        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((1, 3), weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        # self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="CustomTkinter",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # create navigation frame
        self.scroll_frame = customtkinter.CTkScrollableFrame(self, corner_radius=10)
        self.scroll_frame.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(20, 0),
            pady=(20, 0),
            columnspan=4,
            rowspan=3,
        )
        labels_text = [
            "Select",
            "Cover",
            "Title",
            "Artist",
            "Album",
            "Genre",
            "Length",
            "Progress",
        ]

        for col, label_text in enumerate(labels_text):
            customtkinter.CTkLabel(self.scroll_frame, text=label_text).grid(
                row=0, column=col, padx=5, pady=5, sticky="w"
            )
        self.draw_scroll_frame()

        self.entry = customtkinter.CTkEntry(
            self, placeholder_text="Enter Spotify-URI from track, album or playlist"
        )
        self.entry.grid(row=3, column=1, padx=(20, 0), pady=(20, 20), sticky="nsew")
        self.download_type_button = customtkinter.CTkSegmentedButton(self)
        self.download_type_button.grid(
            row=3, column=2, padx=(20, 0), pady=(20, 20), sticky="nsew"
        )
        self.download_type_button.configure(values=["album", "playlist", "track"])
        self.download_type_button.set("track")
        self.verify_only = customtkinter.BooleanVar()
        self.verify_switch = customtkinter.CTkSwitch(
            self,
            text="Verify Only",
            variable=self.verify_only,
            command=self.toggle_verify_only,
        )
        self.verify_switch.grid(
            row=3,
            column=3,
            padx=(20, 20),
            pady=(20, 20),
            sticky="nsew",
        )
        self.submit_button = customtkinter.CTkButton(
            master=self,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
            text="Submit",
            command=self.submit_button_event,
        )
        self.submit_button.grid(
            row=3, column=4, padx=(20, 20), pady=(20, 20), sticky="nsew"
        )

        self.settings_button = customtkinter.CTkButton(
            self.sidebar_frame,
            command=self.settings_button_event,
            text="Settings",
        )
        self.settings_button.grid(row=5, column=0, padx=20, pady=10)
        self.settings_frame = customtkinter.CTkFrame(
            self, corner_radius=0, fg_color="transparent"
        )
        self.settings_frame.grid_columnconfigure(0, weight=1)

    def settings_button_event(self):
        self.select_frame_by_name("settings")

    def submit_button_event(self):
        self.update_blacklist()
        if not self.verify_switch.get():
            mode = tag_mode_t[self.download_type_button.get()]
            download_thread = threading.Thread(
                target=self.downloader.download,
                args=(self.entry.get(), mode, self.blacklist),
            )
            download_thread.start()
        self.tagger.verify_tags(path=self.settings.dir, blacklist=self.blacklist)

    def toggle_verify_only(self):
        verify_only = self.verify_switch.get()
        self.entry.configure(state="disabled" if verify_only else "normal")
        self.download_type_button.configure(
            state="disabled" if verify_only else "normal"
        )

    def update_blacklist(self):
        self.blacklist = File.get_json(self.settings.blacklist_path)

    @staticmethod
    def get_album_tag(file_path):
        song_tags = ID3(file_path)
        return song_tags["TALB"].text[0] if "TALB" in song_tags else ""

    def draw_scroll_frame(self):
        self.progressbars = []
        sorted_files = sorted(
            os.listdir("done/"), key=lambda file: self.get_album_tag("done/" + file)
        )

        for i, file in enumerate(sorted_files, start=1):
            song_tags = ID3("done/" + file)
            song = MP3("done/" + file)

            check_box = customtkinter.CTkCheckBox(self.scroll_frame, text="")
            check_box.grid(row=i, column=0, padx=5, pady=5)

            image = customtkinter.CTkImage(
                Image.open(BytesIO(song_tags.getall("APIC")[0].data)), size=(75, 75)
            )
            cover = customtkinter.CTkLabel(master=self.scroll_frame, image=image)
            cover.grid(row=i, column=1, padx=5, pady=5, sticky="w")

            title = customtkinter.CTkLabel(
                self.scroll_frame, text=song_tags["TIT2"].text[0], wraplength=150
            )
            title.grid(row=i, column=2, padx=5, pady=5, sticky="w")

            artist = customtkinter.CTkLabel(
                self.scroll_frame, text=song_tags["TPE1"].text[0], wraplength=150
            )
            artist.grid(row=i, column=3, padx=5, pady=5, sticky="w")

            album = customtkinter.CTkLabel(
                self.scroll_frame, text=song_tags["TALB"].text[0], wraplength=150
            )
            album.grid(row=i, column=4, padx=5, pady=5, sticky="w")

            genre = customtkinter.CTkLabel(
                self.scroll_frame, text=song_tags["TCON"].text[0]
            )
            genre.grid(row=i, column=5, padx=5, pady=5)

            length = customtkinter.CTkLabel(
                self.scroll_frame, text=Downloader.convert_to_mm_ss(song.info.length)
            )
            length.grid(row=i, column=6, padx=5, pady=5, sticky="w")

            progress = customtkinter.CTkProgressBar(self.scroll_frame)
            progress.grid(row=i, column=7, padx=5, pady=5, sticky="w")
            self.progressbars.append(progress)
            progress.configure(mode="Indeterminate")
            progress.start()

            self.downloader.event.set()


if __name__ == "__main__":
    app = App()
    app.mainloop()
