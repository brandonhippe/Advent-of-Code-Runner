"""
Readme (markdown) viewer for profiled AOC code
"""

import argparse
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Dict, Optional

from ..Languages import LANGS, Language
from ..Loggers import Logger
from ..Loggers.runtime_logger import RuntimeTracker
from . import Viewer, ViewerAction
from .tiles import TileMaker

PRESERVING_REGEXES = [
    # These regexes preserve the parameter tag that identifies the parameter
    re.compile(r"//[^\n]*#{\((?P<parameter_name>\w*)\)}\s*(?P<replace>.*?)\s*//[^\n]*#{/\((?P=parameter_name)\)}", re.MULTILINE | re.DOTALL),
    re.compile(r"<!--[^\n]*#{\((?P<parameter_name>\w*)\)}\s*-->\n(?P<replace>.*?)\s*<!--[^\n]*#{/\((?P=parameter_name)\)}[^\n]*", re.MULTILINE | re.DOTALL),
    re.compile(r"/\*[^\n]*#{\((?P<parameter_name>\w*)\)}[^\n]*\*/\s*(?P<replace>.*?)\s*/\*[^\n]*#{/\((?P=parameter_name)\)}[^\n]*\*/"),
]

DESTROYING_REGEXES = [
    # These regexes destroy the parameter tag that identifies the parameter
    re.compile(r"(?P<replace>#{\((?P<parameter_name>\w+?)\)})"),
]


