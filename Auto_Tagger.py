import re  # various regex functions
import os  # move songs in folders
import json  # save blacklist
import requests  # download albumcover
import shutil  # download albumcover
import argparse  # additional arguments
import threading
from pprint import pprint
from enum import Enum
from spotipy.client import Spotify  # spotify meta-data
from spotipy.oauth2 import SpotifyClientCredentials  # Spotify API Credentials
from pytube import YouTube  # download yt-videos
from pytube import Search  # search yt-videos
from mutagen.easyid3 import EasyID3  # set ID3-tags
from mutagen.id3 import ID3, APIC  # set albumcover
from mutagen.mp3 import MP3
import ffmpeg

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
            File.append_json(path=path, data={"blacklist": {}, "whitelist": {}})
        file = open(path, "r")
        data = json.load(file)
        file.close()
        return data

    @staticmethod
    def append_json(data, path):
        with open(path, "w+") as file:
            file.seek(0)
            json.dump(data, file, sort_keys=True, indent=4)

    @staticmethod
    def check_dir(path):
        if not os.path.exists(path):
            os.mkdir(path)
        return path


def convert_to_dash_pattern(s):
    # Use regular expression to replace the content inside parentheses with a dash
    result = re.sub(r"\((.*?)\)", r"- \1", s)
    return result


class Tagger:
    def __init__(self):
        self.verify_path = os.getcwd()
        self.destination = os.path.join(os.getcwd(), "done")

        if not os.path.exists("credentials.json"):
            File.append_json(data={"cid": "", "secret": ""}, path="credentials.json")
        credentials = File.get_json(path="credentials.json")
        self.sp = Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=credentials["cid"], client_secret=credentials["secret"]
            )
        )
        return

    def research_uri(self, file_path: str):
        song_id3 = ID3(file_path)
        song_mp3 = MP3(file_path)
        track: str = convert_to_dash_pattern(song_id3["TIT2"].text[0]).lower()
        artist: str = song_id3["TPE1"].text[0].lower()
        album: str = song_id3["TALB"].text[0].lower()
        length = song_mp3.info.length

        query = f"track: {track},artist: {artist},album: {album}"
        request = json.loads(json.dumps(self.sp.search(query, type="track")))

        def debug_info(issue, expected, actual):
            print(file_path, f"- {issue} incorrect: {expected} != {actual}")

        for i in request["tracks"]["items"]:
            track_name = i["name"].lower()
            artist_name = i["artists"][0]["name"].lower()
            album_name = i["album"]["name"].lower()

            if track.lower() != track_name:
                debug_info("track", f"{track}", f"{track_name}")
            elif artist.lower() not in artist_name:
                debug_info("artist", f"{artist}", f"{artist_name}")
            elif album.lower() != album_name:
                debug_info("album", album, album_name)
            elif not length - 1000 <= i["duration_ms"] <= length + 1000:
                debug_info("length", length, i["duration_ms"])
            else:
                return i["id"]

        return False

    def get_tags(self, uri: str, mode: tag_mode_t = tag_mode_t.track) -> dict:
        match mode:
            case tag_mode_t.track:
                json_items = json.loads(json.dumps(self.sp.track(uri)))
                album_tags = self.extract_album_tags(
                    json.loads(json.dumps(self.sp.album(json_items["album"]["id"])))
                )
                new_playlist = {uri: self.extract_tags(json_items, album_tags)}
                return new_playlist
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

        tags["albumartist"] = "; ".join(album_artist)
        tags["organization"] = json_album["label"]
        tags["copyright"] = json_album["copyrights"][0]["text"]
        tags["date"] = json_album["release_date"]
        tags["cover"] = json_album["images"][1]["url"]
        tags["album"] = json_album["name"]

        if "genre" in tags:
            tags["genre"] = (json_album["genres"][0],)
        else:
            tags["genre"] = GENRE
        return tags

    @staticmethod
    def extract_tags(json_track, tags):
        artist = []
        for i in json_track["artists"]:
            artist.append(i["name"])

        tags["title"] = json_track["name"]
        tags["artist"] = "; ".join(artist)
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
    def convert_to_mp3(uri):
        # if os.path.isfile(uri + ".mp3") == False:
        ffmpeg.run(
            ffmpeg.output(
                ffmpeg.input(uri + ".mp4"),
                uri + ".mp3",
                format="mp3",
                acodec="libmp3lame",
                ab="320k",
            ),
            quiet=True,
        )
        # os.system("ffmpeg -i " + uri + ".mp4 " + uri + ".mp3 -loglevel warning")
        os.remove(uri + ".mp4")

    @staticmethod
    def assign_id3_tag(uri, tags):
        song = EasyID3(uri + ".mp3")
        status = status_t.unchanged
        for tag, value in tags.items():
            if tag == "duration_ms" or tag == "cover" or tag == "id":
                continue
            if tag in song:
                if not song[tag]:
                    # Don't overwrite existing genre
                    if tag == "genre":
                        continue
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

    def set_album_cover(self, uri, url):
        song = ID3(uri + ".mp3")
        if song.getall("APIC"):
            return status_t.unchanged

        response = requests.get(url, stream=True)
        with open(
            os.path.join(File.check_dir("cover"), uri) + ".jpg", "wb"
        ) as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response
        with open(
            os.path.join(self.verify_path, "cover", uri) + ".jpg", "rb"
        ) as album_cover:
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
        log(uri + ": Set new album cover")
        return status_t.new

    def verify_tags(self, blacklist):
        log("Verifying track in path: " + self.verify_path, "a")
        for filename in os.listdir(self.verify_path):
            uri = filename[:-4]
            if uri in blacklist["blacklist"]:
                print("uri in blacklist")
                continue
            if not filename.endswith(".mp3"):
                continue
            print("Verifying ", filename, end="")
            tags = self.get_tags(uri=uri)[uri]
            # if not (
            self.assign_id3_tag(uri, tags)
            # == status_t.unchanged and
            self.set_album_cover(uri, tags["cover"])
            # == status_t.unchanged ):
            # continue
            song = EasyID3(filename)
            blacklist["blacklist"][uri] = {
                "title": song["title"][0],
                "artist": song["artist"][0],
            }
            if uri in blacklist["whitelist"]:
                blacklist["whitelist"].pop(uri)
            os.rename(
                os.path.join(self.verify_path, filename),
                os.path.join(File.check_dir(self.destination), filename),
            )

        File.append_json(data=blacklist, path=self.verify_path + "/blacklist.json")
        # print("\rVerification done")


