"""
Runtime logger for Advent of Code
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from heapq import nlargest
from typing import Any, Hashable, Optional, Tuple, Dict, List

from ..Languages import LANGS, Language
from . import Logger, LoggerAction, DataTracker


@dataclass
class RuntimeTracker(DataTracker):
    """
    Track runtime data
    """

    total: float = 0
    average: float = 0

    def __call__(self, index_labels: List[str], style: str="DEFAULT", **kwargs) -> str:
        self.longest_runtimes()
        return super().__call__(index_labels, style, **kwargs)

    def update(self):
        self.total = sum(
            v if isinstance(v, float) else v.total for v in self.data.values()
        )
        self.average = self.total / len(self.data)
    
    def keys_to_indecies(self, keys: List[Hashable]) -> Optional[Tuple[List[str], List[Any], int]]:
        *keys, k = keys
        if "longest" in keys:
            if isinstance(k, tuple):
                col_name = "time"
                row_indecies = k
                tab_name = keys[-1]
            else:
                return
        elif len(keys) < 2:
            col_name = str(k)
            tab_name = f"Data"
            row_indecies = keys
        else:
            if len(keys) == 3 and k == "average":
                return
            
            col_name, tab_name, *row_indecies = keys[-3:] + [k]

        if isinstance(k, tuple):
            return (col_name, tab_name, *row_indecies), (False, False, True, slice(1, None)), 0
        else:
            return (col_name, tab_name, *row_indecies), (True, True, False, slice(None)), len(keys)

    def longest_runtimes(
        self, n_longest=10
    ) -> None:
        longest_arr = []
        def find_times(d: Dict[Hashable, Any], keys: List[Hashable]=[]) -> None:
            for k, v in list(d.items()):
                if isinstance(v, dict):
                    find_times(v, keys + [k])
                elif isinstance(v, type(self)):
                    if len(keys) == 2:
                        longest_arr.append((v.total, keys + [k]))
                    else:
                        find_times(v.data, keys + [k])
                elif isinstance(v, float):
                    longest_arr.append((v, keys + [k]))
                else:
                    raise TypeError("Unexpected data type")
                
        find_times(self.data)

        longest_data = nlargest(n_longest, longest_arr, key=lambda x: x[0])
        self.longest = RuntimeTracker(False)
        for i, (k, v) in enumerate(longest_data):
            self.longest.add_data(((i, *v),), new_data=k)

        # for year, day in self.runtime_days():
        #     for lang in LANGS:
        #         if [lang, year, day] not in self.data:
        #             continue
        #         for part in [1, 2]:
        #             if [lang, year, day, part] in self.data:
        #                 longest_arr.append(
        #                     (
        #                         self.data[lang, year, day, part],
        #                         (year, day, part, lang),
        #                     )
        #                 )

@dataclass
class RuntimeLogger(Logger):
    """
    Runtime logger for Advent of Code
    """

    data: RuntimeTracker = field(default_factory=RuntimeTracker)
    max_time: Dict[Language, float] = field(default_factory=lambda: defaultdict(float))
    min_time: Dict[Language, float] = field(
        default_factory=lambda: defaultdict(lambda: float("inf"))
    )
    name: str = "runtimes"
    value_key: str = "time"
    table_style: str = "DOUBLE_BORDER"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """
        Add arguments to the parser
        """
        parser.add_argument(
            "--runtimes",
            "-r",
            action=LoggerAction,
            nargs="*",
            help='Log runtimes. Add " verbose" or "v" to run in verbose mode',
            type=RuntimeLogger,
        )
        parser.add_argument(
            "--no-load",
            action="store_true",
            help="Don't load existing advent of code data",
        )
        parser.add_argument(
            "--no-save", action="store_true", help="Don't save advent of code data"
        )
        parser.add_argument(
            "--runtimes-table-style", type=str, choices=["DEFAULT", "SINGLE_BORDER", "DOUBLE_BORDER"], help="Style of the answer table"
        )

    ### Context manager functions
    def __enter__(self):
        # Load correct answers
        super().__enter__()
        self.changed_data = RuntimeTracker(False)
        return self

    ### Logging helper functions
    def log(self, *args, **kwargs) -> None:
        """
        Log a runtime
        """

        def prep_dict_log(d: Dict, *args) -> None:
            if not any(isinstance(v, dict) for v in d.values()):
                x_data = sorted(d.keys())
                y_data = [d[k] for k in x_data]
                if len(args) == 3:
                    if isinstance(args[2], int):
                        self.add_new_data(
                            args[1],
                            x_data,
                            args[2],
                            args[0],
                            lang=args[0],
                            **{self.value_key: y_data},
                        )
                    else:
                        self.add_new_data(
                            args[1],
                            x_data,
                            args[0],
                            lang=args[0],
                            **{self.value_key: y_data},
                        )
                elif len(args) == 2:
                    self.add_new_data(
                        x_data,
                        args[0],
                        args[1],
                        lang=args[0],
                        **{self.value_key: y_data},
                    )

                return

            for k, v in d.items():
                if isinstance(v, dict):
                    prep_dict_log(d[k], *args, k)
                else:
                    pass

        if not kwargs.get("log_all", False):
            self.log_part(*args, **kwargs)
        else:
            data = defaultdict(lambda: defaultdict(dict))
            for lang in LANGS:
                for year, day in filter(lambda yd: [lang, *yd] in self.data, self.runtime_days(new_only=False)):
                    if year not in data[lang]:
                        data[lang][year] = defaultdict(
                            lambda: defaultdict(dict), {"combined": {}}
                        )

                    for part in range(1, 3):
                        if [lang, year, day, part] in self.data:
                            data[lang][year][part][day] = self.data[
                                lang, year, day, part
                            ]

                    if len(self.data[lang, year]) // 2 > 1:
                        data[lang]["avg"][year] = self.data[lang, year].average
                    if len(self.data[lang, year]) // 2 == 25:
                        data[lang]["tot"][year] = self.data[lang, year].total
                    if len(self.data[lang, year, day]) == 2:
                        data[lang][year]["combined"][day] = self.data[
                            lang, year, day
                        ].total

            prep_dict_log(data)

        super().log(*args, **kwargs)

    def log_part(
        self,
        year: int,
        day: int,
        part: int,
        lang: Optional[Language] = None,
        time: Optional[float] = None,
        event: Optional[str]="on_log",
        **kwargs,
    ) -> None:
        """
        Log the runtime data for a part
        """
        if time is None:
            return

        if not all((lang, year, day, part)):
            raise ValueError(
                "Language, year, day, and part must be provided for runtime logging"
            )
        
        if event == "on_log":
            self.changed_data.add_data((lang, year, day, part), new_data=time)
        self.data.add_data((lang, year, day, part), new_data=time)

        args = [year, day, part]
        while len(args):
            t = self.data[[lang, *args]]
            if len(args) == 3:
                self.add_new_data(*args, lang, time=t)
                if t < self.min_time[lang]:
                    self.min_time[lang] = t
                    self.new_data[-1][-1]["min_time"] = t
            elif len(args) == 2:
                if len(t) == 2:
                    self.add_new_data(*args, lang, time=t.total)
                    if t.total > self.max_time[lang]:
                        self.max_time[lang] = t.total
                        self.new_data[-1][-1]["max_time"] = t.total
            elif len(args) == 1:
                if len(t) // 2 > 1:
                    self.add_new_data(*args, lang, "avg", time=t.average)
                if len(t) // 2 == 25:
                    self.add_new_data(*args, lang, "tot", time=t.total)

            args.pop()
