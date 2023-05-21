from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional, Union

import click

from .. import config, term
from . import options
from ._deco import check_config_first, time_program
from .base import NNCommandHandler, is_executeable_global_path, test_or_find_exiftool
from .common import format_archive_filename, inject_metadata
from .constants import MPublication

console = term.get_console()
conf = config.get_config()
TARGET_TITLE = "{mt} {vol} ({year}) ({pt}) {cpa}{c}{cpb}"


@click.command(
    name="tag",
    help="Tag images with metadata",
    cls=NNCommandHandler,
)
@options.path_or_archive(disable_archive=True)
@click.option(
    "-t",
    "--title",
    "m_title",
    required=True,
    help="The title of the series",
)
@options.m_volume
@options.m_chapter
@options.m_year
@options.m_publication_type()
@options.rls_credit
@options.rls_email
@options.rls_revision
@options.use_bracket_type
@options.exiftool_path
@check_config_first
@time_program
def image_tagging(
    path_or_archive: Path,
    m_title: str,
    m_volume: Optional[int],
    m_chapter: Optional[Union[int, float]],
    m_year: int,
    m_publication_type: MPublication,
    rls_credit: str,
    rls_email: str,
    rls_revision: int,
    bracket_type: Literal["square", "round", "curly"],
    exiftool_path: str,
):
    """
    Tag images with metadata
    """

    if not path_or_archive.is_dir():
        raise click.BadParameter(
            f"{path_or_archive} is not a directory. Please provide a directory.",
            param_hint="path_or_archive",
        )

    force_search = not is_executeable_global_path(exiftool_path, "exiftool")
    exiftool_exe = test_or_find_exiftool(exiftool_path, force_search)
    if exiftool_exe is None:
        console.error("Exiftool not found dumbass, unable to tag image with exif metadata!")
        raise click.exceptions.Exit(1)

    current_pst = datetime.now(timezone(timedelta(hours=-8)))
    current_year = m_year or current_pst.year

    tag_sep = conf.defaults.ch_special_tag

    volume_text: Optional[str] = None
    if m_chapter is not None:
        if isinstance(m_chapter, float):
            float_string = str(m_chapter)
            base_float, decimal_float = float_string.split(".")
            dec_float = int(decimal_float)
            if dec_float - 4 > 0:
                dec_float -= 4
            volume_text = f"{int(base_float):03d}{tag_sep}{dec_float}"
        else:
            volume_text = f"{m_chapter:03d}"
        if conf.defaults.ch_add_c_prefix:
            volume_text = f"c{volume_text}"
    if m_volume is not None:
        volume_text = f"v{m_volume:02d}"
    if volume_text is None:
        raise click.BadParameter(
            "Please provide either a chapter or a volume number.",
            param_hint="m_volume",
        )

    archive_filename = format_archive_filename(
        m_title=m_title,
        m_year=current_year,
        publication_type=m_publication_type,
        rip_credit=rls_credit,
        bracket_type=bracket_type,
        m_volume_text=volume_text,
        rls_revision=rls_revision,
    )

    console.info("Tagging images with exif metadata...")
    inject_metadata(exiftool_exe, path_or_archive, archive_filename, rls_email)