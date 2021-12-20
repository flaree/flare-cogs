# Full credits goto Trusty, https://github.com/TrustyJAID/Trusty-cogs/blob/master/.utils/utils.py

import glob
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Mapping, Optional

import tabulate
from babel.lists import format_list as babel_list

DEFAULT_INFO = {
    "author": [],
    "install_msg": "",
    "name": "",
    "disabled": False,
    "short": "",
    "description": "",
    "tags": [],
    "requirements": [],
    "hidden": False,
}

logging.basicConfig(filename="scripts.log", level=logging.INFO)
log = logging.getLogger(__file__)

ROOT = Path(__file__).parents[1]

VER_REG = re.compile(r"\_\_version\_\_ = \"(\d+\.\d+\.\d+)", flags=re.I)

DEFAULT_AUTHOR = ["flare#0001"]


HEADER = """# Flare-Cogs - (flare#0001)
<p align="center">
  <a href="https://github.com/Cog-Creators/Red-DiscordBot/tree/V3/develop">
    <img src="https://img.shields.io/badge/Red%20DiscordBot-V3-red.svg">
    </a>
  <a href="https://github.com/Rapptz/discord.py">
    <img src="https://img.shields.io/badge/Discord.py-rewrite-blue.svg">
    </a>
  <a href="https://github.com/ambv/black">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg">
    </a>

</p>

# Contact
You can contact me in the Red 3rd party server in #support_flare-cogs

<br>

---


# Installation
`[p]repo add flare-cogs https://github.com/flaree/Flare-Cogs`

`[p]cog install flare-cogs <cog_name>`

---
{body}
---



---
## Cogs in other repos.
---
| Name | Description
| --- | --- |
| Pokecord | Pokecord - found @ [flaree/pokecord-red](https://github.com/flaree/pokecord-red) |
| LastFM | LastFM stats - port of Miso Bot - found @ [flaree/lastfm-red](https://github.com/flaree/lastfm-red) |


---
"""


@dataclass
class InfoJson:
    author: List[str]
    description: Optional[str] = ""
    install_msg: Optional[str] = "Thanks for installing"
    short: Optional[str] = ""
    name: Optional[str] = ""
    min_bot_version: Optional[str] = "3.3.0"
    max_bot_version: Optional[str] = "0.0.0"
    hidden: Optional[bool] = False
    disabled: Optional[bool] = False
    required_cogs: Mapping = field(default_factory=dict)
    requirements: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    type: Optional[str] = "COG"
    permissions: List[str] = field(default_factory=list)
    min_python_version: Optional[List[int]] = field(default_factory=lambda: [3, 8, 0])
    end_user_data_statement: str = (
        "This cog does not persistently store data or metadata about users."
    )

    @classmethod
    def from_json(cls, data: dict):
        min_bot_version = "3.1.8"
        required_cogs: Mapping = {}
        author = data.get("author", [])
        description = data.get("description", "")
        install_msg = data.get("install_msg", "Thanks for installing")
        short = data.get("short", "Thanks for installing")
        if "bot_version" in data:
            min_bot_version = data["bot_version"]
            if isinstance(min_bot_version, list):
                min_bot_version = ".".join(str(i) for i in data["bot_version"])
        if "min_bot_version" in data:
            min_bot_version = data["min_bot_version"]
            # min_bot_version = "3.3.0"
        max_bot_version = data.get("max_bot_version", "0.0.0")
        name = data.get("name", "")
        if "required_cogs" in data:
            if isinstance(data["required_cogs"], list):
                required_cogs = {}
            else:
                required_cogs = data["required_cogs"]
        requirements = data.get("requirements", [])
        tags = data.get("tags", [])
        hidden = data.get("hidden", False)
        disabled = data.get("disabled", False)
        type = data.get("type", "COG")
        permissions = data.get("permissions", [])
        min_python_version = data.get("min_python_version", [])
        end_user_data_statement = data.get(
            "end_user_data_statement",
            "This cog does not persistently store data or metadata about users.",
        )

        return cls(
            author,
            description,
            install_msg,
            short,
            name,
            min_bot_version,
            max_bot_version,
            hidden,
            disabled,
            required_cogs,
            requirements,
            tags,
            type,
            permissions,
            min_python_version,
            end_user_data_statement,
        )


def save_json(folder, data):
    with open(folder, "w") as newfile:
        json.dump(data, newfile, indent=4, sort_keys=True, separators=(",", " : "))


def makereadme():
    """Generate README.md from info about all cogs"""
    table_data = []
    for folder in sorted(os.listdir(ROOT)):
        if folder.startswith(".") or folder.startswith("_"):
            continue
        _version = ""
        info = None
        for file in glob.glob(f"{ROOT}/{folder}/*"):
            if not file.endswith(".py") and not file.endswith("json"):
                continue
            if file.endswith("info.json"):
                try:
                    with open(file, encoding="utf-8") as infile:
                        data = json.loads(infile.read())
                    info = InfoJson.from_json(data)
                except Exception:
                    log.exception(f"Error reading info.json {file}")
            if _version == "":
                with open(file, encoding="utf-8") as infile:
                    data = infile.read()
                    maybe_version = VER_REG.search(data)
                    if maybe_version:
                        _version = maybe_version.group(1)
        if info and not info.disabled and not info.hidden:
            to_append = [info.name.strip(), _version.strip()]
            description = f"<details><summary>{info.short}</summary>{info.description if info.description != info.short else ''}</details>"
            to_append.append(description.strip())
            to_append.append(babel_list(info.author, style="standard").strip())
            table_data.append(to_append)

    body = tabulate.tabulate(
        table_data,
        headers=["Name", "Status/Version", "Description (Click to see full status)", "Authors"],
        # headers=["Name", "Version", "Description (Click to see full info)", "Author(s)"],
        tablefmt="github",
    )
    file_content = HEADER.format(body=body)
    with open(f"{ROOT}/README.md", "r") as outfile:
        if re.sub(" +", " ", outfile.read()) == re.sub(" +", " ", file_content):
            return 1
    with open(f"{ROOT}/README.md", "w") as outfile:
        outfile.write(file_content)
    return 1


if __name__ == "__main__":
    makereadme()
