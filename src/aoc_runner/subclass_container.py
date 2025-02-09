import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass
class SubclassContainer:
    """
    Class to hold all subclasses of a type.
    """

    par_type: type
    par_all: list
    par_dir: Path
    init: bool = False
    subclasses: Dict[str, type] = field(init=False)

    def __post_init__(self) -> None:
        self.subclasses = {}
        for filename in filter(
            lambda f: f.endswith(".py") and f != "__init__.py",
            sorted(os.listdir(self.par_dir)),
        ):
            filename = filename[:-3]
            class_name = "".join(map(lambda s: s.title(), filename.split("_")))
            modname = f"aoc_runner.{self.par_dir.stem}.{filename}"
            importlib.import_module(modname)

            if hasattr(sys.modules[modname], class_name) and issubclass(
                getattr(sys.modules[modname], class_name), self.par_type
            ):
                self.subclasses[class_name] = getattr(sys.modules[modname], class_name)
                if (
                    self.init
                ):
                    self.subclasses[class_name] = self.subclasses[class_name]()
                self.par_all.append(class_name)
                del modname

    def __getitem__(self, key: str | type) -> type:
        return self.subclasses[self.conv_key(key)]

    def __setitem__(self, key: str | type, value: type) -> None:
        self.subclasses[self.conv_key(key)] = value

    def __iter__(self):
        return iter(self.subclasses.values())

    def __contains__(self, key: str | type) -> bool:
        return self.conv_key(key) in self.subclasses

    def __call__(self, *args, **kwargs) -> list[type]:
        defaults, started = {}, {}
        for k, v in self.subclasses.items():
            if vars(v).get("started", False):
                started[k] = v
            elif vars(v).get("default", False):
                defaults[k] = v

        if len(started):
            self.subclasses = started
        else:
            self.subclasses = {k: v(*args, **kwargs) for k, v in defaults.items()}

        return list(self.subclasses.values())

    def __len__(self) -> int:
        return len(self.subclasses)

    def index(self, key: str | type) -> int:
        return list(self.subclasses.keys()).index(self.conv_key(key))

    def conv_key(self, key: str | type) -> str:
        if not isinstance(key, str):
            assert issubclass(
                key, self.par_type
            ), f"{key} is not a valid {self.par_type}"
            key = key.__name__
        return key
