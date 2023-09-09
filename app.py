import tkinter
from typing import Optional, Tuple, Union
import customtkinter
import os
import requests
import threading
from Auto_Tagger import Tagger, Downloader, File, tag_mode_t
from io import BytesIO
from PIL import Image
from mutagen.id3 import ID3
from mutagen.easyid3 import EasyID3
from pprint import pprint


class Settings:
    def __init__(self):
        self.blacklist_path = "blacklist.json"
        self.dir = os.getcwd()
        self.song_path = os.path.join(os.getcwd(), "done")
        self.cover_path = os.path.join(os.getcwd(), "cover")
        self.labels_text = [
            "Cover",
            "Title",
            "Artist",
            "Album",
            "Genre",
            "Length",
            "Progress",
        ]
        self.research_src = os.path.join(self.dir, "researched")
        self.research_failed = os.path.join(self.dir, "no-data")
        self.timeout = 60
        self.default_cover = customtkinter.CTkImage(
            Image.open(
                requests.get(
                    url="https://community.mp3tag.de/uploads/default/original/2X/a/acf3edeb055e7b77114f9e393d1edeeda37e50c9.png",
                    stream=True,
                ).raw
            ),
            size=(300, 300),
        )


class ResearchDialog(customtkinter.CTkToplevel):
    def __init__(
        self,
        fg_color: Optional[Union[str, Tuple[str, str]]] = None,
        text_color: Optional[Union[str, Tuple[str, str]]] = None,
        button_fg_color: Optional[Union[str, Tuple[str, str]]] = None,
        button_hover_color: Optional[Union[str, Tuple[str, str]]] = None,
        button_text_color: Optional[Union[str, Tuple[str, str]]] = None,
        entry_fg_color: Optional[Union[str, Tuple[str, str]]] = None,
        entry_border_color: Optional[Union[str, Tuple[str, str]]] = None,
        entry_text_color: Optional[Union[str, Tuple[str, str]]] = None,
        tags_list=None,
        labels=None,
        file=None,
        source_path=None,
        dest_path=None,
    ):
        super().__init__(fg_color=fg_color)

        self._fg_color = (
            customtkinter.ThemeManager.theme["CTkToplevel"]["fg_color"]
            if fg_color is None
            else self._check_color_type(fg_color)
        )
        self._text_color = (
            customtkinter.ThemeManager.theme["CTkLabel"]["text_color"]
            if text_color is None
            else self._check_color_type(button_hover_color)
        )
        # self._button_fg_color = customtkinter.ThemeManager.theme["CTkButton"]["fg_color"] if button_fg_color is None else self._check_color_type(button_fg_color)
        # self._button_hover_color = customtkinter.ThemeManager.theme["CTkButton"]["hover_color"] if button_hover_color is None else self._check_color_type(button_hover_color)
        # self._button_text_color = customtkinter.ThemeManager.theme["CTkButton"]["text_color"] if button_text_color is None else self._check_color_type(button_text_color)
        # self._entry_fg_color = customtkinter.ThemeManager.theme["CTkEntry"]["fg_color"] if entry_fg_color is None else self._check_color_type(entry_fg_color)
        # self._entry_border_color = customtkinter.ThemeManager.theme["CTkEntry"]["border_color"] if entry_border_color is None else self._check_color_type(entry_border_color)
        # self._entry_text_color = customtkinter.ThemeManager.theme["CTkEntry"]["text_color"] if entry_text_color is None else self._check_color_type(entry_text_color)

        # self._user_input: Union[str, None] = None
        # self._running: bool = False
        self.file = file
        self.source_path = source_path
        self.dest_path = dest_path
        self.song_labels = []
        self.lift()  # lift window on top
        self.attributes("-topmost", True)  # stay on top
        self.protocol("WM_DELETE_WINDOW", self.__on_closing)
        self.after(
            1, self._create_widgets(tags_list, labels)
        )  # create widgets with slight delay, to avoid white flickering of background
        self.resizable(False, False)
        self.grab_set()  # make other windows not clickable

    def _create_widgets(self, tags_list, labels):
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(1, weight=1)
        App.draw_header(master=self, labels=labels).grid(row=0, column=0, columnspan=6)

        for i, tags in enumerate(tags_list, start=1):
            button_click = lambda u=tags["id"]: self.handle_dialog(u, None)

            image = customtkinter.CTkImage(
                Image.open(requests.get(tags["cover"], stream=True).raw),
                size=(50, 50),
            )
            image_label = customtkinter.CTkLabel(master=self, image=image, text="")
            image_label.grid(row=i, column=0, padx=5, pady=5, sticky="w")
            image_label.bind("<Button-1>", button_click)
            tags["length"] = Downloader.convert_to_mm_ss(tags["duration_ms"] / 1000)
            labels = ["title", "artist", "album", "genre", "length"]
            for pos, label in enumerate(labels, start=1):
                l = customtkinter.CTkLabel(
                    master=self,
                    text=tags[label],
                    width=150,
                    wraplength=150,
                )
                l.grid(row=i, column=pos, padx=5, pady=5)
                master = self
                l.bind(
                    "<Button-1>",
                    lambda event, u=tags["id"]: master.handle_dialog(event, u),
                )

    def __on_closing(self):
        self.grab_release()
        self.destroy()

    def handle_dialog(self, event, uri):
        research_data: dict = File.get_json("research_data.json")
        os.rename(
            os.path.join(self.source_path, self.file),
            os.path.join(self.dest_path, (uri + ".mp3")),
        )
        research_data.pop(self.file)
        File.append_json(research_data, "research_data.json")
        # print("clicked label")
        self.__on_closing()