class Downloader:
    def __init__(self):
        self.tagger = Tagger()
        self.event = threading.Event()

    @staticmethod
    def extract_from_url(url):
        spotify_pattern = r"https://open\.spotify\.com/(?:intl-[a-z]{2}/)?(playlist|album|track)/([\w]+)"
        youtube_pattern = r"https://www\.youtube\.com/watch\?v=([\w_-]+)"

        spotify_match = re.match(spotify_pattern, url)
        youtube_match = re.match(youtube_pattern, url)

        if spotify_match:
            spotify_type = spotify_match.group(1)
            spotify_uri = spotify_match.group(2)
            return "Spotify", spotify_type, spotify_uri
        elif youtube_match:
            youtube_video_id = youtube_match.group(1)
            return "YouTube", None, youtube_video_id
        else:
            return "Unknown", None, None

    def downloader_thread(self, event, value, blacklist):
        self.event = event
        self.download_track(tags=value, blacklist=blacklist)
        File.append_json(
            data=blacklist, path=os.path.join(self.tagger.verify_path, "blacklist.json")
        )

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
        self.event.set()
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
                        self.event.set()
                        Tagger.convert_to_mp3(uri=uri)
                        self.event.set()
                        try:
                            self.tagger.assign_id3_tag(uri, tags)
                            self.event.set()
                        except:
                            log("Could not find " + uri + "(" + tags["title"] + ")")
                        try:
                            self.tagger.set_album_cover(uri, tags["cover"])
                            self.event.set()
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
    print(string)
    with open("log.txt", mode) as file:
        file.write(string + "\n")


if __name__ == "__main__":
    print("module is deprecated. Please use the GUI: 'app.py'")
