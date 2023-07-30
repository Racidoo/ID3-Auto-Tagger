import re  # various regex functions
import os  # move songs in folders
import json  # save blacklist
import requests  # download albumcover
import shutil  # download albumcover
import argparse  # additional arguments
from pprint import pprint
from enum import Enum
import spotipy  # spotify meta-data
from spotipy.oauth2 import SpotifyClientCredentials  # Spotify API Credentials
from pytube import YouTube  # download yt-videos
from pytube import Search  # search yt-videos
from mutagen.easyid3 import EasyID3  # set ID3-tags
from mutagen.id3 import ID3, APIC  # set albumcover
from alive_progress import alive_bar  # visualize progress

import tkinter
import customtkinter

GENRE = "Unknown"


class tag_mode_t(Enum):
    track = "track"
    album = "album"
    playlist = "playlist"


class status_t(Enum):
    new = 0
    changed = 1
    unchanged = 2


def get_json(path):
    if not os.path.exists(path):
        append_json(path, {"blacklist": {}, "whitelist": {}})
    file = open(path, "r")
    data = json.load(file)
    file.close()
    return data


def append_json(path, data):
    with open(path, "w+") as file:
        file.seek(0)
        json.dump(data, file, sort_keys=True, indent=4)


credentials = get_json("credentials.json")
cid = credentials["cid"]
secret = credentials["secret"]

client_credentials_manager = SpotifyClientCredentials(
    client_id=cid, client_secret=secret
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


def get_tags(uri: str, mode: tag_mode_t = tag_mode_t.track) -> dict:
    match mode:
        case tag_mode_t.track:
            json_items = json.loads(json.dumps(sp.track(uri)))
            album_tags = extract_album_tags(
                json.loads(json.dumps(sp.album(json_items["album"]["id"])))
            )
            return extract_tags(json_items, album_tags)
        case tag_mode_t.album:
            json_items = json.loads(json.dumps(sp.album(uri)))
            album_tags = extract_album_tags(json_items)

            new_playlist = {
                tracks["id"]: extract_tags(
                    json.loads(json.dumps(sp.track(tracks["id"]))), album_tags.copy()
                ).copy()
                for tracks in json_items["tracks"]["items"]
            }
            return new_playlist

        case tag_mode_t.playlist:
            json_items = json.loads(json.dumps(sp.playlist(uri)))["tracks"]["items"]
            new_playlist = {}
            for track in json_items:
                album_tags = extract_album_tags(
                    json.loads(json.dumps(sp.album(track["track"]["album"]["id"])))
                )
                tag = extract_tags(track["track"], album_tags.copy())
                new_playlist[track["track"]["id"]] = tag
            return new_playlist


def extract_album_tags(json_album) -> dict:
    album_artist = []
    tags: dict = {}
    for i in json_album["artists"]:
        album_artist.append(i["name"])

    tags["albumartist"] = ";".join(album_artist)
    tags["organization"] = json_album["label"]
    tags["copyright"] = json_album["copyrights"][0]["text"]
    tags["date"] = json_album["release_date"]
    tags["cover"] = json_album["images"][1]["url"]
    tags["album"] = json_album["name"]

    try:
        tags["genre"] = (json_album["genres"][0],)
    except:
        tags["genre"] = GENRE
    return tags


def extract_tags(json_track, tags):
    artist = []
    for i in json_track["artists"]:
        artist.append(i["name"])

    tags["title"] = json_track["name"]
    tags["artist"] = ";".join(artist)
    tags["discnumber"] = str(json_track["disc_number"])
    tags["duration_ms"] = json_track["duration_ms"]
    tags["id"] = json_track["id"]
    tags["tracknumber"] = str(json_track["track_number"])

    regex = r" - (.*)"
    matches = re.finditer(regex, str(json_track["name"]))
    for matchNum, match in enumerate(matches, start=1):
        for groupNum in range(0, len(match.groups())):
            groupNum = groupNum + 1
            tags["version"] = match.group(groupNum)

    return tags


def assign_id3_tag(uri, tags):
    if os.path.isfile(uri + ".mp3") == False:
        os.system("ffmpeg -i " + uri + ".mp4 " + uri + ".mp3 -loglevel warning")
        os.system("rm " + uri + ".mp4")

    song = EasyID3(uri + ".mp3")
    status = status_t.unchanged
    for tag, value in tags.items():
        if tag == "duration_ms" or tag == "cover" or tag == "id":
            continue
        if tag in song:
            if not song[tag]:
                log(uri + ": Changed " + tag + " from " + song[tag] + " to " + value)
                song[tag] = value
                status = status_t.changed
        else:
            song[tag] = value
            log(uri + ": Added " + value + " to " + tag)
            status = status_t.new
    song.save()
    return status


def set_album_cover(uri, url):
    song = ID3(uri + ".mp3")
    if song.getall("APIC"):
        return status_t.unchanged

    log(uri + ": Set new album cover")
    response = requests.get(url, stream=True)

    with open("cover/" + uri + ".jpg", "wb") as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response
    with open("cover/" + uri + ".jpg", "rb") as album_cover:
        song.add(
            APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=album_cover.read(),
            )
        )
    song.save()
    return status_t.new


