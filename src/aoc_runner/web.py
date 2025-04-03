"""
Utility functions for interacting with the Advent of Code website
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(os.getcwd(), ".env"))
AOC_COOKIE = os.getenv("AOC_COOKIE", "")
assert AOC_COOKIE, "No AOC_COOKIE found in environment variables"

CACHE_DIR = Path(os.getenv("CACHE_DIR", Path(os.getcwd(), "__cache__")))


def get_from_url(url: str, data: Optional[Dict]=None, **kwargs) -> BeautifulSoup:
    """
    Get the content of a given URL
    """
    if Path(CACHE_DIR, AOC_COOKIE, url.replace("https://", "").replace("/", "_")).exists():
        with open(Path(CACHE_DIR, AOC_COOKIE, url.replace("https://", "").replace("/", "_")), "r") as f:
            return BeautifulSoup(f.read(), 'html.parser')
    
    if data:
        response = requests.post(url, cookies={"session": AOC_COOKIE}, data=data, timeout=0.5)
    else:
        response = requests.get(url, cookies={"session": AOC_COOKIE}, timeout=0.5)

    if response.status_code != 200:
        raise FileNotFoundError(f"Error: {response.status_code} for {url=}")
    
    response = BeautifulSoup(response.content, 'html.parser')

    os.makedirs(Path(CACHE_DIR, AOC_COOKIE), exist_ok=True)
    with open(Path(CACHE_DIR, AOC_COOKIE, url.replace("https://", "").replace("/", "_")), "w") as f:
        f.write(str(response))

    return response


def get_input(year: int, day: int, *args, **kwargs) -> str:
    """
    Get the input for a given year and day from the Advent of Code website
    """
    return get_from_url(f"https://adventofcode.com/{year}/day/{day}/input").text


def get_answers(year: int, day: int, *args, **kwargs) -> Dict[int, str]:
    """
    Get the answers for a given year and day from the Advent of Code website
    """
    soup = get_from_url(f"https://adventofcode.com/{year}/day/{day}")
    
    part_answers = {}
    for part, ans_str in enumerate(filter(None, map(lambda p: re.search(r"Your puzzle answer was (.+)\.", p.text), soup.find_all("p"))), 1):
        part_answers[part] = ans_str.group(1)

    return part_answers

def submit_answer(year: int, day: int, part: int, ans: str, *args, **kwargs) -> bool:
    """
    Submit an answer for a given year and day to the Advent of Code website
    """
    soup = get_from_url(f"https://adventofcode.com/{year}/day/{day}/answer", data={"level": part, "answer": ans}).text
    return re.search(r"That's the right answer", soup) or re.search(r"You don't seem to be solving the right level", soup)

def get_leaderboard(year: int, *args, **kwargs) -> str:
    """
    Get the leaderboard for a given year from the Advent of Code website
    """
    soup = get_from_url(f"https://adventofcode.com/{year}/leaderboard/self")
    return str(soup)
