from abc import ABC, abstractmethod
from ast import dump
from collections import defaultdict
from dataclasses import dataclass, field
from functools import reduce
from typing import Any, Dict, Hashable, Iterable, List, Optional, Tuple

import prettytable as pt
from prettytable import TableStyle


@dataclass
class DataTracker(ABC):
    """
    Tracker for AOC Data
    """
    dump_this: bool = True
    print_this: bool = True
    data: Dict[Hashable, Any] = field(default_factory=dict)

    def conv_key(self, key: Tuple[Hashable], *args) -> List[Hashable]:
        if not isinstance(key, list):
            if isinstance(key, Iterable):
                key = list(key)
            else:
                key = [key]
        key += [*args]
        return key


    def add_data(self, key: Tuple[Hashable], *args, new_data: Any, **kwargs) -> None:
        """
        Add data to the tracker
        """
        key = self.conv_key(key, *args)

        k = key[0]
        if len(key) == 1:
            self.data[k] = new_data
        else:
            if k not in self.data:
                self.data[k] = type(self)(dump_this=self.dump_this, print_this=self.print_this)
            self.data[k].add_data(key[1:], new_data=new_data)

        self.update()

    def __getitem__(
        self, key: Hashable | List[Hashable], *args
    ) -> Any:
        key = self.conv_key(key, *args)

        if len(key) == 1:
            return self.data[key[0]]

        return self.data[key[0]][key[1:]]

    def __contains__(
        self, key: Hashable | List[Hashable], *args
    ) -> bool:
        key = self.conv_key(key, *args)

        if len(key) == 1:
            return key[0] in self.data

        return key[0] in self.data and key[1:] in self.data[key[0]]

    def __len__(self) -> int:
        tot_len = 0
        for v in self.data.values():
            if isinstance(v, type(self)):
                tot_len += len(v)
            else:
                tot_len += 1

        return tot_len

    def __call__(self, index_labels: List[str], style: str="DEFAULT", **kwargs) -> str:
        """
        Get tables from the DataTracker
        """
        if not self.print_this:
            return ""

        use_divider = style in ["DEFAULT", "SINGLE_BORDER"]
        use_divider = style not in ["MARKDOWN", "DOUBLE_BORDER"]
        logger_name = kwargs.get("logger_name", "data")
        # use_divider = True

        as_tables = self.get_tables(index_labels=index_labels, **kwargs)
        out_tables = defaultdict(pt.PrettyTable)

        for tab_name, table_data_format in sorted(as_tables.items(), key=lambda x: tuple((len(v), v) for v in x)):
            table_data, (add_ix_label, reduce_row_indecies, no_dividers, row_ix_slice), num_keys = table_data_format

            if add_ix_label and num_keys < 2:
                tab_name = f"{index_labels[num_keys]} {tab_name}"

            max_row_indecies = max(len(v) for v in table_data.keys())
            row_ix_slice = slice(*row_ix_slice.indices(max_row_indecies))


            max_row_indecies = min(max_row_indecies, row_ix_slice.stop - row_ix_slice.start)
            col_labels = index_labels[num_keys:num_keys+max_row_indecies]
            # max_row_indecies = len(col_labels)

            field_names = sorted(reduce(lambda x, y: x | set(y), map(lambda v: set(v.keys()), table_data.values()), set()))
            out_tables[tab_name].field_names = col_labels + field_names
            out_tables[tab_name].float_format = ".4"

            p_row_indecies = []
            rows = []
            for row_indecies, row_data in sorted(table_data.items(), key=lambda x: tuple((len(x[0][i]), x[0][i]) if len(x[0]) > i else (0, "") for i in range(max_row_indecies))):
                reduced_row_indecies = [index if (not reduce_row_indecies or i >= len(p_row_indecies) or index != p_row_indecies[i]) else "" for i, index in enumerate(row_indecies[row_ix_slice])]
                if not reduced_row_indecies:
                    continue
                
                if not no_dividers and p_row_indecies and reduced_row_indecies[0]:
                    rows[-1][-1]["divider"] = use_divider

                rows.append(((reduced_row_indecies + [""] * max(max_row_indecies - len(row_indecies), 0) + [row_data.get(col_name, "") for col_name in field_names]), {}))
                p_row_indecies = row_indecies

            for row, kwargs in rows:
                out_tables[tab_name].add_row(row, **kwargs)

        tab_style = vars(TableStyle).get(style)
        for table in out_tables.values():
            table.set_style(tab_style)

        # Get printing order of tables
        year_filter = lambda x: inv ^ x.isnumeric()
        inv = True
        extra_tables = sorted(filter(year_filter, out_tables.keys()))
        inv = False
        year_tables = sorted(filter(year_filter, out_tables.keys()))

        # Stringify the tables
        if style == "MARKDOWN":
            lower = lambda s: s.lower()
            return_string = f"# Advent of Code {logger_name.title()}\n\n"

            if len(out_tables):
                for table_key in extra_tables:
                    return_string += f"* [{table_key}](#{'-'.join(map(lower, table_key.split()))})\n\n"
                
                return_string += f"Yearly {logger_name} for all languages:\n\n"
                
                for table_key in year_tables:
                    return_string += f"* [{table_key}](#{'-'.join(map(lower, table_key.split()))})\n\n"
                
                for table_key in extra_tables + year_tables:
                    return_string += f"\n## {table_key}\n\n"
                    return_string += f"[Back to top](#advent-of-code-{logger_name})\n\n"
                    return_string += f"{out_tables[table_key]}\n"
            else:
                return_string += "No data to display"
        else:
            return_string = "\n\n".join(f"{k}:\n{out_tables[k]}" for k in year_tables + extra_tables)

        return return_string
    
    def get_tables(self, keys: List[Hashable]=[], tables: Optional[Dict[str, Dict]]=None, **kwargs) -> Dict[str, Tuple[Dict, Tuple[Any]]]:
        """
        Get tables from the DataTracker
        """
        if tables is None:
            tables = defaultdict(lambda: [defaultdict(dict), (True, True, False, slice(None)), float("inf")])
        str_title = lambda s: str(s).title()
        def dict_to_table(d: Dict[Hashable, Any]):
            for k, v in sorted(d.items(), key=lambda x: str(x[0])):
                # Skip certain keys
                if k in ["dump_this", "print_this"]:
                    continue

                # Turn into table by type
                if issubclass(type(v), type(self)):
                    v.get_tables(keys=keys + [k], tables=tables, **kwargs)
                elif isinstance(v, dict):
                    dict_to_table(v)
                else:
                    if not (key_data := self.keys_to_indecies(keys + [k])):
                        continue
                    
                    (col_name, tab_name, *row_indecies), table_format, num_keys = key_data
                    col_name, tab_name, *row_indecies = map(str_title, [col_name, tab_name, *row_indecies])
                    tables[tab_name][0][tuple(row_indecies)][col_name] = v
                    
                    # (add_ix_label, reduce_row_indecies, no_dividers, row_ix_slice)
                    tables[tab_name][1] = table_format
                    tables[tab_name][2] = min(tables[tab_name][2], num_keys)

                    # if "keys" not in tables[tab_name]:
                    #     tables[tab_name][0]["keys"] = len(keys)
                    # else:
                    #     tables[tab_name][0]["keys"] = min(tables[tab_name]["keys"], len(keys))

        dict_to_table(vars(self))
        return tables

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def keys_to_indecies(self, keys: List[Hashable]) -> Tuple[List[str], List[Any], int]:
        pass
