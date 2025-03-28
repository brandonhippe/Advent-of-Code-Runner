import re
from pathlib import Path
import subprocess


def main():
    pyproj = Path(Path(__file__).resolve().parent.parent, "pyproject.toml")

    with open(pyproj, "r") as f:
        pyproj_text = f.read()

    reqs_text = subprocess.run(["python3", "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    deps_regex = re.compile(r"dependencies = \[.*?\]", flags=re.DOTALL | re.MULTILINE)

    new_deps = map(lambda x: f'\t"{x}"', reqs_text)
    new_deps = "dependencies = [\n" + ",\n".join(new_deps) + "\n]"

    if deps_regex.search(pyproj_text):
        new_pyproj = deps_regex.sub(new_deps, pyproj_text)
    else:
        new_pyproj = pyproj_text + "\n" + new_deps

    with open(pyproj, "w") as f:
        f.write(new_pyproj)

if __name__ == '__main__':
    main()