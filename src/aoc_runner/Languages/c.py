import os
import platform
from pathlib import Path

from . import Language


class C(Language):
    """
    Class for the C language.
    """

    def __init__(self) -> None:
        super().__init__("c")
        self.folder = False
        self.ext = ".c"

    def parent_dir(self, year: int, day: int) -> Path:
        return Path(os.getcwd(), f"{year}", "c")

    def compile_str(self, year: int, day: int) -> str:
        return f"gcc {day}.c -o {day}{'.exe' if platform.system() == 'Windows' else ''} -lm"

    def run_str(self, year: int, day: int) -> str:
        return (
            f".{os.sep}{day}{'.exe' if platform.system() == 'Windows' else ''} {self.input_loc(year, day)}"
        )