# Needs rework to make it a proper widget. Currently a workaround to make the selection work
class SongLabel(customtkinter.CTkFrame):
    def __init__(
        self,
        master: any,
        func=None,
        row: int = 1,
        tags: dict = {
            "cover": "https://community.mp3tag.de/uploads/default/original/2X/a/acf3edeb055e7b77114f9e393d1edeeda37e50c9.png",
            "title": "example title",
            "artist": "example artist",
            "album": "example album",
            "genre": "example genre",
            "duration_ms": 99999,
        },
        active_songs: str = [],
        song_path: str = "",
        cover_size=(50, 50),
        **kwargs,
    ):
        customtkinter.CTkFrame.__init__(self, master)

        self.is_active = False
        image: customtkinter.CTkImage

        if isinstance(tags["cover"], str):
            image = customtkinter.CTkImage(
                Image.open(requests.get(tags["cover"], stream=True).raw),
                size=cover_size,
            )
        else:
            image = customtkinter.CTkImage(
                Image.open(BytesIO(tags["cover"])), size=cover_size
            )

        self.song: str = song_path

        def __clicked_label(event, multiple=False):
            # if not multiple:
            #     active_songs.clear()
            self.is_active = not self.is_active
            if self.is_active:
                active_songs.append(self.song)
                # pprint(active_songs)
            else:
                active_songs.remove(self.song)
            self.configure(
                fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"]
                if self.is_active
                else customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"]
            )
            func()

        self.image_label = customtkinter.CTkLabel(master=self, image=image, text="")
        self.image_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.image_label.bind("<Button-1>", __clicked_label)

        if "length" not in tags:
            if "duration_ms" in tags:
                tags["length"] = Downloader.convert_to_mm_ss(tags["duration_ms"] / 1000)
            else:
                tags["length"] = "--:--"

        labels = ["title", "artist", "album", "genre", "length"]
        for pos, label in enumerate(labels, start=1):
            l = customtkinter.CTkLabel(
                master=self,
                text=tags[label],
                width=100,
                wraplength=100,
            )
            l.grid(row=0, column=pos, padx=5, pady=5)
            l.bind("<Button-1>", __clicked_label)
        self.bind("<Button-1>", __clicked_label)
        # self.bind("<Shift-Button-1>", lambda event: print("Shift-Click"))


