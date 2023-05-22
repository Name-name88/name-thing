from typing import Literal, TypedDict

__all__ = (
    "ConfigT",
    "BracketTypeT",
)
BracketTypeT = Literal["square", "round", "curly"]


class _ConfigDefaultsT(TypedDict, total=False):
    bracket_type: BracketTypeT
    rip_credit: str
    rip_email: str


class _ConfigExecutableT(TypedDict, total=False):
    magick_path: str
    pingo_path: str
    exiftool_path: str


class ConfigT(TypedDict, total=False):
    _is_first_time: bool
    defaults: _ConfigDefaultsT
    executables: _ConfigExecutableT