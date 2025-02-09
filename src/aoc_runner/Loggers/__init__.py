"""
Logger class for Advent of Code
"""

import argparse
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import reduce
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from .. import BASE_DIR
from ..Languages import LANGS
from ..subclass_container import SubclassContainer
from ..data_tracker import DataTracker

__all__ = ["Logger", "LoggerAction", "LOGGERS"]


class LoggerAction(argparse.Action):
    """
    Action to instantiate a logger class and add it to the loggers list
    """

    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        LOGGERS[self.type] = self.type(namespace)
        if len(values) and hasattr(values[0], "args"):
            LOGGERS[self.type].verbose = True


@dataclass
class Logger(ABC):
    args: argparse.Namespace
    name: str = "logger"
    table_style: str = "DEFAULT"
    new_data: List[Tuple[Tuple, Dict]] = field(default_factory=list)
    post_load: List[Callable] = field(default_factory=list)
    on_log: List[Callable] = field(default_factory=list)
    pre_exit: List[Callable] = field(default_factory=list)
    on_exit: List[Callable] = field(default_factory=list)
    post_exit: List[Callable] = field(default_factory=list)
    value_key: str = "value"
    verbose: bool = False
    data: DataTracker = field(init=False)
    data_prefix: str = ""
    data_yaml_path: Path = field(init=False)

    def __post_init__(self):
        self.started = True
        if isinstance(self.args, argparse.Namespace):
            self.verbose = vars(self.args).get("verbose", False)
            # self.data_yaml_path = Path(Path(__file__).parent, "_".join(filter(None, (self.name, self.data_prefix, "data.yml"))))
            self.data_yaml_path = Path(BASE_DIR, "_".join(filter(None, (self.name, self.data_prefix, "data.yml"))))

    def __hash__(self):
        return hash(self.name)

    # Default methods
    def __enter__(self) -> "Logger":
        """
        Context manager entry point
        """
        if style := vars(self.args).get(f"{self.name}_table_style", None):
            self.table_style = style
        
        self.print(f"Setting up")
        self.load_data()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Context manager exit point
        """
        if exc_type:
            print(exc_val)
            print(exc_tb)
            return False

        for func in self.pre_exit:
            func(from_logger=self, event="pre_exit", verbose=self.verbose)

        self.print(f"Finished logging")

        for var in filter(lambda v: v != self.data and issubclass(type(v), DataTracker) and len(v), vars(self).values()):
            p_verbose, self.verbose = self.verbose, True
            self.print("\n" + var(["Language", "Year", "Day", "Part"], style=self.table_style, logger_name=self.name) + "\n")
            self.verbose = p_verbose

        self.log(log_all=True, callables=self.on_exit)
        self.save_data()

        for func in self.post_exit:
            func(from_logger=self, event="post_exit", verbose=self.verbose)

        return True

    def log(self, *args, callables: Optional[List[Callable]] = None, **kwargs) -> None:
        """
        Log a message
        """
        if callables is None:
            callables = self.on_log

        for new_args, new_kwargs in sorted(
            self.new_data, key=lambda d: tuple(map(len, d)), reverse=True
        ):
            for k, v in kwargs.items():
                if k not in new_kwargs:
                    new_kwargs[k] = v
            
            new_kwargs["event"] = new_kwargs.get("event", "on_log")

            for func in callables:
                func(*new_args, from_logger=self, verbose=self.verbose, **new_kwargs)

        self.new_data = []

    def __call__(self, *args, **kwargs) -> Dict[str, Any]:
        dumping = {}
        for name, tracker in vars(self).items():
            if not issubclass(type(tracker), DataTracker) or not tracker.dump_this:
                continue

            data = dumping.get(name, {})
            for year, day in self.runtime_days():
                data[year] = data.get(year, {})
                data[year][day] = data[year].get(day, {})

                for part in [1, 2]:
                    for lang in filter(lambda l: [l, year, day, part] in tracker, LANGS):
                        data[year][day][part] = data[year][day].get(part, {})
                        data[year][day][part][str(lang)] = tracker[
                            lang, year, day, part
                        ]

            dumping[name] = data

        return dumping

    def __lt__(self, other: object) -> bool:
        if other_name := getattr(other, "name", ""):
            return self.name < other_name

        return True

    def print(self, *args, **kwargs) -> None:
        """
        Print if verbose
        """
        if self.verbose:
            print(f"\n{self.name.title()} Logger:", *args, **kwargs)

    def load_data(self) -> None:
        """
        Load logger data
        """
        def log_dict(d: dict, value_key: str, keys: List[Any] = []) -> None:
            for k, v in d.items():
                if isinstance(v, dict):
                    log_dict(v, value_key, keys + [k])
                elif k.title() in LANGS and len(keys) == 3:
                    LANGS[k.title()].add_part(*keys, **{value_key: v}, loggers=[self], event="on_load")


        if vars(self.args).get("no_load", False) or not os.path.exists(self.data_yaml_path):
            return

        self.print("Loading data")

        with open(self.data_yaml_path, "r") as f:
            if data := yaml.safe_load(f):
                for v in data.values():
                    log_dict(v, self.value_key)

        self.print("Data loaded")
        self.print(self.data(["Language", "Year", "Day", "Part"], style=self.table_style))
        
        for func in self.post_load:
            func(from_logger=self, event="post_load", verbose=self.verbose)

    def save_data(self) -> None:
        """
        Save logger data
        """
        if vars(self.args).get("no_save", False):
            return

        self.print("Saving data")
        self.print(self.data(["Language", "Year", "Day", "Part"], style=self.table_style))

        with open(self.data_yaml_path, "w") as f:
            yaml.safe_dump(self(), f)

        self.print("Data saved")

    def add_new_data(self, *args, **kwargs) -> None:
        """
        Add new data to the logger
        """
        self.new_data.append((args, kwargs))

    def runtime_days(self, new_only: bool = False) -> List[Tuple[int, int]]:
        return sorted(
            reduce(
                lambda a, b: a | b,
                map(lambda l: l.changed if new_only else l.ran, LANGS),
                set(),
            )
        )

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add arguments to the parser. Must be a static method
        """
        pass


LOGGERS = SubclassContainer(Logger, __all__, Path(__file__).parent)
