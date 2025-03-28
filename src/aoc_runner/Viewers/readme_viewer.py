"""
Readme (markdown) viewer for profiled AOC code
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
import os
from pathlib import Path
from itertools import product
from typing import Dict, Optional

import re
import subprocess

from ..Languages import Language, LANGS
from ..Loggers import Logger
from . import Viewer, ViewerAction


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
    
    def write(self, *args, from_logger: Optional[Logger]=None, **kwargs) -> None:
        """
        Write the various README's based on answer data
        """
        if from_logger is None:
            return
        
        year_stars: Dict[int, Dict[Language, int]] = defaultdict(lambda: defaultdict(int))
        
        for lang in LANGS:
            for (year, day), part in product(lang.ran, [1, 2]):
                if (day, part) == (25, 2) or not (correct_ans := from_logger.correct[year, day, part]) or not (got_ans := from_logger.data[lang, year, day, part]):
                    continue

                year_stars[year][lang] += got_ans == correct_ans

        total_stars = 0
        for year, year_data in year_stars.items():
            year_stars = max(year_data.values())
            if year_stars == 49:
                year_stars += 1

            total_stars += year_stars

            self.print(f"Writing {year} README(s)")
            for lang, lang_year_stars in year_data.items():
                lang_title = str(lang).title()
                self.print(f"Writing {lang_title} README")
                with open(Path(os.getcwd(), str(year), str(lang), "README.md"), "w") as f:
                    f.write(self.fill_in_template(self.templates["language"], **vars()))
            
            with open(Path(os.getcwd(), str(year), "README.md"), "w") as f:
                f.write(self.fill_in_template(self.templates["year"], **vars()))

        self.print("Writing top-level README")
        with open(Path(os.getcwd(), "README.md"), "w") as f:
            f.write(self.fill_in_template(self.templates["overall"], **vars()))

    ### Other Helper Functions
    def fill_in_template(self, template: str, **kwargs) -> str:
        """
        Fill in the template with the arguments and variables.

        Looks for the key in the arguments, variables, and global functions, in that order.
        """
        filled_in = template[:]
        match_regex = re.compile(r"(?P<replace>#{\((?P<parameter_name>\w+?)\)})")

        for key_match in match_regex.finditer(template):
            context = key_match.group()
            parameter_name = key_match.group("parameter_name")
            replace_str = key_match.group("replace")
            
            if hasattr(self, parameter_name):
                # Key is a variable or function in this class
                if callable(vars(self)[parameter_name]):
                    replace_with = getattr(self, parameter_name)()
                else:
                    replace_with = str(getattr(self, parameter_name))
            else:
                # This will raise an error if the key is not a defined variable or a function in the global scope
                try:
                    if callable(globals()[parameter_name]):
                        replace_with = globals()[parameter_name]()
                    else:
                        replace_with = str(globals()[parameter_name])
                except KeyError:
                    raise KeyError(f"No way to fill template key: {parameter_name}")
            
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

def git_username(self, *args, **kwargs) -> str:
    return re.search(r"user\.name=(.+)", subprocess.run(["git", "config", "--list"], capture_output=True, text=True).stdout).group(1).strip()

def submod_repos(self, *args, **kwargs) -> str:
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