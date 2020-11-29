![Screeenshot](https://i.imgur.com/ZVGL1AZ.png)

Python Carplay implementation for the "Autobox" dongles. Forked from https://github.com/electric-monk/pycarplay to include audio/video output via mpv and key presses

Video of WIP here: 
https://www.youtube.com/watch?v=D8P99BTqCCo

# Dongles

These are readily available from Amazon, but are also available from cheaper sources. The one I got was labelled "Carlinkit" here: https://www.aliexpress.com/item/32829019768.html

# Setup
## Download assets from the .APK
The dongle relies on the copying of various "assets" to the dongle that happens on every boot. To acquire these assets, a script is provided.

Simply run:
```
./downloadassets.sh
```
from the repository root.

## Dependencies
This script relies on the following packages (installed via `apt-get` or otherwise):
* ffmpeg
* mpv
* libmpv 
* libmpv-dev

## Setup and running

The code is intended for Python3. To install the necessary packages, run this command:
```
pip3 install pyusb 
```

To run, call 
```
sudo python3 carplay.py
```
(note: you need a user that is allowed to manipulate usb devices, or run as)

# Implementation
# Finally
The real 'guts' of this project that drive device communication were not Implemented by me. They were discovered by Colin Monro (Electric-monk). His repo is here: https://github.com/electric-monk/pycarplay
