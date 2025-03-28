"""
Viewer class for Advent of Code
"""

import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml
from matplotlib import colormaps, colors

from ..Languages import LANGS, get_released
from ..Loggers import LOGGERS, Logger
from ..subclass_container import SubclassContainer

__all__ = ["Viewer", "ViewerAction", "VIEWERS"]


COLOR_MAP = colormaps["tab10"]


def map_to_entity_path(entity_path: list[Any]) -> str:
    """
    Convert a list of entities to an entity path
    """
    entity_path = list(map(str, entity_path))
    if not entity_path or not entity_path[0].startswith("+"):
        entity_path = [""] + entity_path
    return "/".join(map(str, entity_path))


class ViewerAction(argparse.Action):
    """
    Action to instantiate a viewer class and add it to the viewers list
    """

    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        VIEWERS[self.type] = self.type(namespace)
        if len(values) and hasattr(values[0], "args"):
            VIEWERS[self.type].verbose = True


@dataclass
class Viewer(ABC):
    """
    Abstract class for a viewer
    """

    args: argparse.Namespace
    colormap: Dict = field(default_factory=dict)
    name: str = "viewer"
    verbose: bool = field(init=False)

    def __post_init__(self):
        self.started = True
        if isinstance(self.args, argparse.Namespace):
            self.verbose = vars(self.args).get("verbose", False)

    # Default methods
    def __enter__(self) -> "Viewer":
        """
        Context manager entry point
        """
        self.print(f"Setting up")
        self.attach_viewer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Context manager exit point
        """
        if exc_type:
            print(exc_val)
            print(exc_tb)
            return False

        self.print(f"Finished")
        return True

    def __lt__(self, other: object) -> bool:
        other_name = getattr(other, "name", "")
        if not other_name:
            return True

        return self.name < other_name

    def print(self, *args, **kwargs) -> None:
        """
        Print if verbose
        """
        if self.verbose:
            print(f"{self.name.title()} Viewer:", *args, **kwargs)

    def attach_viewer(self) -> None:
        """
        Attach the viewer to the loggers
        """
        for fpath in vars(self.args).get(f"{self.name}_attachments", []):
            assert (
                fpath.exists()
            ), f"{self.name.title()} Viewer config file {fpath} does not exist"
            with open(fpath, "r") as f:
                viewer_config = yaml.safe_load(f)

            logger_check = lambda item: item[0] in LOGGERS

            for logger_name, to_attach in filter(logger_check, viewer_config.items()):
                if not getattr(LOGGERS[logger_name], "started", False):
                    continue

                for event, to_call in to_attach.items():
                    callables = getattr(LOGGERS[logger_name], event)
                    for x in to_call:
                        func = getattr(self, x)
                        if func not in callables:
                            callables.append(func)
                    setattr(LOGGERS[logger_name], event, callables)

            self.configure_viewer(dict(filter(lambda i: not logger_check(i), viewer_config.items())))

    def configure_viewer(self, viewer_config: Dict[str, Any]) -> None:
        """
        Configure the viewer with the provided config
        """
        for var_name, val in viewer_config.items():
            if hasattr(self, var_name):
                setattr(self, var_name, val)
            else:
                raise ValueError(f"{self.name} viewer has no attribute {var_name}")

    def view(self, *args, from_logger: Optional[Logger] = None, **kwargs):
        """
        Default viewing function\\
        Can attach to answer or runtime logger\\
        """
        assert from_logger is not None, "Must provide the logger that logged the data"
        varname = from_logger.value_key
        val = kwargs.get(varname, None)
        assert val is not None, f"Value for {varname} must be provided"

        new_kwargs = dict(filter(lambda x: x[0] != "lang", kwargs.items()))
        new_kwargs["from_logger"] = from_logger

        entity_path = args
        self.print(
            f"{val} from {from_logger.name} sent to {map_to_entity_path(entity_path)}"
        )

        if len(entity_path) == 4:
            self.view_part(*args, **new_kwargs)
        elif len(entity_path) == 3:
            if entity_path[-1] == kwargs["lang"]:
                self.view_day(*args, **new_kwargs)
            else:
                self.view_year(*args, **new_kwargs)
        else:
            raise ValueError(f"Unknown entity path: {map_to_entity_path(entity_path)}")

    ### Helper functions for viewing
    def check_intypes(self, seq, data) -> Tuple[List, List]:
        """
        Check that the sequence and data are of the length
        """
        iter_type = lambda t: isinstance(t, Iterable) and not isinstance(t, str)
        seq_type = iter_type(seq)
        assert (
            not iter_type(data) ^ seq_type
        ), "Data and sequence must be both iterable or both non-iterable"
        if seq_type:
            assert len(seq) == len(data), "Data and sequence must be the same length"
            seq = list(seq)
            data = list(data)
        else:
            seq = [seq]
            data = [data]

        return seq, data

    def entity_color(
        self, entity_path: List[str]
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Set the color of the entity based on the last part of the path that has a color
        """
        ### Assemble the current entity colors
        entity_path = list(map(str, entity_path))
        for i, l in enumerate(LANGS):
            self.colormap[str(l)] = COLOR_MAP(i % COLOR_MAP.N)

        for i, y in enumerate(sorted(get_released())):
            self.colormap[str(y)] = COLOR_MAP(i % COLOR_MAP.N)

        # Get the color of the last part of the entity path that has a color
        for p in entity_path[::-1]:
            if p in self.colormap:
                if "avg" in entity_path:
                    return colors.to_rgba(self.colormap[p], alpha=0.5)
                return colors.to_rgba(self.colormap[p])


VIEWERS = SubclassContainer(Viewer, __all__, Path(__file__).parent)
