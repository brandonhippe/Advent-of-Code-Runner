import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import rerun as rr
import rerun.blueprint as rrb
import yaml

from ...Languages import LANGS, Language
from ...Loggers import LOGGERS, Logger
from ...Viewers import map_to_entity_path

__all__ = ["BlueprintMaker", "DEFAULT_BLUEPRINT_DIR"]


DEFAULT_BLUEPRINT_DIR = Path(__file__).parent


@dataclass
class BlueprintMaker:
    """
    Class to handle making blueprints
    """

    no_load: bool
    blueprint_dir: Path = DEFAULT_BLUEPRINT_DIR
    blueprint_yamls: Dict[str, Dict] = field(default_factory=dict)
    scale_factor: float = 1.1

    def __call__(self, filepath: Path, **kwargs) -> Optional[rrb.BlueprintLike]:
        """
        Load a blueprint from yaml file for the rerun viewer
        """
        if self.no_load:
            return rrb.Blueprint()

        if str(filepath) not in self.blueprint_yamls:
            # self.print(f"Loading blueprint from {filepath}")
            with open(filepath) as f:
                self.blueprint_yamls[str(filepath)] = yaml.safe_load(f)

        assert issubclass(
            type(
                bp := self.construct_bp(
                    deepcopy(self.blueprint_yamls[str(filepath)]), **kwargs
                )
            ),
            rrb.BlueprintLike,
        ), f"Blueprint {filepath} does not make a valid blueprint"
        return bp

    def construct_bp(
        self, iter: Iterable, *args, **kwargs
    ) -> rrb.BlueprintLike | Iterable:
        """
        Construct a blueprint from an iterable
        """
        if not isinstance(iter, Iterable):
            return iter

        # Construct based on type (str or dict)
        if func := getattr(self, f"construct_{type(iter).__name__.lower()}", False):
            return func(iter, *args, **kwargs)

        return_list = []
        for i in iter:
            v = self.construct_bp(i, **kwargs)
            if isinstance(v, (list, set, tuple)):
                return_list.extend(v)
            else:
                return_list.append(v)

        return return_list

    def construct_str(self, iter: str, *args, **kwargs) -> rrb.BlueprintLike | Iterable:
        iter = self.regex_replace(iter, **kwargs)
        type_instantiator, include_passed_args = self.get_instantiator(iter)
        if type_instantiator:
            if include_passed_args:
                return type_instantiator(*args, **kwargs)
            else:
                return type_instantiator()
        return iter

    def construct_dict(
        self, iter: Dict, *args, **kwargs
    ) -> rrb.BlueprintLike | Iterable:
        return_dict = {}
        return_list = []

        for k, v in iter.items():
            del_key = None
            if isinstance(v, dict) and "del_key" in v:
                del_key = v["del_key"]
                del v["del_key"]

            v = self.construct_bp(v, **kwargs)
            type_instantiator, include_passed_args = self.get_instantiator(k)
            if type_instantiator:
                if del_key is None:
                    del_key = True
                new_args = []
                new_kwargs = {}

                if include_passed_args:
                    new_args = list(args[:])
                    new_kwargs = kwargs.copy()

                if isinstance(v, (list, set, tuple)):
                    for v1 in v:
                        if isinstance(v1, dict):
                            new_kwargs.update(v1)
                        else:
                            new_args.append(v1)
                elif isinstance(v, dict):
                    new_kwargs.update(v)
                else:
                    new_args.append(v)

                v = type_instantiator(*tuple(new_args), **new_kwargs)

            if del_key:
                if isinstance(v, (list, set, tuple)):
                    return_list.extend(v)
                elif isinstance(v, dict):
                    return_list.extend(v.values())
                else:
                    return_list.append(v)
            else:
                return_dict[k] = v

        if return_list and return_dict:
            return return_list + [return_dict]
        elif return_list:
            if len(return_list) == 1:
                return return_list[0]
            else:
                return return_list
        elif return_dict:
            return return_dict

    ### Helpers
    def get_instantiator(self, k: str) -> Tuple[Optional[Callable], bool]:
        check_mods = [rr, rrb, rrb.components, rrb.views, rrb.archetypes]
        for mod in check_mods:
            m = getattr(mod, k, False)
            if isinstance(m, Callable):
                return m, False

        m = getattr(self, k, False)
        if isinstance(m, Callable):
            return m, True
        return None, True

    def regex_replace(self, k: str, **kwargs):
        regex_match = re.search(r"\$\{(.+?)\}", k)
        if not regex_match:
            return k

        name = regex_match.group(1)
        if name in kwargs:
            return f"{k[:regex_match.start()]}{kwargs[name]}{k[regex_match.end():]}"

        type_instantiator = self.get_instantiator(k)
        if type_instantiator:
            return type_instantiator()

        return k

    def get_language_views(
        self, path: Path = "", bp_dir: bool = False, **kwargs
    ) -> rrb.BlueprintLike | Iterable:
        """
        Generate blueprint views for all languages
        """
        if bp_dir:
            path = Path(self.blueprint_dir, path)

        views = {}
        for lang in LANGS:
            if not len(lang):
                continue

            views[lang] = self(path, lang=lang, lang_title=str(lang).title(), **kwargs)

        if not views:
            views = [
                rrb.TextDocumentView(
                    origin="/", name="No languages found", contents="+ $origin/no-langs"
                )
            ]
        return views

    def get_languages_list(
        self, path_ext: List[str], **kwargs
    ) -> rrb.BlueprintLike | Iterable:
        """
        Generate a list of entity paths for all languages
        """
        return [
            map_to_entity_path(["+ $origin", lang] + path_ext)
            for lang in filter(lambda l: len(l), LANGS)
        ]

    def get_logger_views(
        self, path: Path = "", bp_dir: bool = False, **kwargs
    ) -> rrb.BlueprintLike | Iterable:
        """
        Generate blueprint views for all loggers
        """
        if bp_dir:
            path = Path(self.blueprint_dir, path)

        views = []
        for logger in LOGGERS:
            views.append(self(Path(path, f"{logger.name}.yml"), **kwargs))

        return views

    def get_range(
        self, lang: Optional[Language] = None, **kwargs
    ) -> Tuple[float, float]:
        """
        Get the range of a log
        """
        logger = LOGGERS["RuntimeLogger"]
        max_time = logger.max_time[lang] * self.scale_factor
        min_time = logger.max_time[lang] - max_time
        return min_time, max_time

    def get_active_tab(self, *args, **kwargs) -> int | str:
        """
        Get the active tab
        """
        if not len(args):
            return 0

        val = kwargs.get(args[0], 0)
        if isinstance(val, int):
            return val

        if isinstance(val, str):
            return val

        if isinstance(val, Language):
            return list(filter(lambda l: len(l), LANGS)).index(val)

        if isinstance(val, Logger):
            return list(LOGGERS).index(val)

        raise NotImplementedError(f"Active tab not implemented for {type(val)}")
