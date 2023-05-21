from pathlib import Path

import click

from .. import term
from . import options
from ._deco import check_config_first, time_program
from .base import NNCommandHandler, is_executeable_global_path, test_or_find_pingo
from .common import optimize_images

console = term.get_console()


@click.command(
    name="optimize",
    help="Optimize images with pingo",
    cls=NNCommandHandler,
)
@options.path_or_archive(disable_archive=True)
@click.option(
    "-ax",
    "--aggressive",
    "aggresive_mode",
    default=False,
    show_default=True,
)
@options.pingo_path
@check_config_first
@time_program
def image_optimizer(
    path_or_archive: Path,
    aggresive_mode: bool,
    pingo_path: str,
):
    """
    Optimize images with pingo
    """

    if not path_or_archive.is_dir():
        raise click.BadParameter(
            f"{path_or_archive} is not a directory. Please provide a directory.",
            param_hint="path_or_archive",
        )

    force_search = not is_executeable_global_path(pingo_path, "exiftool")
    pingo_exe = test_or_find_pingo(pingo_path, force_search)
    if pingo_exe is None:
        console.error("pingo not found dumbass, unable to optimize images")
        raise click.exceptions.Exit(1)

    console.info(f"Using pingo at {pingo_exe}")
    console.info("Optimizing images...")
    optimize_images(pingo_exe, path_or_archive, aggresive_mode)