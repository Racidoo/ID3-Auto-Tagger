import tkinter
import customtkinter
import os
import requests
import threading
from Auto_Tagger import Tagger, Downloader, File, tag_mode_t
from io import BytesIO
from PIL import Image
from mutagen.id3 import ID3
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3


class Settings:
    def __init__(self):
        self.blacklist_path = "blacklist.json"
        self.dir = os.getcwd()
        self.song_path = os.path.join(os.getcwd(), "done")
        self.cover_path = os.path.join(os.getcwd(), "cover")
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
        self.timeout = 10


class SongLabel(customtkinter.CTkFrame):
    def __init__(
        self,
        master: any,
        func=None,
        row: int = 1,
        tags: dict = {
            # "cover": "https://community.mp3tag.de/uploads/default/original/2X/a/acf3edeb055e7b77114f9e393d1edeeda37e50c9.png",
            "cover": "https://i.scdn.co/image/ab67616d00001e0254d3de8fa0c42b102640dbbc",
            "title": "example title",
            "artist": "example artist",
            "album": "example album",
            "genre": "example genre",
            "duration_ms": 99999,
        },
        check_box=False,
        # progress_bar = False,
        **kwargs,
    ):
        pos = 0
        image: customtkinter.CTkImage
        if check_box:
            self.checkbox_toggle = customtkinter.BooleanVar()
            # Needs to be outside class as value is used to identify radio-button
            # self.checkbox_toggle = customtkinter.IntVar()

            def on_checkbox_toggle(func):
                if self.checkbox_toggle.get():
                    # Checkbox is enabled (checked)
                    func()

            customtkinter.CTkCheckBox(
                master=master,
                variable=self.checkbox_toggle,
                text="",
                command=lambda func=func: on_checkbox_toggle(func),
                # command=func if self.checkbox_toggle.get() else None,
            ).grid(row=row, column=pos, padx=5, pady=5)
            pos += 1

        if "image" in kwargs:
            image = customtkinter.CTkImage(
                Image.open(BytesIO(kwargs.pop("image"))), size=(75, 75)
            )
        else:
            image = customtkinter.CTkImage(
                Image.open(requests.get(tags["cover"], stream=True).raw), size=(75, 75)
            )

        customtkinter.CTkLabel(master=master, image=image, text="").grid(
            row=row, column=pos, padx=5, pady=5, sticky="w"
        )
        pos += 1
        labels = ["title", "artist", "album", "genre"]

        for label in labels:
            self.__create_label(master=master, text=tags[label], row=row, column=pos)
            pos += 1
        self.__create_label(
            master=master,
            text=Downloader.convert_to_mm_ss(tags["duration_ms"] / 1000),
            row=row,
            column=6,
        )
        super().__init__(master=master, **kwargs)

    def __create_label(
        self,
        master,
        text,
        row,
        column,
    ):
        return customtkinter.CTkLabel(master=master, text=text, wraplength=150).grid(
            row=row, column=column, padx=5, pady=5, sticky="w"
        )


class ScrollFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master: any, labels):
        super().__init__(master, corner_radius=10, fg_color="transparent")

        # draw header
        for col, label_text in enumerate(labels):
            customtkinter.CTkLabel(self, text=label_text).grid(
                row=0, column=col, padx=5, pady=5, sticky="w"
            )

    @staticmethod
    def get_album_tag(file_path):
        song_tags = ID3(file_path)
        return song_tags["TALB"].text[0] if "TALB" in song_tags else ""