@dataclass
class ReadmeViewer(Viewer):
    """
    Viewer for README files per year/language
    """

    args: argparse.Namespace
    name: str = "readme"
    verbose: bool = field(init=False)
    template_paths: Dict[str, str] = field(default_factory=dict)
    templates: Dict[str, str] = field(default_factory=lambda: defaultdict(str))

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """
        Add arguments to the parser. Must be a static method
        """
        parser.add_argument(
            "--readme",
            action=ViewerAction,
            nargs="*",
            help='Run the readme viewer. Add " verbose" to run in verbose mode',
            type=ReadmeViewer,
        )
        parser.add_argument(
            "--readme-attachments",
            nargs="*",
            default=[Path(Path(__file__).parent, "readme.yml")],
            help="Path to yaml file(s) that define the attachments for the readme viewer",
        )
        TileMaker.add_arguments(parser)

    ### Context manager functions
    def __enter__(self):
        super().__enter__()
        self.start_viewer()
        return self
    
    def start_viewer(self):
        """
        Start the viewer

        Loads the templates
        """
        for template_name, p in self.template_paths.items():
            p = Path(p)
            if not p.is_absolute():
                p = Path(__file__).parent / p

            self.print(f"Loading template {template_name} from {p}")            
            with open(p, "r") as file:
                self.templates[template_name] = file.read()

    def copy_incorrect(self, *args, from_logger: Optional[Logger]=None, **kwargs) -> None:
        """
        Copy the answer tracker data of incorrect answers
        """
        self.incorrect = from_logger.incorrect
    
    def write(self, *args, from_logger: Optional[Logger]=None, **kwargs) -> None:
        """
        Write the various README's based on answer data
        """
        if from_logger is None:
            return
        
        year_stars: Dict[int, Dict[Language, int]] = defaultdict(lambda: defaultdict(int))
        
        for lang in LANGS:
            for (year, day), part in product(lang.ran, [1, 2]):
                if (year < 2025 and (day, part) == (25, 2)) or (year >= 2025 and (day, part) == (12, 2)) or (year, day, part) in self.incorrect:
                    continue

                year_stars[year][lang] += 1

        total_stars = 0
        for year, year_data in year_stars.items():
            year_stars = max(year_data.values())
            if year_stars == (49 if year < 2025 else 23):
                year_stars += 1

            total_stars += year_stars

            self.print(f"Writing {year} README(s)")
            for lang, lang_year_stars in year_data.items():
                if lang_year_stars == (49 if year < 2025 else 23):
                    lang_year_stars += 1

                lang_title = str(lang).title()
                self.print(f"Writing {lang_title} README")
                readme_path = Path(os.getcwd(), str(year), str(lang), "README.md")
                with open(readme_path, "w") as f:
                    f.write(self.fill_in_template(self.templates["language"], **dict(filter(lambda item: item[0] != 'self', locals().items()))))
            
            readme_path = Path(os.getcwd(), str(year), "README.md")
            with open(readme_path, "w") as f:
                f.write(self.fill_in_template(self.templates["year"], **dict(filter(lambda item: item[0] != 'self', locals().items()))))

        self.print("Writing top-level README")
        readme_path = Path(os.getcwd(), "README.md")
        with open(readme_path, "w") as f:
            f.write(self.fill_in_template(self.templates["overall"], **dict(filter(lambda item: item[0] != 'self', locals().items()))))

    ### Other Helper Functions
    def fill_in_template(self, template: str, **kwargs) -> str:
        """
        Fill in the template with the arguments and variables.

        Looks for the key in the arguments, variables, and global functions, in that order.
        """
        vars().update(kwargs)
        used_args = set()
        filled_in = template[:]
        for match_regex, preserving in list(product(PRESERVING_REGEXES, (True,))) + list(product(DESTROYING_REGEXES, (False,))):
            for key_match in match_regex.finditer(template):
                context = key_match.group()
                parameter_name = key_match.group("parameter_name")
                replace_str = key_match.group("replace")

                if parameter_name in used_args and not preserving:
                    continue
                
                if hasattr(self, parameter_name):
                    # Key is a variable or function in this class
                    if callable(getattr(self, parameter_name)):
                        replace_with = getattr(self, parameter_name)(**kwargs)
                    else:
                        replace_with = str(getattr(self, parameter_name))
                elif parameter_name in locals():
                    # Key is a variable or function in this function
                    if callable(locals()[parameter_name]):
                        replace_with = locals()[parameter_name](**kwargs)
                    else:
                        replace_with = str(locals()[parameter_name])
                else:
                    # This will raise an error if the key is not a defined variable or a function in the global scope
                    try:
                        if callable(globals()[parameter_name]):
                            replace_with = globals()[parameter_name](**kwargs)
                        else:
                            replace_with = str(globals()[parameter_name])
                    except KeyError:
                        raise KeyError(f"No way to fill template key: {parameter_name}")
                
                if preserving:
                    used_args.add(parameter_name)
                
                filled_in = self.make_substitution(filled_in, context, replace_str, replace_with)

        return filled_in

    def make_substitution(self, template: str, context: str, replace_str: str, replace_with: str) -> str:
        """
        Make a substitution in the context string.
        """
        assert template
        if not context or not replace_str or not replace_with:
            return template
        
        replaced = context.replace(replace_str, replace_with, 1)
        return template.replace(context, replaced, 1)

    def lang_tiles(self, *args, readme_path: Path, lang: Optional[Language]=None, year: Optional[int]=None, year_stars: Optional[int]=None, from_logger: Optional[Logger]=None, **kwargs) -> str:
        """
        Get the readme tiles for a language
        """
        if not all([lang, year, from_logger]):
            return ""
        if year_stars is None:
            year_stars = 0

        lang_data = from_logger.data[lang]

        tile_maker = TileMaker(**vars(self.args))
        tile_maker.aoc_tiles_dir = Path(readme_path.parent, ".tiles", str(lang))
        tile_maker.image_dir = Path(tile_maker.aoc_tiles_dir, "images")
        tile_maker.what_to_show_on_right_side = "runtime"
        tile_str = tile_maker(*args, years=[year], languages=[lang], solutions_by_year=lang_data, readme_path=readme_path, **kwargs)
        return tile_str
    
    def year_tiles(self, *args, readme_path: Path, year: Optional[int]=None, year_stars: Optional[int]=None, from_logger: Optional[Logger]=None, **kwargs) -> str:
        """
        Get the readme tiles for a year
        """
        if not all([year, from_logger]):
            return ""
        if year_stars is None:
            year_stars = 0

        lang_data = RuntimeTracker()
        lang_list = []
        for lang in filter(lambda l: l in from_logger.data and year in from_logger.data[l], LANGS):
            lang_data.add_data(year, lang, new_data=from_logger.data[lang][year])
            lang_list.append(lang)

        tile_maker = TileMaker(**vars(self.args))
        tile_maker.aoc_tiles_dir = Path(readme_path.parent, ".tiles")
        tile_maker.image_dir = Path(tile_maker.aoc_tiles_dir, "images")
        tile_str = tile_maker(*args, years=[year], languages=lang_list, solutions_by_year=lang_data, readme_path=readme_path, **kwargs)
        return tile_str
    
    def solution_langs(self, *args, year: int, from_logger: Logger, **kwargs) -> str:
        """
        Get the list of solution languages
        """
        if from_logger is None:
            return ""
        
        lang_list = []
        for lang in filter(lambda l: [l, year] in from_logger.data, LANGS):
            lang_list.append(lang)

        return "\n".join([f" - [{str(lang).title()}]({lang}/README.md)" for lang in lang_list])

    
def git_username(*args, **kwargs) -> str:
    return re.search(r"user\.name=(.+)", subprocess.run(["git", "config", "--list"], capture_output=True, text=True).stdout).group(1).strip()

def submod_repos(*args, **kwargs) -> str:
    submod_text = subprocess.run(["git", "submodule"], capture_output=True, text=True).stdout
    md_out = ""
    for m in re.finditer(r"\b.* (\d+) \(.*\)", submod_text):
        submod = m.group(1)
        cwd = os.getcwd()
        os.chdir(submod)
        url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
        os.chdir(cwd)

        md_out += f"- [{submod}]({url})\n"

    return md_out
