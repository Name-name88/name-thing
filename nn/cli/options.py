from pathlib import Path
from typing import Optional

import click

from ..config import get_config
from ..exporter import ExporterType
from .constants import M_PUBLICATION_TYPES

config = get_config()


def path_or_archive(disable_archive: bool = False, disable_folder: bool = False):
    if disable_archive and disable_folder:
        raise click.UsageError("You can't disable both archive and folder")

    metavar = "path_or_archive_file"
    if disable_archive:
        metavar = "folder_path"
    elif disable_folder:
        metavar = "archive_file"

    return click.argument(
        "path_or_archive",
        metavar=metavar.upper(),
        required=True,
        type=click.Path(
            exists=True,
            resolve_path=True,
            file_okay=not disable_archive,
            dir_okay=not disable_folder,
            path_type=Path,
        ),
    )


class FloatIntParamType(click.ParamType):
    name = "int_or_float"

    def convert(self, value, param, ctx):
        if isinstance(value, int):
            return value

        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            self.fail(f"{value!r} is not a valid integer or floating type", param, ctx)


class MPublicationParamType(click.ParamType):
    name = "publication_type"

    def convert(self, value, param, ctx):
        if not isinstance(value, str):
            self.fail(f"{value!r} is not a valid string", param, ctx)

        pub_type = M_PUBLICATION_TYPES.get(value)
        pub_keys_list = list(M_PUBLICATION_TYPES.keys())
        pub_keys = "`" + "`, `".join(pub_keys_list) + "`"

        if pub_type is None:
            self.fail(f"{value!r} is not a valid publication type (must be either: {pub_keys})")
        return pub_type

    def get_metavar(self, param: "click.core.Parameter") -> Optional[str]:
        choices_str = "|".join(list(M_PUBLICATION_TYPES.keys()))

        if param.required and param.param_type_name == "argument":
            return f"{{{choices_str}}}"
        return f"[{choices_str}]"


FLOAT_INT = FloatIntParamType()
PUBLICATION_TYPE = MPublicationParamType()


def m_publication_type(chapter_mode: bool = False):
    default_arg = config.defaults.rls_pub_type
    if chapter_mode:
        default_arg = config.defaults.rls_ch_pub_type

    return click.option(
        "-pt",
        "--publication-type",
        "m_publication_type",
        type=PUBLICATION_TYPE,
        help="The publication type for this series, use none to remove it from image filename",
        default=default_arg,
        show_default=True,
    )


archive_file = click.argument(
    "archive_file",
    metavar="ARCHIVE_FILE",
    required=True,
    type=click.Path(exists=True, resolve_path=True, file_okay=True, dir_okay=False, path_type=Path),
)
output_mode = click.option(
    "-m",
    "--mode",
    "output_mode",
    type=click.Choice(ExporterType),
    help="The output mode for the archive packing",
    default=ExporterType.cbz,
    show_default=True,
)
magick_path = click.option(
    "-me",
    "--magick-exec",
    "magick_path",
    default=config.executables.magick_path,
    help="Path to the magick executable",
    show_default=True,
)
exiftool_path = click.option(
    "-ee",
    "--exiftool-exec",
    "exiftool_path",
    default=config.executables.exiftool_path,
    help="Path to the exiftool executable",
    show_default=True,
)
pingo_path = click.option(
    "-pe",
    "--pingo-exec",
    "pingo_path",
    default=config.executables.pingo_path,
    help="Path to the pingo executable",
    show_default=True,
)
debug_mode = click.option(
    "-v",
    "--verbose",
    "debug_mode",
    is_flag=True,
    default=False,
    help="Enable debug mode",
)
use_bracket_type = click.option(
    "-br",
    "--bracket-type",
    "bracket_type",
    default=config.defaults.bracket_type,
    help="Bracket to use to surround the ripper name",
    show_default=True,
    type=click.Choice(["square", "round", "curly"]),
)
m_volume = click.option(
    "-vol",
    "--volume",
    "m_volume",
    type=int,
    help="The volume of the series release",
    default=None,
)
m_chapter = click.option(
    "-ch",
    "--chapter",
    "m_chapter",
    type=FLOAT_INT,
    help="The chapter of the series release",
    default=None,
)
m_ripper = click.option(
    "-ch",
    "--chapter",
    "m_chapter",
    type=FLOAT_INT,
    help="The chapter of the series release",
    default=None,
)
m_year = click.option(
    "-y",
    "--year",
    "m_year",
    default=None,
    type=int,
    help="The year of the series release",
)
m_title = click.option(
    "-t",
    "--title",
    "m_title",
    required=True,
    help="The title of the series",
)
m_publisher = click.option(
    "-pub",
    "--publisher",
    "m_publisher",
    help="The publisher of the series",
    required=True,
)

rls_credit = click.option(
    "-c",
    "--credit",
    "rls_credit",
    help="The ripper credit for this series",
    show_default=True,
    default=config.defaults.rip_credit,
)
rls_email = click.option(
    "-e",
    "--email",
    "rls_email",
    help="The ripper email for this series",
    show_default=True,
    default=config.defaults.rip_email,
)
rls_revision = click.option(
    "-r",
    "--revision",
    "rls_revision",
    help="The revision of the release, if the number 1 provided it will not put in the filename",
    type=click.IntRange(min=1, max_open=True),
    default=1,
    show_default=True,
)