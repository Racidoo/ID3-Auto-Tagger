import tkinter
import customtkinter
import os
import requests
import threading
from Auto_Tagger import Tagger, Downloader, File, tag_mode_t
from PIL import Image
from mutagen.id3 import ID3
from mutagen.mp3 import MP3


class Settings:
    def __init__(self):
        self.blacklist_path = "blacklist.json"
        self.dir = os.getcwd()
        self.song_path = os.getcwd() + "/done/"
        self.cover_path = os.getcwd() + "/cover/"
        self.labels_text = [
            "Select",
            "Cover",
            "Title",
            "Artist",
            "Album",
            "Genre",
            "Length",
            "Progress",
        ]
        self.research_src = os.path.join(self.dir, "researched")


class App(customtkinter.CTk):
    def __init__(self):
        self.PADDING_FRAME_X = (10, 10)
        self.PADDING_FRAME_Y = (10, 10)
        self.settings = Settings()
        self.tagger = Tagger()
        self.downloader = Downloader()
        self.download_event = threading.Event()
        super().__init__()

        self.update_blacklist()

        # configure window
        self.title("Auto-Tagger")
        self.geometry(f"{1100}x{580}")

        # configure grid layout (2x2)
        self.grid_columnconfigure(1, weight=6)
        # self.grid_columnconfigure((1, 3), weight=1)
        self.grid_rowconfigure(0, weight=6)

        self.draw_sidebar()
        self.draw_footer()
        self.draw_scroll_frame()
        self.draw_research_frame()
        self.draw_settings_frame()
        self.select_frame_by_name("download_sp")

    def draw_sidebar(self):
        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(
            row=0,
            column=0,
            rowspan=2,
            # padx=self.PADDING_FRAME_X,
            # pady=self.PADDING_FRAME_Y,
            sticky="nsew",
        )
        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="CustomTkinter",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.download_sp_button = customtkinter.CTkButton(
            self.sidebar_frame,
            command=lambda: self.select_frame_by_name("download_sp"),
            text="Download songs",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            height=40,
            corner_radius=0,
            border_spacing=10,
        )
        self.download_sp_button.grid(row=1, column=0, sticky="ew")
        self.research_existing_button = customtkinter.CTkButton(
            self.sidebar_frame,
            command=lambda: self.select_frame_by_name("research_existing"),
            text="Research URI",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            height=40,
            corner_radius=0,
            border_spacing=10,
        )
        self.research_existing_button.grid(row=2, sticky="ew")
        self.settings_button = customtkinter.CTkButton(
            self.sidebar_frame,
            command=lambda: self.select_frame_by_name("settings"),
            text="Settings",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
            height=40,
            corner_radius=0,
            border_spacing=10,
        )
        self.settings_button.grid(row=5, column=0, sticky="ew")

    def draw_footer(self):
        # Footer
        self.footer_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.footer_frame.grid(
            row=1,
            column=1,
            padx=self.PADDING_FRAME_X,
            pady=self.PADDING_FRAME_Y,
            sticky="nsew",
        )
        # self.footer_frame.grid_configure(column=4, row=1)
        self.footer_frame.grid_columnconfigure(0, weight=2)
        self.entry = customtkinter.CTkEntry(
            self.footer_frame,
            placeholder_text="Enter Spotify-URI from track, album or playlist",
            # placeholder_text="2LM2u1sZuzLRsRSspo9hTe",
        )
        self.entry.grid(row=0, column=0, padx=(20, 0), pady=(20, 20), sticky="nsew")
        self.download_type_button = customtkinter.CTkSegmentedButton(self.footer_frame)
        self.download_type_button.grid(
            row=0, column=2, padx=(20, 0), pady=(20, 20), sticky="nsew"
        )
        self.download_type_button.configure(values=["album", "playlist", "track"])
        self.download_type_button.set("playlist")
        self.verify_only = customtkinter.BooleanVar()
        self.verify_switch = customtkinter.CTkSwitch(
            self.footer_frame,
            text="Verify Only",
            variable=self.verify_only,
            command=self.toggle_verify_only,
        )
        self.verify_switch.grid(
            row=0,
            column=3,
            padx=(20, 20),
            pady=(20, 20),
            sticky="nsew",
        )
        self.submit_button = customtkinter.CTkButton(
            master=self.footer_frame,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
            text="Submit",
            command=self.submit_button_event,
        )
        self.submit_button.grid(
            row=0, column=4, padx=(20, 20), pady=(20, 20), sticky="nsew"
        )

    def draw_scroll_frame(self):
        self.scroll_frame = customtkinter.CTkScrollableFrame(self, corner_radius=10)
        self.progressbars = []
        sorted_files = sorted(
            os.listdir(self.settings.song_path),
            key=lambda file: self.get_album_tag(self.settings.song_path + file),
        )
        # draw header
        for col, label_text in enumerate(self.settings.labels_text):
            customtkinter.CTkLabel(self.scroll_frame, text=label_text).grid(
                row=0, column=col, padx=5, pady=5, sticky="w"
            )
        # draw song details
        # for i, file in enumerate(sorted_files, start=1):
        #     song_tags = ID3("done/" + file)
        #     song = MP3("done/" + file)

        #     check_box = customtkinter.CTkCheckBox(self.scroll_frame, text="")
        #     check_box.grid(row=i, column=0, padx=5, pady=5)

        #     image = customtkinter.CTkImage(
        #         Image.open(BytesIO(song_tags.getall("APIC")[0].data)), size=(75, 75)
        #     )
        #     cover = customtkinter.CTkLabel(master=self.scroll_frame, image=image)
        # cover.grid(row=i, column=1, padx=5, pady=5, sticky="w")

        # title = customtkinter.CTkLabel(
        #     self.scroll_frame, text=song_tags["TIT2"].text[0], wraplength=150
        # )
        # title.grid(row=i, column=2, padx=5, pady=5, sticky="w")

        # artist = customtkinter.CTkLabel(
        #     self.scroll_frame, text=song_tags["TPE1"].text[0], wraplength=150
        # )
        # artist.grid(row=i, column=3, padx=5, pady=5, sticky="w")

        # album = customtkinter.CTkLabel(
        #     self.scroll_frame, text=song_tags["TALB"].text[0], wraplength=150
        # )
        # album.grid(row=i, column=4, padx=5, pady=5, sticky="w")

        # genre = customtkinter.CTkLabel(
        #     self.scroll_frame, text=song_tags["TCON"].text[0]
        # )
        # genre.grid(row=i, column=5, padx=5, pady=5)

        # length = customtkinter.CTkLabel(
        #     self.scroll_frame, text=Downloader.convert_to_mm_ss(song.info.length)
        # )
        # length.grid(row=i, column=6, padx=5, pady=5, sticky="w")

        # progress = customtkinter.CTkProgressBar(self.scroll_frame)
        # progress.grid(row=i, column=7, padx=5, pady=5, sticky="w")
        # self.progressbars.append(progress)
        # progress.configure(mode="Indeterminate")
        # progress.start()

        # self.downloader.event.set()
        # print("frontend event.set()")

    def draw_research_frame(self):
        self.research_existing_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.research_button = customtkinter.CTkButton(
            self.research_existing_frame,
            command=lambda: self.research_tracks(
                self.settings.research_src, self.settings.dir
            ),
            text="Research existing songs",
        )
        self.research_button.grid(sticky="nsew")

    def draw_settings_frame(self):
        self.keep_cover = customtkinter.BooleanVar()
        self.settings_frame = customtkinter.CTkFrame(self, corner_radius=0)
        label_blacklist = customtkinter.CTkLabel(
            self.settings_frame, text="Path to 'blacklist.json'"
        )
        label_blacklist.grid(row=1, padx=5, sticky="w")
        entry_blacklist = customtkinter.CTkEntry(
            self.settings_frame, placeholder_text=self.settings.blacklist_path
        )
        entry_blacklist.grid(row=2, padx=5, sticky="nsew")
        label_entry_dir = customtkinter.CTkLabel(
            self.settings_frame, text="Path to downloaded songs"
        )
        label_entry_dir.grid(row=3, padx=5, sticky="w")
        entry_entry_dir = customtkinter.CTkEntry(
            self.settings_frame, placeholder_text=self.settings.dir
        )
        entry_entry_dir.grid(row=4, padx=5, sticky="nsew")
        label_song_path = customtkinter.CTkLabel(
            self.settings_frame, text="Path to fully tagged songs"
        )
        label_song_path.grid(row=5, padx=5, sticky="w")
        entry_song_path = customtkinter.CTkEntry(
            self.settings_frame, placeholder_text=self.settings.song_path
        )
        entry_song_path.grid(row=6, padx=5, sticky="nsew")
        self.keep_cover_switch = customtkinter.CTkSwitch(
            self.settings_frame,
            text="Keep separate Album cover",
            state=tkinter.NORMAL,
            variable=self.keep_cover,
            command=self.toggle_keep_cover,
        )
        self.keep_cover_switch.grid(row=7, padx=5, sticky="nsew")
        label_cover_path = customtkinter.CTkLabel(
            self.settings_frame, text="Path to saved album covers"
        )
        label_cover_path.grid(row=8, padx=5, sticky="w")
        self.entry_cover_path = customtkinter.CTkEntry(
            self.settings_frame, placeholder_text=self.settings.cover_path
        )
        self.entry_cover_path.grid(row=9, padx=5, sticky="nsew")

    def select_frame_by_name(self, name):
        # Set button colors for selected button
        buttons = [self.download_sp_button, self.settings_button]
        button_names = ["download_sp", "research_existing", "settings"]
        for button, button_name in zip(buttons, button_names):
            fg_color = ("gray75", "gray25") if name == button_name else "transparent"
            button.configure(fg_color=fg_color)

        # Show selected frame
        frames = [self.scroll_frame, self.research_existing_frame, self.settings_frame]
        for frame, frame_name in zip(frames, button_names):
            if name == frame_name:
                frame.grid(
                    row=0,
                    column=1,
                    padx=self.PADDING_FRAME_X,
                    pady=self.PADDING_FRAME_Y,
                    sticky="nsew",
                )
            else:
                frame.grid_forget()

    def draw_song_table(self, titles):
        for i, text in enumerate(titles):
            title = customtkinter.CTkLabel(self.scroll_frame, text=text, wraplength=150)
            title.grid(row=i, column=2, padx=5, pady=5, sticky="w")
            progress = customtkinter.CTkProgressBar(self.scroll_frame)
            progress.grid(row=i, column=7, padx=5, pady=5, sticky="w")
            self.progressbars.append(progress)
            progress.configure(mode="Indeterminate")
            progress.start()

    def submit_button_event(self):
        self.update_blacklist()
        if not self.verify_switch.get():
            mode = tag_mode_t[self.download_type_button.get()]
            # titles = list(self.tagger.get_tags(self.entry.get(), mode).keys())
            # self.draw_song_table(titles)
            i = 1
            for key, value in self.tagger.get_tags(self.entry.get(), mode).items():
                # for key, value in self.tagger.get_tags(
                #     "2LM2u1sZuzLRsRSspo9hTe", mode).items():
                # print(key)
                threading.Thread(
                    target=self.downloader.downloader_thread,
                    args=[self.download_event, value, self.blacklist],
                ).start()
                threading.Thread(target=self.refresher_thread, args=[i, value]).start()
                i += 1

            # print("download complete")
            # time.sleep()

        self.tagger.verify_tags(blacklist=self.blacklist)

    def toggle_verify_only(self):
        verify_only = self.verify_switch.get()
        self.entry.configure(state="disabled" if verify_only else "normal")
        self.download_type_button.configure(
            state="disabled" if verify_only else "normal"
        )

    def toggle_keep_cover(self):
        keep_cover = self.keep_cover_switch.get()
        self.entry_cover_path(state="normal" if keep_cover else "disabled")

    def update_blacklist(self):
        self.blacklist = File.get_json(self.settings.blacklist_path)

    @staticmethod
    def get_album_tag(file_path):
        song_tags = ID3(file_path)
        return song_tags["TALB"].text[0] if "TALB" in song_tags else ""

    def create_label(self, text, row, column):
        return customtkinter.CTkLabel(
            self.scroll_frame, text=text, wraplength=150
        ).grid(row=row, column=column, padx=5, pady=5, sticky="w")

    def refresher_thread(self, i, song_tags):
        print("Waiting for event")
        customtkinter.CTkCheckBox(self.scroll_frame, text="").grid(
            row=i, column=0, padx=5, pady=5
        )

        image = customtkinter.CTkImage(
            Image.open(requests.get(song_tags["cover"], stream=True).raw), size=(75, 75)
        )
        customtkinter.CTkLabel(master=self.scroll_frame, image=image).grid(
            row=i, column=1, padx=5, pady=5, sticky="w"
        )

        labels = ["title", "artist", "album", "genre"]
        grid_positions = [2, 3, 4, 5]

        for label, pos in zip(labels, grid_positions):
            self.create_label(song_tags[label], i, pos)
        self.create_label(
            Downloader.convert_to_mm_ss(song_tags["duration_ms"] / 1000), i, 6
        )

        progress = customtkinter.CTkProgressBar(self.scroll_frame)
        progress.grid(row=i, column=7, padx=5, pady=5, sticky="w")
        progress.set(0)
        # progress.configure(mode="Indeterminate")
        # progress.start()
        progress["maximum"] = 5
        for j in range(5):
            if self.download_event.wait(10):
                self.download_event.clear()
                print("downloaded", i)
                # progress.configure(mode="determinate")
                progress.set(j)
                # progress.stop()
            else:
                print("Timed out", i)
                progress.configure(progress_color="red")
                break
        progress.stop()

    def research_tracks(self, src, dest):
        if not os.path.exists(src):
            os.mkdir(src)
        for file in os.listdir(src):
            if file.lower().endswith(".mp3"):
                fullpath = os.path.join(src, file)
                song = ID3(fullpath)
                track = MP3(fullpath)
                res = self.tagger.research_uri(
                    track=song["TIT2"].text[0],
                    artist=song["TPE1"].text[0],
                    length=track.info.length,
                )
                if res != False:
                    os.rename(fullpath, os.path.join(dest, res + ".mp3"))


if __name__ == "__main__":
    app = App()
    app.mainloop()
