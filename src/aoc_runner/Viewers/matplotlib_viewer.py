"""
Matplotlib Viewer for profiled AOC code
"""

import argparse
import platform
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt

from ..Languages import Language
from ..Loggers import LOGGERS, Logger
from . import Viewer, ViewerAction


@dataclass
class FigureData:
    """
    Dataclass to store figure data
    """

    runtime_logger: Logger
    lang: Language = None
    fig: plt.Figure = field(init=False)
    ax: plt.Axes = field(init=False)
    year_data: Dict[str, Dict[int, float]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    scale_factor: float = 1.1

    def __post_init__(self) -> None:
        self.fig, self.ax = plt.subplots(2, 2)

    def __call__(self) -> None:
        assert self.lang, "Language must be set"
        assert self.runtime_logger, "Runtime Logger must be set"

        max_time = self.runtime_logger.max_time[self.lang]
        min_time = self.runtime_logger.min_time[self.lang]
        for (ax_y, ax_x), t in zip(
            [(0, 0), (0, 1), (1, 0)], ["Part 1", "Part 2", "Combined"]
        ):
            self.ax[ax_y][ax_x].set_ylim(
                min_time / (10**self.scale_factor), max_time * (10**self.scale_factor)
            )
            self.ax[ax_y][ax_x].set_xlim(1, 25)
            self.ax[ax_y][ax_x].set_xlabel("Day")
            self.ax[ax_y][ax_x].set_ylabel("Time (s)")
            self.ax[ax_y][ax_x].grid(True)
            self.ax[ax_y][ax_x].set_title(t)
            self.ax[ax_y][ax_x].legend()

        self.fig.suptitle(f"{self.lang} Runtimes".title())
        sums = defaultdict(float)
        set_xticks = False
        for label, data in sorted(self.year_data.items(), key=lambda x: x[0]):
            xs = sorted(data.keys())
            ys = list(map(lambda x: data[x] - sums[x], xs))
            bar = self.ax[1][1].bar(
                xs, ys, label=label, bottom=list(map(lambda x: sums[x], xs))
            )
            self.ax[1][1].bar_label(bar, fmt="%.3f")
            sums = defaultdict(float, {x: data[x] for x in xs})

            if not set_xticks:
                self.ax[1][1].set_xticks(xs)
                set_xticks = True

        self.ax[1][1].set_title("Year Total Runtimes")
        self.ax[1][1].set_xlabel("Year")
        self.ax[1][1].set_ylabel("Time (s)")
        self.ax[1][1].legend()

        if platform.system() == "Linux":
            plt.figure(self.fig.number)
            mng = plt.get_current_fig_manager()
            mng.resize(*mng.window.maxsize())
        else:
            raise NotImplementedError(
                f"Fullscreen not yet supported on {platform.system()}"
            )

    def plot_line(
        self, x: List[int], y: List[float], label: str, part: int = 0, **kwargs
    ) -> None:
        self.ax[0 if part else 1][0 if not part else part - 1].semilogy(
            x, y, label=label, **kwargs
        )

    def plot_bar(self, x: int | List[int], y: float | List[float], label: str) -> None:
        self.year_data[label].update({x: y})


@dataclass
class MatplotlibViewer(Viewer):
    """
    Matplotlib Viewer class for Advent of Code runtimes
    """

    lang_figs: Dict[Language, FigureData] = field(
        default_factory=lambda: defaultdict(
            lambda: FigureData(LOGGERS["RuntimeLogger"])
        )
    )
    name: str = "matplotlib"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """
        Add arguments to the parser. Must be a static method
        """
        parser.add_argument(
            "--matplotlib",
            action=ViewerAction,
            nargs="*",
            help='Run the matplotlib viewer. Add " verbose" to run in verbose mode',
            type=MatplotlibViewer,
        )
        parser.add_argument(
            "--matplotlib-attachments",
            nargs="*",
            default=[Path(Path(__file__).parent, "matplotlib.yml")],
            help="Path to yaml file(s) that define the attachments for the Matplotlib Viewer",
        )

    ### Context manager functions
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Context manager exit point
        """
        if super().__exit__(exc_type, exc_val, exc_tb):
            for lang, fig_data in self.lang_figs.items():
                fig_data.lang = lang
                fig_data()

            plt.show(block=True)

        return not bool(exc_type)

    def __lt__(self, _: object) -> bool:
        return False

    ### Viewing helper functions
    def view_year(
        self,
        year: int | List[int],
        lang: Language,
        plot: str,
        *args,
        time: float | List[float] = [],
        **kwargs,
    ) -> None:
        """
        View the average/total runtime data for a year
        """
        # super().view_year(year, lang, plot, *args, time=time, **kwargs)
        if not kwargs.get("log_all", False) or not isinstance(time, list) or not time:
            return

        for y, t in zip(*self.check_intypes(year, time)):
            self.lang_figs[lang].plot_bar(y, t, plot)

    def view_day(
        self,
        year: int,
        day: int,
        lang: Language,
        *args,
        time: float | List[float] = [],
        **kwargs,
    ) -> None:
        """
        View the runtime data for a day
        """
        # super().view_day(year, day, lang, *args, time=time, **kwargs)
        if not kwargs.get("log_all", False) or not isinstance(time, list) or not time:
            return

        self.lang_figs[lang].plot_line(
            day, time, str(year), color=self.entity_color([lang, year]), linewidth=2
        )

    def view_part(
        self,
        year: int,
        day: int | List[int],
        part: int,
        lang: Language,
        *args,
        time: float | List[float] = [],
        **kwargs,
    ):
        """
        View the runtime data for a part
        """
        # super().view_part(year, day, part, lang, *args, time=time, **kwargs)
        if not kwargs.get("log_all", False) or not isinstance(time, list) or not time:
            return

        self.lang_figs[lang].plot_line(
            day,
            time,
            str(year),
            part=part,
            color=self.entity_color([lang, f"part{part}", year]),
            linewidth=2,
        )
