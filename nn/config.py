import json
import os.path
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ._ntypes import BracketTypeT, ConfigT, _ConfigDefaultsT, _ConfigExecutableT
from .cli.constants import M_PUBLICATION_TYPES

__all__ = (
    "get_config",
    "ConfigHandler",
    "ConfigError",
    "Config",
)

if sys.platform == "win32":
    CONFIG_DIR = Path(os.path.expandvars(r"%APPDATA%\nn"))
else:
    CONFIG_DIR = Path.expanduser(Path("~/.config/nn"))


@dataclass
class _ConfigExecutable:
    magick_path: str = field(default="magick")
    pingo_path: str = field(default="pingo")
    exiftool_path: str = field(default="exiftool")

    def to_dict(self) -> _ConfigExecutableT:
        return {
            "magick_path": self.magick_path,
            "pingo_path": self.pingo_path,
            "exiftool_path": self.exiftool_path,
        }


@dataclass
class _ConfigDefaults:
    bracket_type: BracketTypeT = field(default="round")
    rip_credit: str = field(default="bob")
    rip_email: str = field(default="lol@bob.com")
    ch_add_c_prefix: bool = field(default=False)
    ch_special_tag: str = field(default="x")

    rls_pub_type: str = field(default=list(M_PUBLICATION_TYPES.keys())[0])
    rls_ch_pub_type: str = field(default=list(M_PUBLICATION_TYPES.keys())[0])

    def to_dict(self) -> _ConfigDefaultsT:
        return {
            "bracket_type": self.bracket_type,
            "rip_credit": self.rip_credit,
            "rip_email": self.rip_email,
            "chapter_add_c_prefix": self.ch_add_c_prefix,
            "chapter_special_tag": self.ch_special_tag,
            "release_publication_type": self.rls_pub_type,
            "release_chapter_publication_type": self.rls_ch_pub_type,
        }

    @property
    def is_special_x(self) -> bool:
        return self.ch_special_tag == "x"


@dataclass
class Config:
    defaults: _ConfigDefaults = field(default_factory=_ConfigDefaults)
    executables: _ConfigExecutable = field(default_factory=_ConfigExecutable)

    def to_dict(self) -> ConfigT:
        return {
            "defaults": self.defaults.to_dict(),
            "executables": self.executables.to_dict(),
        }


class ConfigError(TypeError):
    pass


class ConfigHandler:
    def __init__(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        self.__config_file = CONFIG_DIR / "config.json"
        self.__config = Config()
        self._is_first_time_warn = False

        self.read_and_parse()

    def _parse_config(self, json_data: ConfigT) -> Config:
        defaults = json_data.get("defaults", {})
        executables = json_data.get("executables", {})

        if not isinstance(defaults, dict):
            raise ConfigError("`defaults` must be a dict")
        if not isinstance(executables, dict):
            raise ConfigError("`executables` must be a dict")

        config = Config()

        bracket_type = defaults.get("bracket_type", "round")
        if not isinstance(bracket_type, str):
            raise ConfigError("`defaults.bracket_type` must be a string")

        rip_credit = defaults.get("rip_credit", "bob")
        if not isinstance(rip_credit, str):
            raise ConfigError("`defaults.ripper_credit` must be a string")

        rip_email = defaults.get("rip_email", "lol@bob.com")
        if not isinstance(rip_email, str):
            raise ConfigError("`defaults.ripper_email` must be a string")

        ch_add_c_prefix = defaults.get("chapter_add_c_prefix", False)
        if not isinstance(ch_add_c_prefix, bool):
            raise ConfigError("`defaults.chapter_add_c_prefix` must be a bool")

        ch_special_tag = defaults.get("chapter_special_tag", "x")
        if not isinstance(ch_special_tag, str):
            raise ConfigError("`defaults.chapter_special_tag` must be a string")

        rls_pub_type = defaults.get("release_publication_type", list(M_PUBLICATION_TYPES.keys())[0])
        if not isinstance(rls_pub_type, str):
            raise ConfigError("`defaults.release_publication_type` must be a string")

        rls_ch_pub_type = defaults.get("release_chapter_publication_type", list(M_PUBLICATION_TYPES.keys())[0])
        if not isinstance(rls_ch_pub_type, str):
            raise ConfigError("`defaults.release_chapter_publication_type` must be a string")

        if rls_pub_type not in M_PUBLICATION_TYPES:
            raise ConfigError("`defaults.release_publication_type` is not a valid publication type")
        if rls_ch_pub_type not in M_PUBLICATION_TYPES:
            raise ConfigError("`defaults.release_chapter_publication_type` is not a valid publication type")

        config.defaults = _ConfigDefaults(
            bracket_type=bracket_type,
            rip_credit=rip_credit,
            rip_email=rip_email,
            ch_add_c_prefix=ch_add_c_prefix,
            ch_special_tag=ch_special_tag,
            rls_pub_type=rls_pub_type,
            rls_ch_pub_type=rls_ch_pub_type,
        )

        magick_path = executables.get("magick_path", "magick")
        if not isinstance(magick_path, str):
            raise ConfigError("`executables.magick_path` must be a string")

        pingo_path = executables.get("pingo_path", "pingo")
        if not isinstance(pingo_path, str):
            raise ConfigError("`executables.pingo_path` must be a string")

        exiftool_path = executables.get("exiftool_path", "exiftool")
        if not isinstance(exiftool_path, str):
            raise ConfigError("`executables.exiftool_path` must be a string")

        config.executables = _ConfigExecutable(
            magick_path=magick_path, pingo_path=pingo_path, exiftool_path=exiftool_path
        )

        is_first_time = bool(json_data.get("_is_first_time", False))
        self._is_first_time_warn = is_first_time

        return config

    def read_and_parse(self) -> None:
        if self.__config_file.exists():
            with self.__config_file.open("r") as f:
                parsed_config = json.load(f)

            parsed = self._parse_config(parsed_config)
            self.__config = parsed
        else:
            self.save_config(self.__config, True)
            self._is_first_time_warn = True

    def save_config(self, config: Config, mark_first_time: bool = False) -> None:
        as_dict = config.to_dict()
        self.__config = config

        as_dict["_is_first_time"] = mark_first_time

        with self.__config_file.open("w") as f:
            json.dump(as_dict, f, indent=4, ensure_ascii=False)

    @property
    def config(self) -> Config:
        return self.__config

    def is_first_time(self) -> bool:
        return self._is_first_time_warn


_config_handler: Optional[ConfigHandler] = None


def get_config_handler() -> ConfigHandler:
    global _config_handler

    if _config_handler is None:
        # Initialize here to prevent some stupid thing
        _config_handler = ConfigHandler()

    return _config_handler


def get_config() -> Config:
    return get_config_handler().config