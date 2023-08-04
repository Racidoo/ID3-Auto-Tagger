# ID3-Auto-Tagger
Downloads any song from Spotify/Youtube (track, album, playlist) and automatically assigns important ID3-tags

## Table of Contents
* [Features](#features)
* [Installation](#installation)
* [Dependencies](#dependencies)
## Features
- Download any song from Youtube and convert it to .mp3
- Research meta-data from a Spotify API and assign ID3-Tags to the .mp3
- Import tracks, albums, or playlists from Spotify and download them
- Verify ID3-Tags of existings songs (and update them when missing)
## Installation

Download main project:
```
$ git clone https://github.com/Racidoo/ID3-Auto-Tagger.git
```

Install dependencies:
```
$ pip install -r requirements.txt
```
Run app:
```
$ python3 app.py
```

## Dependencies

This project currently relies on following packages:
* customtkinker
* ffmpeg
* mutagen
* Pillow
* pytube
* spotipy