class App(customtkinter.CTk):
    def __init__(self):
        self.PADDING_FRAME_X = (10, 10)
        self.PADDING_FRAME_Y = (10, 10)
        self.settings = Settings()
        self.tagger = Tagger()
        self.downloader = Downloader()
        self.download_event = threading.Event()
        # Dictionary to store the buttons as member variables
        self.__buttons = {}
        self.edit_downloaded_entries: dict = {}
        self.album_cover: customtkinter.CTkButton
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
        self.draw_download_frame()
        self.draw_view_downloaded_frame()
        self.draw_research_frame()
        self.draw_settings_frame()
        self.select_frame_by_name("download_sp")

    def draw_sidebar(self):
        # Create a list of button names and their corresponding texts
        buttons_info = [
            ("download_sp", "Download songs"),
            ("view_downloaded", "View downloaded songs"),
            ("research_existing", "Research URI"),
            ("settings", "Settings"),
        ]

        # Create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")

        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="CustomTkinter",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        for idx, (name, text) in enumerate(buttons_info, start=1):
            button = customtkinter.CTkButton(
                self.sidebar_frame,
                command=lambda n=name: self.select_frame_by_name(n),
                text=text,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                anchor="w",
                height=40,
                corner_radius=0,
                border_spacing=10,
            )
            button.grid(row=idx, column=0, sticky="ew")

            # Save the button as a member variable
            self.__buttons[name] = button

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
        self.footer_frame.grid_columnconfigure(0, weight=2)
        self.download_progress = customtkinter.CTkProgressBar(
            self.footer_frame, mode="determinate"
        )
        self.download_progress.grid(
            row=0, column=0, padx=(20, 0), pady=(0, 0), sticky="ew"
        )
        self.download_progress.set(0)
        self.entry = customtkinter.CTkEntry(
            self.footer_frame,
            placeholder_text="Enter URL from Spotify or YouTube",
        )
        self.entry.grid(row=1, column=0, padx=(20, 0), pady=(0, 0), sticky="ew")

        self.verify_only = customtkinter.BooleanVar()
        self.verify_switch = customtkinter.CTkSwitch(
            self.footer_frame,
            text="Verify Only",
            variable=self.verify_only,
            command=self.__toggle_verify_only,
        )
        self.verify_switch.grid(
            row=0,
            rowspan=2,
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
            row=0, rowspan=2, column=4, padx=(20, 20), pady=(20, 20), sticky="nsew"
        )

    def draw_download_frame(self):
        self.download_frame = ScrollFrame(self, self.settings.labels_text[1:])

    def draw_view_downloaded_frame(self):
        self.view_downloaded_frame = customtkinter.CTkFrame(self)
        self.view_downloaded_frame.columnconfigure(0, weight=10)
        self.view_downloaded_frame.columnconfigure(1, weight=1)
        self.view_downloaded_frame.rowconfigure(0, weight=1)

        self.edit_downloaded_frame = customtkinter.CTkFrame(self.view_downloaded_frame)
        self.edit_downloaded_frame.grid(row=0, column=1, sticky="nsew")
        self.edit_downloaded_cover_frame = customtkinter.CTkFrame(
            self.edit_downloaded_frame
        )
        self.edit_downloaded_cover_frame.grid(row=0, column=0, sticky="s")
        self.edit_downloaded_tags_frame = customtkinter.CTkFrame(
            self.edit_downloaded_frame
        )
        self.edit_downloaded_tags_frame.grid(row=1, column=0, sticky="n")

        self.edit_downloaded_frame.columnconfigure(0, weight=1)
        self.edit_downloaded_frame.rowconfigure(0, weight=2)
        self.edit_downloaded_frame.rowconfigure(1, weight=1)
        url = "https://community.mp3tag.de/uploads/default/original/2X/a/acf3edeb055e7b77114f9e393d1edeeda37e50c9.png"
        image = customtkinter.CTkImage(
            Image.open(requests.get(url=url, stream=True).raw), size=(300, 300)
        )
        self.album_cover = customtkinter.CTkButton(
            master=self.edit_downloaded_cover_frame,
            image=image,
            text="",
            command=lambda: print(
                "Changing the album cover has not been implemented yet!"
            ),
        )
        self.album_cover.grid(
            row=0, column=0, columnspan=2, padx=20, pady=20, sticky="ew"
        )
        labels = [
            "title",
            "artist",
            "album",
            "albumartist",
            "date",
            "genre",
            "copyright",
            "organization",
            "tracknumber",
            "discnumber",
        ]

        def on_entry_change(self, event):
            input_text = event.widget.get()
            print("Entry content changed:", event.widget.get())
            event.widget.delete(0, "end")
            self.configure(placeholder_text=input_text)

        for pos, label in enumerate(labels):
            customtkinter.CTkLabel(
                master=self.edit_downloaded_tags_frame, text=label, wraplength=150
            ).grid(row=pos, column=0, padx=20, pady=5, sticky="ew")
            e = customtkinter.CTkEntry(
                master=self.edit_downloaded_tags_frame,
                placeholder_text=label,
                width=250,
            )
            e.bind("<Return>", lambda event, e=e: on_entry_change(e, event))
            e.grid(row=pos, column=1)
            self.edit_downloaded_entries[label] = e

    def refresh_scroll_frame(self):
        self.view_downloaded_scroll_frame = ScrollFrame(
            self.view_downloaded_frame, self.settings.labels_text[:-1]
        )
        self.view_downloaded_scroll_frame.grid(row=0, column=0, sticky="nsew")
        # sorted_files = sorted(
        #     os.listdir(File.check_dir(self.settings.dir)),
        #     key=lambda file: ScrollFrame.get_album_tag(os.path.join(self.settings.dir, file)),
        # )
        sorted_files = []
        for file in os.listdir(File.check_dir(self.settings.song_path)):
            if file.lower().endswith(".mp3"):
                sorted_files.append(file)

        # draw song details
        for i, file in enumerate(sorted_files, start=1):
            song_tags = ID3("done/" + file)
            song = MP3("done/" + file)
            tags = {
                "title": song_tags["TIT2"].text[0],
                "artist": song_tags["TPE1"].text[0],
                "album": song_tags["TALB"].text[0],
                "genre": song_tags["TCON"].text[0],
                "albumartist": song_tags["TPE2"].text[0],
                "date": song_tags["TDRC"].text[0],
                "copyright": song_tags["TCOP"].text[0],
                "organization": song_tags["TPUB"].text[0],
                "tracknumber": song_tags["TRCK"].text[0],
                "discnumber": song_tags["TPOS"].text[0],
                "duration_ms": song.info.length * 1000,
                "cover": song_tags.getall("APIC")[0].data,
            }
            SongLabel(
                master=self.view_downloaded_scroll_frame,
                func=lambda tags=tags: self.select_song(tags),
                row=i,
                tags=tags,
                image=song_tags.getall("APIC")[0].data,
                check_box=True,
            )

    def draw_research_frame(self):
        self.research_existing_frame = customtkinter.CTkScrollableFrame(
            self, corner_radius=10
        )
        self.research_button = customtkinter.CTkButton(
            self.research_existing_frame,
            command=lambda: self.research_tracks(
                self.settings.research_src, self.settings.dir
            ),
            text="Research existing songs",
        )
        self.research_button.grid(sticky="nsew")

    def draw_settings_frame(self):
        self.__keep_cover = customtkinter.BooleanVar()
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
            variable=self.__keep_cover,
            command=self.__toggle_keep_cover,
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
        for button_name, button in self.__buttons.items():
            fg_color = ("gray75", "gray25") if name == button_name else "transparent"
            button.configure(fg_color=fg_color)

        # Show selected frame
        frames = [
            self.download_frame,
            self.view_downloaded_frame,
            self.research_existing_frame,
            self.settings_frame,
        ]
        for frame, frame_name in zip(frames, self.__buttons.keys()):
            if name == frame_name:
                frame.grid(
                    row=0,
                    column=1,
                    padx=self.PADDING_FRAME_X,
                    pady=self.PADDING_FRAME_Y,
                    sticky="nsew",
                )
                if name == "view_downloaded":
                    self.refresh_scroll_frame()
            else:
                frame.grid_forget()

    def submit_button_event(self):
        self.download_progress.set(0)
        self.update_blacklist()
        if not self.verify_switch.get():
            link_type, match_type, id = Downloader.extract_from_url(self.entry.get())
            if link_type == "YouTube":
                # Do something, will be implemented later
                print("")
            elif link_type == "Spotify":
                threads = []
                j = 1
                for key, value in self.tagger.get_tags(
                    uri=id, mode=tag_mode_t[match_type]
                ).items():
                    if key in self.blacklist["blacklist"]:
                        continue
                    threads.append(
                        threading.Thread(
                            target=self.downloader.downloader_thread,
                            args=[self.download_event, value, self.blacklist],
                        )
                    )
                    threads.append(
                        threading.Thread(target=self.refresher_thread, args=[j, value]),
                    )
                    j += 1
                # Start all threads
                for thread in threads:
                    thread.start()

                # Overwatch for download and refresher-threads to execute verify_tags() AFTER everything was downloaded
                def watch_threads(threads):
                    step = int(1000 / (len(threads) + 1))
                    progress = 0
                    for thread in threads:
                        progress += step
                        thread.join(timeout=None)
                        self.download_progress.set(progress * 0.001)
                    progress += step
                    self.download_progress.set(progress)
                    self.tagger.verify_tags(blacklist=self.blacklist)

                threading.Thread(target=watch_threads, args=[threads]).start()

    def __toggle_verify_only(self):
        verify_only = self.verify_switch.get()
        self.entry.configure(state="disabled" if verify_only else "normal")

    def __toggle_keep_cover(self):
        keep_cover = self.keep_cover_switch.get()
        self.entry_cover_path(state="normal" if keep_cover else "disabled")

    def update_blacklist(self):
        self.blacklist = File.get_json(self.settings.blacklist_path)

    def refresher_thread(self, i, song_tags):
        print("Waiting for event")
        SongLabel(
            self.download_frame,
            row=i,
            tags=song_tags,
        )
        progress = customtkinter.CTkProgressBar(self.download_frame)
        progress.grid(row=i, column=7, padx=5, pady=5, sticky="w")
        progress.set(0)
        for j in range(2, 12, 2):
            if self.download_event.wait(self.settings.timeout):
                self.download_event.clear()
                print("downloaded", i, ": ", j * 0.1)
                progress.set((j) * 0.1)
            else:
                print("Timed out", i)
                progress.configure(progress_color="red")
                break

    def research_tracks(self, src, dest):
        for file in os.listdir(File.check_dir(src)):
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

    def select_song(self, tags: dict):
        if "cover" in tags:
            image = customtkinter.CTkImage(
                Image.open(BytesIO(tags["cover"])), size=(300, 300)
            )
            self.album_cover.configure(image=image)
        for label, entry in self.edit_downloaded_entries.items():
            if label in tags:
                entry.configure(placeholder_text=tags[label])
            else:
                print(f"Key '{label}' not found in self.edit_dowloaded_entries")


if __name__ == "__main__":
    app = App()
    app.mainloop()
