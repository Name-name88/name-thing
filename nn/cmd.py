from __future__ import annotations

from pathlib import Path

import click

from .cli.archive import pack_releases, pack_releases_comment_archive, pack_releases_epub_mode
from .cli.auto_split import auto_split
from .cli.config import cli_config
from .cli.image_optimizer import image_optimizer
from .cli.image_tagging import image_tagging
from .cli.manual_split import manual_split
from .cli.merge_chapters import merge_chapters
from .cli.releases import prepare_releases, prepare_releases_chapter
from .cli.spreads_manager import spreads
from .constants import __author__, __name__, __version__
from .term import get_console

console = get_console()


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
WORKING_DIR = Path.cwd().absolute()


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(
    __version__,
    "--version",
    "-V",
    prog_name=__name__,
    message="%(prog)s v%(version)s - Created by {}".format(__author__),
)
@click.option(
    "-v",
    "--verbose",
    "verbose",
    is_flag=True,
    required=False,
    help="Enable debug/verbose mode",
    default=False,
)
@click.pass_context
def main(ctx: click.Context, verbose: bool):
    
    ctx.ensure_object(dict)
    ctx.obj["VERBOSE_MODE"] = verbose
    if verbose:
        console.enable_debug()
    else:
        console.disable_debug()


main.add_command(auto_split)
main.add_command(cli_config)
main.add_command(manual_split)
main.add_command(merge_chapters)
main.add_command(pack_releases)
main.add_command(pack_releases_epub_mode)
main.add_command(pack_releases_comment_archive)
main.add_command(prepare_releases)
main.add_command(prepare_releases_chapter)
main.add_command(spreads)
main.add_command(image_tagging)
main.add_command(image_optimizer)


if __name__ == "__main__":
    main()