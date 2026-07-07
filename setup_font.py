"""Download SolaimanLipi Bengali font."""

import os
import urllib.request

FONT_DIR = "fonts"
FONT_URL = "https://github.com/shiftenterdev/bangla-font/raw/refs/heads/master/SolaimanLipi.ttf"
FONT_PATH = os.path.join(FONT_DIR, "SolaimanLipi.ttf")


def main():
    os.makedirs(FONT_DIR, exist_ok=True)
    if os.path.exists(FONT_PATH):
        print(f"Font already exists at {FONT_PATH}")
        return
    print(f"Downloading SolaimanLipi font...")
    urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    size = os.path.getsize(FONT_PATH)
    print(f"Downloaded! ({size} bytes)")


if __name__ == "__main__":
    main()
