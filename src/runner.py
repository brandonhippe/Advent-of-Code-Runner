import argparse
import os
from itertools import product
from typing import Dict, List, Tuple

from aoc_runner import (LANGS, Language, RunnerHandler, add_arguments,
                        get_released)


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    length = os.get_terminal_size().columns - 10
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()


def contiguous_groups(l: List[int]) -> List[Tuple[int, int]]:
    """
    Find the contiguous groups of numbers in a list.
    """
    l = sorted(list(set(l)))
    ranges = [(l[0], l[0])]
    for i in range(1, len(l)):
        if l[i] - l[i - 1] > 1:
            ranges[-1] = (ranges[-1][0], l[i - 1])
            ranges.append((l[i], l[i]))

    ranges[-1] = (ranges[-1][0], l[-1])
    return ranges


def run(
    language_year_days: Dict[Language, Tuple[int, int]], progressBar: bool, loggers=()
):
    year_days_langs: Dict[Tuple[Tuple[int, int],], List[Language]] = {
        tuple(sorted(list(year_days))): []
        for year_days in language_year_days.values()
        if len(year_days) != 0
    }
    for lang, year_days in language_year_days.items():
        if len(year_days) != 0:
            year_days_langs[tuple(sorted(list(year_days)))].append(lang)

    for year_days, langs in year_days_langs.items():
        print(f"Running {', '.join(l.lang for l in langs)} for:")
        for year in sorted(list(set(y for y, _ in year_days))):
            days_for_year = [d for y, d in year_days if y == year]
            if len(days_for_year) == 1:
                print(f"{year}, day {days_for_year[0]}")
            else:
                ranges = contiguous_groups(days_for_year)
                print(
                    f"{year}, days {', '.join(f'{start}-{end}' if start != end else str(start) for start, end in ranges)}"
                )

        print()

    print("\n")

    for lang, year_days in language_year_days.items():
        totalTime = 0
        language = lang.lang.title()

        if len(year_days) == 0:
            continue

        print(f"Running {language}...")

        for i, (year, day) in enumerate(year_days):
            if progressBar and i == 0:
                printProgressBar(i, len(year_days))

            for _, t in lang.run(year, day, not progressBar, loggers=loggers):
                totalTime += t

            if progressBar:
                printProgressBar(i + 1, len(year_days))

        print(f"\n{language}: Total time: {totalTime:.4f} seconds\n\n")


def aoc_parser() -> argparse.ArgumentParser:
    langs_iter = list(map(str, LANGS))
    year_iterable = get_released()
    day_iterable = list(range(1, 26))

    parser = argparse.ArgumentParser(
        description="Run Advent of Code solutions.", conflict_handler="resolve"
    )

    parser.add_argument(
        "--year",
        "-y",
        type=int,
        nargs="+",
        default=year_iterable,
        help="Specify year(s) to run. Default: All",
    )
    parser.add_argument(
        "--day",
        "-d",
        type=int,
        nargs="+",
        default=day_iterable,
        help="Specify day(s) to run. Default: All",
    )
    parser.add_argument(
        "--no-run",
        action="store_true",
        help="Do not run the programs, only load existing data. Default: False",
    )

    lang_group = parser.add_mutually_exclusive_group()
    lang_group.add_argument(
        "--languages",
        "-l",
        type=str,
        nargs="+",
        default=langs_iter,
        choices=langs_iter,
        help="Specify language(s) to run. Default: All",
    )
    lang_group.add_argument(
        "--exclude",
        type=str,
        nargs="+",
        default=[],
        choices=langs_iter,
        help="Exclude language(s) from running. Default: None",
    )

    parser.add_argument(
        "--common",
        action="store_true",
        help="Run only programs that exist in all specified languages. Default: False",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print verbose output. Default: False"
    )

    add_arguments(parser)
    return parser


def main():
    parser = aoc_parser()
    args = parser.parse_args()

    years = vars(args).get("year", get_released())
    days = vars(args).get("day", list(range(1, 26)))
    common = vars(args).get("common", False)
    languages = {
        l: LANGS[l.title()] for l in sorted(vars(args).get("languages", LANGS)) if l not in vars(args).get("exclude", [])
    }

    year_days = set((year, day) for year, day in product(years, days))

    if len(year_days) == 0:
        raise ValueError("No valid years/days for the given languages")

    progressBar = not vars(args).get("verbose", False) and len(year_days) > 1

    if common:
        for s in [set(lang.discover()) for lang in languages.values()]:
            year_days.intersection_update(s)

    language_year_days = {
        lang: sorted(list(year_days.intersection(set(lang.discover()))))
        for lang in languages.values()
    }
    if all(len(k) == 0 for k in language_year_days.values()):
        raise ValueError("No valid years/days for the given languages")

    if vars(args).get("verbose", False):
        print("Running:")

    with RunnerHandler(args) as aoc_runner:
        if not vars(args).get("no_run", False):
            run(language_year_days, progressBar, aoc_runner.loggers)


if __name__ == "__main__":
    main()