def download(uri, mode, blacklist):
    log("Download " + mode.value + ": " + uri, "a")
    tags = get_tags(uri, mode)
    with alive_bar(len(tags), calibrate=100) as bar:
        for key, value in tags.items():
            bar()
            download_track(tags=value, blacklist=blacklist)


# ToDo: download missing tracks, which are to long or extended remix
def download_track(tags, blacklist):
    regex = r"videoId=(.*?)\>"
    uri = tags["id"]
    if uri in blacklist["blacklist"]:
        log(uri + ".mp3: File already exists.")
        return

    title = tags["title"]
    artist = tags["artist"]
    time_s = int(tags["duration_ms"] / 1000)
    search = artist + " - " + title
    s = Search(search)
    for song in s.results:
        matches = re.finditer(regex, str(song))
        for matchNum, match in enumerate(matches, start=1):
            for groupNum in range(0, len(match.groups())):
                groupNum = groupNum + 1
                group = match.group(groupNum)
                yt = YouTube("https://www.youtube.com/watch?v=" + group)
                if yt.length <= time_s + 2 and yt.length >= time_s - 2:
                    yt.streams.filter(only_audio=True).first().download(
                        os.getcwd(), uri + ".mp4"
                    )

                    assign_meta_data(tags)
                    return
    log("Could not download: " + search)
    if not uri in blacklist["whitelist"]:
        blacklist["whitelist"][uri] = {
            "title": title,
            "artist": artist,
            "length": str(int(time_s / 60)) + ":" + str(time_s % 60),
            "UID": "",
        }


def assign_meta_data(tags):
    uri = tags["id"]
    try:
        assign_id3_tag(uri, tags)
    except:
        log("Could not find " + uri + "(" + tags["title"] + ")")
    try:
        set_album_cover(uri, tags["cover"])
    except:
        log("Could not assign album cover: " + tags["title"])


def log(string, mode="a"):
    with open("log.txt", mode) as file:
        file.write(string + "\n")


def verify_tags(path, blacklist):
    log("Verifying track in path: " + path, "a")
    for filename in os.listdir(path):
        uri = filename[:-4]
        if uri in blacklist["blacklist"]:
            continue
        if not filename.endswith(".mp3"):
            continue
        print("\rVerifying ", filename, end="")
        tags = get_tags(uri)
        if not (
            assign_id3_tag(uri, tags) == status_t.unchanged
            and set_album_cover(uri, tags["cover"]) == status_t.unchanged
        ):
            continue
        song = EasyID3(filename)
        blacklist["blacklist"][uri] = {
            "title": song["title"][0],
            "artist": song["artist"][0],
        }
        if uri in blacklist["whitelist"]:
            blacklist["whitelist"].pop(uri)
        os.rename(path + filename, path + "done/" + filename)

    print("\rVerification done")


class Settings:
    def __init__(self):
        self.blacklist_path = "blacklist.json"
        self.dir = "/home/racido/YT-Downloader/"


class App(customtkinter.CTk):
    def __init__(self):
        self.settings = Settings()
        super().__init__()

        self.blacklist = get_json(self.settings.blacklist_path)

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
        verify_tags(path=self.settings.dir, blacklist=self.blacklist)
        append_json(path=self.settings.blacklist_path, data=self.blacklist)
        # self.select_frame_by_name("verify")

    def submit_button_event(self):
        uri = self.entry.get()
        # pprint(get_tags(uri=uri))
        tags = get_tags(uri=uri)
        print(tags["id"])
        if uri in self.blacklist["blacklist"]:
            print("track exists")
        download_track(tags, blacklist=self.blacklist)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-a", "--album", required=False, help="Spotify album uri")
    ap.add_argument("-p", "--playlist", required=False, help="Spotify playlist uri")
    ap.add_argument("-t", "--track", required=False, help="Spotify track uri")
    ap.add_argument(
        "-v",
        "--verify",
        required=False,
        help="Verify existing files",
        action="store_true",
    )
    ap.add_argument(
        "-n",
        "--nogui",
        required=False,
        help="Execute without GUI",
        action="store_true",
    )
    args = vars(ap.parse_args())

    if args["nogui"]:
        blacklist = get_json(path="blacklist.json")
        if args["album"]:
            download(
                uri=args["album"],
                mode=tag_mode_t.album,
                blacklist=blacklist,
            )
        elif args["playlist"]:
            download(
                uri=args["playlist"],
                mode=tag_mode_t.playlist,
                blacklist=blacklist,
            )
        elif args["track"]:
            download_track(get_tags(args["track"]), blacklist=blacklist)
        if args["verify"]:
            verify_tags(os.getcwd(), blacklist)
            append_json(blacklist)
        return

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
