import os
import platform
from pathlib import Path

from . import Language


class Rust(Language):
    """
    Class for Rust programs.
    """

    def __init__(self) -> None:
        super().__init__("rust")
        self.folder = True
        self.ext = ".rs"

    def executable_path(self, year: int, day: int) -> Path:
        return Path("target", "release", f"rust_{year}_{day}{'.exe' if platform.system() == 'Windows' else ''}")

    def parent_dir(self, year: int, day: int) -> Path:
        return Path(os.getcwd(), f"{year}", "rust", f"{day}")

    def compile_str(self, year: int, day: int) -> str:
        return "cargo build --release"

    def run_str(self, year: int, day: int) -> str:
        return f"cargo run --release {self.input_loc(year, day)}"