class App(customtkinter.CTk):
    def __init__(self):
        self.PADDING_FRAME_X = (10, 10)
        self.PADDING_FRAME_Y = (0, 0)
        self.settings = Settings()
        self.tagger = Tagger()
        self.downloader = Downloader()
        self.download_event = threading.Event()
        self.selected_songs = []
        # Dictionary to store the buttons as member variables
        self.__buttons = {}
        self.selected_songs = []
        self.edit_downloaded_entries: dict = {}
        self.album_cover: customtkinter.CTkButton
        self.frames = {
            "title": "TIT2",
            "artist": "TPE1",
            "album": "TALB",
            "genre": "TCON",
            "albumartist": "TPE2",
            "date": "TDRC",
            "copyright": "TCOP",
            "organization": "TPUB",
            "tracknumber": "TRCK",
            "discnumber": "TPOS",
        }
        self.sort_frame = self.frames["title"]

        super().__init__()

        self.update_blacklist()

        # configure window
        self.title("Auto-Tagger")
        # self.geometry(f"{1300}x{580}")
        self.iconbitmap("music.ico")
        # configure grid layout (2x2)
        self.grid_columnconfigure(1, weight=10)
        # self.grid_columnconfigure((1, 3), weight=1)
        self.grid_rowconfigure(0, weight=6)

        self.draw_sidebar()
        self.draw_footer()
        self.draw_download_frame()
        self.draw_view_downloaded_frame()
        self.draw_research_frame()
        self.draw_settings_frame()
        self.select_frame_by_name("download")

    def draw_sidebar(self):
        # Create a list of button names and their corresponding texts
        buttons_info = [
            ("download", "Download songs"),
            ("view_downloaded", "View downloaded songs"),
            # ("research_existing", "Research URI"),
            ("settings", "Settings"),
        ]

        def on_click(event):
            for name, text in buttons_info:
                button_text = text if self.__buttons[name].cget("text") == "" else ""
                self.__buttons[name].configure(text=button_text)

        # Create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.bind("<Button-1>", on_click)

        for idx, (name, text) in enumerate(buttons_info, start=1):
            button = customtkinter.CTkButton(
                self.sidebar_frame,
                command=lambda n=name: self.select_frame_by_name(n),
                text="",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                anchor="w",
                height=40,
                width=40,
                corner_radius=0,
                border_spacing=10,
                image=customtkinter.CTkImage(
                    light_image=Image.open(name + "_light.png"),
                    dark_image=Image.open(name + "_dark.png"),
                ),
            )
            # button.grid(row=idx, column=0, sticky="ew")
            button.pack()
            # Save the button as a member variable
            self.__buttons[name] = button

    def draw_footer(self):
        # Footer
        self.footer_frame = customtkinter.CTkFrame(self)
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
        self.entry.bind("<Return>", lambda event: self.submit_button_event())
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
        self.download_frame = customtkinter.CTkFrame(self)
        self.download_frame.columnconfigure(0, weight=1)
        self.download_frame.rowconfigure(0, weight=0)
        self.download_frame.rowconfigure(1, weight=1)
        self.draw_header(self.download_frame, self.settings.labels_text).grid(
            row=0, column=0, sticky="w"
        )
        self.download_scroll_frame = customtkinter.CTkScrollableFrame(
            self.download_frame
        )
        self.download_scroll_frame.grid(row=1, column=0, sticky="nsew")

    def draw_view_downloaded_frame(self):
        self.view_downloaded_frame = customtkinter.CTkFrame(self)
        self.view_downloaded_frame.bind(
            "<Button-1>", lambda event: print("view_downloaded_frame")
        )
        self.draw_header(
            self.view_downloaded_frame, self.settings.labels_text[:-1]
        ).grid(row=0, column=0, sticky="sw")

        self.view_downloaded_frame.columnconfigure(0, weight=3)
        self.view_downloaded_frame.columnconfigure(1, weight=0)
        self.view_downloaded_frame.rowconfigure(0, weight=0)
        self.view_downloaded_frame.rowconfigure(1, weight=1)

        self.edit_downloaded_frame = customtkinter.CTkFrame(self.view_downloaded_frame)
        self.edit_downloaded_frame.bind(
            "<Button-1>", lambda event: print("edit_downloaded_frame")
        )

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

        self.album_cover = customtkinter.CTkButton(
            master=self.edit_downloaded_cover_frame,
            image=self.settings.default_cover,
            text="",
            command=lambda: print(
                "Changing the album cover has not been implemented yet!"
            ),
        )
        self.album_cover.pack(fill="x")

        def on_entry_change(widget, label):
            input_text = widget.get()
            print(label, "changed:", widget.get())
            print("selected songs:", len(self.selected_songs))
            widget.delete(0, "end")
            widget.configure(placeholder_text=input_text)
            for path in self.selected_songs:
                print(path, label, input_text)
                song = EasyID3(path)
                song[label] = input_text
                song.save(v2_version=3)
            self.refresh_scroll_frame()

        for pos, label in enumerate(self.frames.keys()):
            customtkinter.CTkLabel(
                master=self.edit_downloaded_tags_frame,
                text=label.capitalize(),
                wraplength=150,
            ).grid(row=pos, column=0, padx=20, pady=5, sticky="w")
            e = customtkinter.CTkEntry(
                master=self.edit_downloaded_tags_frame,
                placeholder_text=label,
                width=250,
            )
            e.bind(
                "<Return>",
                lambda event, widget=e, label=label: on_entry_change(widget, label),
            )
            e.grid(row=pos, column=1)
            self.edit_downloaded_entries[label] = e

    def refresh_scroll_frame(self):
        # clear selected songs each time to avoid having multiple istances of the same song present
        self.selected_songs = []
        self.view_downloaded_scroll_frame = customtkinter.CTkScrollableFrame(
            self.view_downloaded_frame
        )
        self.view_downloaded_scroll_frame.bind(
            "<Button-1>", lambda event: print("view_downloaded_scoll_frame")
        )

        self.view_downloaded_scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.view_downloaded_scroll_frame.focus()

        def extract_frame(file_path, frame):
            song_tags = ID3(file_path)
            frame = song_tags.get(frame)
            if frame:
                return frame.text[0]
            return ""

        sorted_files = []
        for file in os.listdir(File.check_dir(self.settings.song_path)):
            if file.lower().endswith(".mp3"):
                sorted_files.append(file)

        sorted_files.sort(
            key=lambda file: extract_frame(
                os.path.join(self.settings.song_path, file), self.sort_frame
            )
        )

        # draw song details
        for i, file in enumerate(sorted_files, start=1):
            file_path = os.path.join(self.settings.song_path, file)
            song_tags = ID3(file_path)
            tags = {}
            for label, frame in self.frames.items():
                if song_tags.get(frame):
                    tags[label] = song_tags[frame].text[0]
                else:
                    tags[label] = ""

            tags.update(
                {
                    "length": song_tags.getall("TLEN"),
                    "cover": song_tags.getall("APIC")[0].data,
                }
            )

            SongLabel(
                master=self.view_downloaded_scroll_frame,
                func=self.select_song,
                row=i,
                tags=tags,
                # image=song_tags.get("APIC"),
                active_songs=self.selected_songs,
                song_path=file_path,
                # ).grid(row=i, column=0, sticky="nsew")
            ).pack(fill="both")

    def draw_research_frame(self):
        self.research_existing_frame = customtkinter.CTkFrame(self)
        self.research_existing_frame.columnconfigure(0, weight=1)
        self.research_existing_frame.rowconfigure(0, weight=0)
        self.research_existing_frame.rowconfigure(1, weight=1)
        self.research_button = customtkinter.CTkButton(
            self.research_existing_frame,
            command=lambda: self.research_tracks(
                self.settings.research_src, self.settings.dir
            ),
            text="Research existing songs",
        )
        self.research_button.grid(sticky="nsew")
        self.research_existing_scroll_frame = customtkinter.CTkScrollableFrame(
            self.research_existing_frame
        )
        self.research_existing_scroll_frame.grid(row=1, column=0, sticky="nsew")

        sorted_files = []
        for file in os.listdir(File.check_dir(self.settings.research_failed)):
            if file.lower().endswith(".mp3"):
                sorted_files.append(file)

        # draw song details
        for i, file in enumerate(sorted_files, start=1):
            file_path = os.path.join(self.settings.research_failed, file)
            song_tags = ID3(file_path)
            tags = {}
            for label, frame in self.frames.items():
                if song_tags.getall(frame):
                    tags[label] = song_tags[frame].text[0]
                else:
                    tags[label] = ""
            tags["length"] = song_tags.getall("TLEN")[0]

            if song_tags.getall("APIC"):
                tags["cover"] = song_tags.getall("APIC")[0].data
            else:
                tags["cover"] = self.settings.default_cover

            SongLabel(
                master=self.research_existing_scroll_frame,
                func=lambda file=file: self.open_research_dialog(
                    research_data_path="research_data.json", file=file
                ),
                row=i,
                tags=tags,
                song_path=file_path,
            ).grid(row=i, column=0, sticky="nsew")

    def draw_settings_frame(self):
        self.__keep_cover = customtkinter.BooleanVar()
        self.settings_frame = customtkinter.CTkFrame(self)
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

    # @staticmethod
    def draw_header(self, master, labels):
        frame = customtkinter.CTkFrame(master=master, height=20)

        def sort_header(event, frame):
            self.sort_frame = self.frames[frame]
            self.refresh_scroll_frame()
            # event.widget.configure(fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"])

        for col, label_text in enumerate(labels):
            l = customtkinter.CTkLabel(
                master=frame,
                text=label_text,
                width=100 if not label_text == "Cover" else 50,
            )
            l.grid(row=0, column=col, padx=5, pady=5)
            l.bind(
                "<Button-1>", lambda event, t=label_text: sort_header(event, t.lower())
            )
        return frame

    def select_frame_by_name(self, name):
        # Set button colors for selected button
        for button_name, button in self.__buttons.items():
            fg_color = ("gray75", "gray25") if name == button_name else "transparent"
            button.configure(fg_color=fg_color)

        # Show selected frame
        frames = [
            self.download_frame,
            self.view_downloaded_frame,
            # self.research_existing_frame,
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
        self.select_frame_by_name("download")
        self.download_progress.set(0)
        self.update_blacklist()
        if self.verify_switch.get():
            self.tagger.verify_tags(self.blacklist)
        else:
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
                self.entry.delete(0, "end")
                self.entry.configure(placeholder_text="")

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
            self.download_scroll_frame,
            row=i,
            tags=song_tags,
        ).grid(row=i, column=0, sticky="nsew")

        progress = customtkinter.CTkProgressBar(self.download_scroll_frame)
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
        research_data = File.get_json("research_data.json")
        for file in os.listdir(File.check_dir(src)):
            if file.lower().endswith(".mp3"):
                fullpath = os.path.join(src, file)
                try:
                    res = self.tagger.research_uri(fullpath)
                except:
                    print("EXCEPTION")
                    continue
                # list contains possible researched tracks to choose from -> no automatic re-naming
                if isinstance(res, list):
                    research_data[file] = res
                    os.rename(
                        fullpath,
                        os.path.join(dest, File.check_dir("no-data"), file),
                    )
                else:
                    os.rename(fullpath, os.path.join(dest, res + ".mp3"))

        File.append_json(research_data, "research_data.json")
        self.draw_research_frame()
        self.select_frame_by_name("research_existing")

    def select_song(self):
        image = self.settings.default_cover

        # Clear entry contents
        for entry in self.edit_downloaded_entries.values():
            entry.configure(placeholder_text="")

        num_selected_songs = len(self.selected_songs)

        if num_selected_songs == 0:
            self.edit_downloaded_frame.grid_forget()
            return

        self.edit_downloaded_frame.grid(row=0, rowspan=2, column=1, sticky="nsew")

        if num_selected_songs == 1:
            song = ID3(self.selected_songs[0])
            apic_frames = song.getall("APIC")[0]

            if apic_frames:
                image = customtkinter.CTkImage(
                    Image.open(BytesIO(apic_frames.data)),
                    size=(300, 300),
                )

            for label, frame in self.frames.items():
                tags = song[frame].text[0] if song.get(frame) else ""
                self.edit_downloaded_entries[label].configure(placeholder_text=tags)

        else:
            song_tags = [{} for _ in range(num_selected_songs)]
            # get all tags from clicked songs
            for i, file in enumerate(self.selected_songs):
                song = ID3(file)
                for label, frame in self.frames.items():
                    song_tags[i][label] = song[frame].text[0] if song.get(frame) else ""

            common_values = {}
            first_song_tags = song_tags[0]

            # Check if value is common across all songs
            for key, common_value in first_song_tags.items():
                is_common = all(song[key] == common_value for song in song_tags)
                if is_common:
                    common_values[key] = common_value
                    # only display values that are common
                    self.edit_downloaded_entries[key].configure(
                        placeholder_text=common_value
                    )

        self.album_cover.configure(image=image)

    def open_research_dialog(self, research_data_path, file):
        tags_list = File.get_json(research_data_path)[file]
        ResearchDialog(
            file=file,
            tags_list=tags_list,
            labels=self.settings.labels_text[:-1],
            source_path=self.settings.research_failed,
            dest_path=self.settings.dir
            # func=self.handle_dialog,
        )


if __name__ == "__main__":
    app = App()
    app.mainloop()
