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
import threading

GENRE = "Unknown"


class tag_mode_t(Enum):
    track = "Track"
    album = "Album"
    playlist = "Playlist"


class status_t(Enum):
    new = 0
    changed = 1
    unchanged = 2


class File:
    @staticmethod
    def get_json(path):
        if not os.path.exists(path):
            Tagger.append_json(path, {"blacklist": {}, "whitelist": {}})
        file = open(path, "r")
        data = json.load(file)
        file.close()
        return data

    @staticmethod
    def append_json(data, path):
        with open(path, "w+") as file:
            file.seek(0)
            json.dump(data, file, sort_keys=True, indent=4)


class Tagger:
    def __init__(self):
        if not os.path.exists("credentials.json"):
            File.append_json(data={"cid": "", "secret": ""}, path="credentials.json")
        credentials = File.get_json(path="credentials.json")
        self.sp = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=credentials["cid"], client_secret=credentials["secret"]
            )
        )
        return

    def get_tags(self, uri: str, mode: tag_mode_t = tag_mode_t.track) -> dict:
        match mode:
            case tag_mode_t.track:
                json_items = json.loads(json.dumps(self.sp.track(uri)))
                album_tags = self.extract_album_tags(
                    json.loads(json.dumps(self.sp.album(json_items["album"]["id"])))
                )
                return self.extract_tags(json_items, album_tags)
            case tag_mode_t.album:
                json_items = json.loads(json.dumps(self.sp.album(uri)))
                album_tags = self.extract_album_tags(json_items)

                new_playlist = {
                    tracks["id"]: self.extract_tags(
                        json.loads(json.dumps(self.sp.track(tracks["id"]))),
                        album_tags.copy(),
                    ).copy()
                    for tracks in json_items["tracks"]["items"]
                }
                return new_playlist

            case tag_mode_t.playlist:
                json_items = json.loads(json.dumps(self.sp.playlist(uri)))["tracks"][
                    "items"
                ]
                new_playlist = {}
                for track in json_items:
                    album_tags = self.extract_album_tags(
                        json.loads(
                            json.dumps(self.sp.album(track["track"]["album"]["id"]))
                        )
                    )
                    tag = self.extract_tags(track["track"], album_tags.copy())
                    new_playlist[track["track"]["id"]] = tag
                return new_playlist

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
                    log(
                        uri + ": Changed " + tag + " from " + song[tag] + " to " + value
                    )
                    song[tag] = value
                    status = status_t.changed
            else:
                song[tag] = value
                log(uri + ": Added " + value + " to " + tag)
                status = status_t.new
        song.save()
        return status

    @staticmethod
    def set_album_cover(uri, url):
        song = ID3(uri + ".mp3")
        if song.getall("APIC"):
            return status_t.unchanged

        log(uri + ": Set new album cover")
        response = requests.get(url, stream=True)
        if not os.path.exists("cover/"):
            os.makedirs("cover/")
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

    def verify_tags(self, path, blacklist):
        log("Verifying track in path: " + path, "a")
        for filename in os.listdir(path):
            uri = filename[:-4]
            if uri in blacklist["blacklist"]:
                print("uri in blacklist")
                continue
            if not filename.endswith(".mp3"):
                continue
            print("\rVerifying ", filename, end="")
            tags = self.get_tags(uri=uri)
            if not (
                self.assign_id3_tag(uri, tags) == status_t.unchanged
                and self.set_album_cover(uri, tags["cover"]) == status_t.unchanged
            ):
                continue
            song = EasyID3(filename)
            blacklist["blacklist"][uri] = {
                "title": song["title"][0],
                "artist": song["artist"][0],
            }
            if uri in blacklist["whitelist"]:
                blacklist["whitelist"].pop(uri)
            if not os.path.exists(path + "/done/"):
                os.makedirs(path + "/done/")
            os.rename(path + "/" + filename, path + "/done/" + filename)

        File.append_json(data=blacklist, path=path + "/blacklist.json")
        print("\rVerification done")


class Downloader:
    def __init__(self):
        self.tagger = Tagger()
        self.event = threading.Event()

    def download(self, uri, mode, blacklist):
        log("Download " + mode.value + ": " + uri, "a")
        tags = self.tagger.get_tags(uri, mode)
        # with alive_bar(len(tags), calibrate=100) as bar:
        for key, value in tags.items():
            # bar()
            self.download_track(tags=value, blacklist=blacklist)
            self.event.set()
            self.event.wait()
            self.event.clear()

    # ToDo: download missing tracks, which are to long or extended remix
    def download_track(self, tags, blacklist):
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

                        try:
                            self.tagger.assign_id3_tag(uri, tags)
                        except:
                            log("Could not find " + uri + "(" + tags["title"] + ")")
                        try:
                            self.tagger.set_album_cover(uri, tags["cover"])
                        except:
                            log("Could not assign album cover: " + tags["title"])
                        return
        log("Could not download: " + search)
        if not uri in blacklist["whitelist"]:
            blacklist["whitelist"][uri] = {
                "title": title,
                "artist": artist,
                "length": self.convert_to_mm_ss(time_s),
                "UID": "",
            }

    @staticmethod
    def convert_to_mm_ss(time_s):
        m = int(time_s / 60)
        s = int(time_s % 60)
        mm = ("0" if m < 10 else "") + str(m)
        ss = ("0" if s < 10 else "") + str(s)
        return mm + ":" + ss


def log(string, mode="a"):
    with open("log.txt", mode) as file:
        file.write(string + "\n")


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
    args = vars(ap.parse_args())

    downloader = Downloader()
    blacklist = File.get_json(path="blacklist.json")
    if args["album"]:
        downloader.download(
            uri=args["album"],
            mode=tag_mode_t.album,
            blacklist=blacklist,
        )
    elif args["playlist"]:
        downloader.download(
            uri=args["playlist"],
            mode=tag_mode_t.playlist,
            blacklist=blacklist,
        )
    elif args["track"]:
        downloader.download(
            uri=args["track"], mode=tag_mode_t.track, blacklist=blacklist
        )
    if args["verify"]:
        downloader.tagger.verify_tags(os.getcwd(), blacklist)
    return


if __name__ == "__main__":
    main()
