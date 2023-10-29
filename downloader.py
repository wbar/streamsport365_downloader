#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import Iterable
import re
from progress.bar import IncrementalBar
from argparse import ArgumentParser

class Logger:
    def info(self, msg):
        print(msg)

logger = Logger()

M3U8_URL = "https://edge8.xmediaget.com:743/edge1/xrecord/{VIDEO_ID}/prog_index.m3u8"
FRAGMENT_URL = "https://edge8.xmediaget.com:743/edge1/xrecord/{VIDEO_ID}/{FRAGMENT_ID}"
COMMON_HEADERS = {
    "Origin": "https://streamsport365.com",
    "Referer": "https://streamsport365.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


def get_source_page(url: str) -> str:
    logger.info("Fetching page...")
    response = requests.get(url, headers=COMMON_HEADERS)
    response.raise_for_status()
    return response.text

def get_video_id(contents: str) -> str:
    logger.info("Parsing page...")
    soup = BeautifulSoup(contents, "html.parser")
    all_scripts: Iterable[Tag] = soup.find_all("script")
    element: str = [x.prettify() for x in all_scripts if "VideoCore_WS.VideoPlayerCore.Create(config)" in x.prettify()][-1]
    vid = re.findall(
        r'Source:."(?P<vid>[0-9]+)"',
        element,
        re.MULTILINE
    ).pop()
    logger.info(f"Found vid: {vid}")
    return vid

def get_fragments_list(video_id: str) -> Iterable[str]:
    logger.info(f"Detecting fragments for {video_id}")
    target = M3U8_URL.replace("{VIDEO_ID}", video_id)
    response = requests.get(
        target,
        headers=COMMON_HEADERS
    )
    response.raise_for_status()
    yield from (
        x for x in response.text.splitlines()
        if not x.startswith("#")
    )

def download_fragments(video_id:str, fragments_iter: Iterable[str]):
    fragments = list(fragments_iter)
    logger.info(f"Found {len(fragments)} fragments...")
    with open(f"{video_id}.ts", 'wb') as f:
        for fragment in IncrementalBar("Downloading", width=100, max=len(fragments)).iter(fragments):
            url = FRAGMENT_URL.replace("{VIDEO_ID}", video_id).replace("{FRAGMENT_ID}", fragment)
            response = requests.get(url, headers=COMMON_HEADERS)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=2**16):
                if chunk:
                    f.write(chunk)


def main(source_url: str):
    source = get_source_page(url=source_url)
    video_id = get_video_id(contents=source)
    fragments_iter = get_fragments_list(video_id=video_id)
    download_fragments(video_id=video_id, fragments_iter=fragments_iter)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()
    main(args.url)
