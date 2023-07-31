import tkinter
import customtkinter
import os
from Auto_Tagger import Tagger, Downloader, File


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

        self.blacklist = File.get_json(self.settings.blacklist_path)

        # configure window
        self.title("Song verifier")
        self.geometry(f"{1100}x{580}")

        # menu bar

        self.menu = tkinter.Menu(self)
        self.config(menu=self.menu)
        # File
        self.file_menu = tkinter.Menu(self.menu)
        self.menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New")
        self.file_menu.add_command(label="Open...")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit)
        # View
        view_menu = tkinter.Menu(self.menu)
        self.menu.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Appearance Mode")
        self.scaling_option_menu = customtkinter.CTkOptionMenu(
            view_menu,
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event,
        )
        view_menu.add_cascade(label="UI Scaling", menu=self.scaling_option_menu)
        # Help
        help_menu = tkinter.Menu(self.menu)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About")

        # configure grid layout (4x4)

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((1, 3), weight=5)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # create sidebar frame with widgets
        self.navigation_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = customtkinter.CTkLabel(
            self.navigation_frame,
            text="CustomTkinter",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # create navigation frame
        self.navigation_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1)

        # create input frame
        # self.input_frame = customtkinter.CTkFrame(self, height=20, corner_radius=0)
        # self.input_frame.grid(row=4, column=0, sticky="nsew")
        # self.input_frame.grid_rowconfigure(4, weight=1)

        self.entry = customtkinter.CTkEntry(
            self, placeholder_text="Enter Spotify-URI from track, album or playlist"
        )
        self.entry.grid(
            row=3, column=1, columnspan=3, padx=(20, 0), pady=(20, 20), sticky="nsew"
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

        self.track_button = customtkinter.CTkButton(
            self.navigation_frame,
            command=self.track_button_event,
            text="Download Track",
        )
        self.track_button.grid(row=1, column=0, padx=20, pady=10)
        self.album_button = customtkinter.CTkButton(
            self.navigation_frame,
            command=self.album_button_event,
            text="Download Album",
        )
        self.album_button.grid(row=2, column=0, padx=20, pady=10)
        self.playlist_button = customtkinter.CTkButton(
            self.navigation_frame,
            command=self.playlist_button_event,
            text="Download Playlist",
        )
        self.playlist_button.grid(row=3, column=0, padx=20, pady=10)

        self.verify_button = customtkinter.CTkButton(
            self.navigation_frame,
            command=self.verify_button_event,
            text="Verify Tags",
        )
        self.verify_button.grid(row=4, column=0, padx=20, pady=10)

        self.settings_button = customtkinter.CTkButton(
            self.navigation_frame,
            command=self.settings_button_event,
            text="Settings",
        )
        self.settings_button.grid(row=5, column=0, padx=20, pady=10)

        # self.appearance_mode_label = customtkinter.CTkLabel(
        #     self.navigation_frame, text="Appearance Mode:", anchor="w"
        # )
        # self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        # self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
        #     self.navigation_frame,
        #     values=["Light", "Dark", "System"],
        #     command=self.change_appearance_mode_event,
        # )
        # self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        # self.scaling_label = customtkinter.CTkLabel(
        #     self.navigation_frame, text="UI Scaling:", anchor="w"
        # )
        # self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        # self.scaling_optionemenu = customtkinter.CTkOptionMenu(
        #     self.navigation_frame,
        #     values=["80%", "90%", "100%", "110%", "120%"],
        #     command=self.change_scaling_event,
        # )
        # self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        self.track_frame = customtkinter.CTkFrame(
            self, corner_radius=0, fg_color="transparent"
        )
        self.track_frame.grid_columnconfigure(0, weight=1)
        self.album_frame = customtkinter.CTkFrame(
            self, corner_radius=0, fg_color="transparent"
        )
        self.album_frame.grid_columnconfigure(0, weight=1)
        self.playlist_frame = customtkinter.CTkFrame(
            self, corner_radius=0, fg_color="transparent"
        )
        self.playlist_frame.grid_columnconfigure(0, weight=1)
        self.settings_frame = customtkinter.CTkFrame(
            self, corner_radius=0, fg_color="transparent"
        )
        self.settings_frame.grid_columnconfigure(0, weight=1)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def sidebar_button_event(self):
        print("sidebar_button click")

    def select_frame_by_name(self, name):
        # set button color for selected button
        # self.track_button.configure(
        #     fg_color=("gray75", "gray25") if name == "track" else "transparent"
        # )
        # self.album_button.configure(
        #     fg_color=("gray75", "gray25") if name == "album" else "transparent"
        # )
        # self.playlist_button.configure(
        #     fg_color=("gray75", "gray25") if name == "playlist" else "transparent"
        # )
        # self.settings_button.configure(
        #     fg_color=("gray75", "gray25") if name == "playlist" else "transparent"
        # )

        # show selected frame
        if name == "track":
            self.track_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.track_frame.grid_forget()
        if name == "album":
            self.album_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.album_frame.grid_forget()
        if name == "playlist":
            self.playlist_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.playlist_frame.grid_forget()

    def button_event(self, button):
        self.select_frame_by_name(name=button)

    def track_button_event(self):
        self.select_frame_by_name("track")

    def album_button_event(self):
        self.select_frame_by_name("album")

    def playlist_button_event(self):
        self.select_frame_by_name("playlist")

    def settings_button_event(self):
        self.select_frame_by_name("settings")

    def verify_button_event(self):
        self.downloader.tagger.verify_tags(path=self.settings.dir, blacklist=self.blacklist)
        File.append_json(path=self.settings.blacklist_path, data=self.blacklist)
        # self.select_frame_by_name("verify")

    def submit_button_event(self):
        uri = self.entry.get()
        # pprint(get_tags(uri=uri))
        tags = self.downloader.tagger.get_tags(uri=uri)
        # print(tags["id"])
        if uri in self.blacklist["blacklist"]:
            print("track exists")
        self.downloader.download_track(tags=tags, blacklist=self.blacklist)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
