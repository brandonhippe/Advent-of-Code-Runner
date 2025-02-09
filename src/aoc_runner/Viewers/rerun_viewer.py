"""
Rerun viewer for profiled AOC code
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import rerun as rr

from ..Languages import Language, get_released
from ..Loggers import Logger
from . import Viewer, ViewerAction, map_to_entity_path
from .blueprints import DEFAULT_BLUEPRINT_DIR, BlueprintMaker


@dataclass
class RecordingWithInitialized:
    """
    Recording stream with initialized entities
    """
    args: argparse.Namespace
    application_id: str
    uuid: uuid4 = field(default_factory=uuid4)
    initialized_entities: set[str] = field(default_factory=set)
    recording: rr.RecordingStream = field(init=False)

    def __post_init__(self):
        self.recording = rr.script_setup(
            self.args, application_id=self.application_id, recording_id=self.uuid
        )

    def __call__(self, entity_path: str | List[Any]) -> bool:
        """
        Initialize an entity path for logging, if not already initialized
        """
        if not self.recording:
            self.recording = rr.get_global_data_recording()

        if isinstance(entity_path, list):
            entity_path = map_to_entity_path(entity_path)

        if entity_path not in self.initialized_entities:
            self.initialized_entities.add(entity_path)
            return True
        return False


@dataclass
class RerunViewer(Viewer):
    """
    Displays Advent of Code solutions in a rerun viewer
    """
    application_id: str = "Advent of Code"
    bar_graph_data: Dict = field(
        default_factory=lambda: defaultdict(
            lambda: defaultdict(lambda: {y: 0 for y in get_released()})
        )
    )
    blueprint_maker: BlueprintMaker = field(
        default_factory=lambda: BlueprintMaker(False)
    )
    name: str = "rerun"
    last_start_event: str = None

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        """
        Add arguments to the parser
        """
        parser.add_argument(
            "--rerun",
            action=ViewerAction,
            nargs="*",
            help='Run the rerun viewer. Add " verbose" to run in verbose mode',
            type=RerunViewer,
        )
        parser.add_argument(
            "--rerun-attachments",
            nargs="*",
            default=[Path(Path(__file__).parent, "rerun.yml")],
            help="Path to yaml file(s) that define the attachments for the Rerun Viewer",
        )

        blueprint_args = parser.add_mutually_exclusive_group()
        blueprint_args.add_argument(
            "--default-blueprint",
            type=str,
            default=Path(DEFAULT_BLUEPRINT_DIR, "main.yml"),
            help="Path to yaml that defines the base level blueprint",
        )
        blueprint_args.add_argument(
            "--no-blueprint", action="store_true", help="Don't load any blueprints"
        )

        rr.script_add_args(parser)

    def start_viewer(self, *args, event: str = "init", **kwargs):
        """
        Start the rerun viewer
        """
        if not self.last_start_event or self.last_start_event != event:
            self.active_recording = RecordingWithInitialized(
                self.args, application_id=self.application_id
            )
            rr.set_time_sequence("Day", 0, recording=self.active_recording.recording)
            self.last_start_event = event

    ### Context manager functions
    def __enter__(self):
        super().__enter__()
        self.blueprint_maker.no_load = self.args.no_blueprint
        self.start_viewer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Exit, spawning the rerun viewer if no errors occurred
        """
        super().__exit__(exc_type, exc_val, exc_tb)
        rr.script_teardown(self.args)
        return bool(exc_type)

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
        if not time:
            return

        for y, t in zip(*self.check_intypes(year, time)):
            self.bar_graph_data[plot][lang][y] = t

        data = list(
            map(
                lambda x: x[1],
                sorted(self.bar_graph_data[plot][lang].items(), key=lambda x: x[0]),
            )
        )
        self.bar_log([lang, plot], data, **kwargs)

    def view_day(
        self,
        year: int,
        day: int,
        lang: Language,
        *args,
        time: float | List[float] = [],
        max_time: Optional[float] = None,
        **kwargs,
    ) -> None:
        """
        View the runtime data for a day
        """
        # super().view_day(year, day, lang, *args, time=time, max_time=max_time, **kwargs)
        if not time:
            return

        if max_time or self.active_recording([lang]):
            rr.send_blueprint(
                self.blueprint_maker(
                    self.args.default_blueprint, recent_lang=lang, **kwargs
                ),
                recording=self.active_recording.recording,
            )
        self.series_line_log([lang, year], time, "Day", day, recent_lang=lang, **kwargs)

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
        if not time:
            return

        if self.active_recording([lang]):
            rr.send_blueprint(
                self.blueprint_maker(
                    self.args.default_blueprint, recent_lang=lang, **kwargs
                ),
                recording=self.active_recording.recording,
            )
        self.series_line_log(
            [lang, f"part{part}", year], time, "Day", day, recent_lang=lang, **kwargs
        )

    def view_table(self, *args, from_logger: Logger, **kwargs):
        """
        View a table of data
        """
        text = from_logger.data(["Language", "Year", "Day", "Part"], style="MARKDOWN", logger_name=from_logger.name)
        self.text_log(
            [from_logger.name],
            text,
            from_logger=from_logger,
            media_type=rr.MediaType.MARKDOWN,
        )

    ### Actual rerun logging functions
    def clear_log(self, entity_path: List[str], recursive: bool = False, **kwargs):
        """
        Clear a log
        """
        log_name = map_to_entity_path(entity_path)

        rr.log(
            log_name,
            rr.Clear(recursive=recursive),
            recording=self.active_recording.recording,
        )

    def series_line_log(
        self,
        entity_path: List[str],
        data: float | List[float],
        seq_str: str,
        seq: int | List[int],
        **kwargs,
    ):
        """
        Log a value as a part of a time series line
        """
        assert type(data) != type(seq) or len(data) == len(
            seq
        ), "Data and sequence must be the same length"

        log_name = map_to_entity_path(entity_path)

        extras = {
            "width": rr.components.StrokeWidth(5),
            "name": str(entity_path[-1]).title(),
            "aggregation_policy": rr.components.AggregationPolicy.Off,
        }
        if color := self.entity_color(entity_path):
            extras["color"] = rr.components.Color(color)

        if self.active_recording(entity_path):
            rr.log(
                log_name,
                rr.SeriesLine(**extras),
                recording=self.active_recording.recording,
                static=True,
            )

        if isinstance(data, list):
            rr.disable_timeline(seq_str, recording=self.active_recording.recording)
            rr.send_columns(
                log_name,
                times=[rr.TimeSequenceColumn(seq_str, seq)],
                components=[rr.components.ScalarBatch(data)],
                recording=self.active_recording.recording,
            )
        else:
            rr.set_time_sequence(
                seq_str, seq, recording=self.active_recording.recording
            )
            rr.log(log_name, rr.Scalar(data), recording=self.active_recording.recording)

        rr.set_time_sequence(seq_str, 0, recording=self.active_recording.recording)

    def series_point_log(
        self,
        entity_path: List[str],
        data: float,
        seq_str: str,
        seq: int,
        marker_size: int = 5,
        **kwargs,
    ):
        """
        Log a value as a part of a time series with points
        """
        log_name = map_to_entity_path(entity_path)

        if self.active_recording(entity_path):
            self.clear_log(entity_path)

        rr.set_time_sequence(seq_str, seq, recording=self.active_recording.recording)
        rr.log(
            log_name,
            rr.Scalar(data),
            rr.SeriesPoint(
                color=self.entity_color(entity_path),
                marker="Circle",
                marker_size=marker_size,
                **kwargs,
            ),
            recording=self.active_recording.recording,
        )
        rr.set_time_sequence(seq_str, 0, recording=self.active_recording.recording)

    def bar_log(self, entity_path: List[str], data: List[float], **kwargs):
        """
        Log a set of values as a bar chart
        """
        if len(data) < 2:
            return

        log_name = map_to_entity_path(entity_path)

        extras = []
        if color := self.entity_color(entity_path):
            extras.append(rr.components.Color(color))

        if self.active_recording(entity_path):
            self.clear_log(entity_path)
        rr.log(
            log_name,
            rr.BarChart(data),
            extras,
            recording=self.active_recording.recording,
        )

    def text_log(
        self,
        entity_path: List[str],
        text: str | List[str],
        from_logger: Logger,
        **kwargs,
    ):
        """
        Log some text
        """
        log_name = map_to_entity_path(entity_path)
        self.clear_log(entity_path)
        if self.active_recording(entity_path):
            rr.send_blueprint(
                self.blueprint_maker(
                    self.args.default_blueprint, from_logger=from_logger, **kwargs
                ),
                recording=self.active_recording.recording,
            )

        if isinstance(text, list):
            text = "\n".join(text)
        rr.log(
            log_name,
            rr.TextDocument(text, **kwargs),
            recording=self.active_recording.recording,
        )
