import functools
from typing import Callable, List, Optional, Tuple

import click

from .. import config, term
from .base import NNCommandHandler, test_or_find_exiftool, test_or_find_magick, test_or_find_pingo
from .constants import M_PUBLICATION_TYPES

__all__ = ("cli_config",)
cfhandler = config.get_config_handler()
console = term.get_console()


SAVE_CHOICE = term.ConsoleChoice("save_data", "Save")
CANCEL_CHOICE = term.ConsoleChoice("cancel_data", "Cancel")


_default_bracket_index = ["round", "square", "curly"]


def _check_defaults_inquire_validator(text: str):
    if not isinstance(text, str):
        return False

    if len(text.strip()) < 1:
        return False

    return True


def _loop_defaults_bracket_type(config: config.Config) -> config.Config:
    choice_round = term.ConsoleChoice("round", "Round bracket type -> (bob)")
    choice_square = term.ConsoleChoice("square", "Square bracket type -> [bob]")
    choice_curly = term.ConsoleChoice("curly", "Curly bracket type -> {bob}")

    default_idx = _default_bracket_index.index(config.defaults.bracket_type)
    choices = [choice_round, choice_square, choice_curly]

    select_option = console.choice(
        f"Select default bracket type [current: {config.defaults.bracket_type}]",
        choices=choices,
        default=choices[default_idx],
    )

    config.defaults.bracket_type = select_option.name
    return config


def _loop_defaults_rip_credit(config: config.Config) -> config.Config:
    rip_name = console.inquire(
        "Rip credit name",
        validation=_check_defaults_inquire_validator,
        default=config.defaults.rip_credit,
    )

    config.defaults.rip_credit = rip_name
    return config


def _loop_defaults_rip_email(config: config.Config) -> config.Config:
    rip_email = console.inquire(
        "Ripper credit email",
        validation=_check_defaults_inquire_validator,
        default=config.defaults.rip_email,
    )

    config.defaults.rip_email = rip_email
    return config


def _loop_defaults_chapter_prefixed(config: config.Config) -> config.Config:
    CHOICE_ENABLE = term.ConsoleChoice("yes_add", "Enable")
    CHOICE_DISABLE = term.ConsoleChoice("no_yeet", "Disable")

    message = "Enable `c` prefixing for chapter packing? (ex: c001 instead of 001)"
    message += f" [Current: {config.defaults.ch_add_c_prefix}]"

    select_option = console.choice(
        message=message,
        choices=[CHOICE_ENABLE, CHOICE_DISABLE],
        default=CHOICE_ENABLE if config.defaults.ch_add_c_prefix else CHOICE_DISABLE,
    )

    option = select_option.name
    if option == CHOICE_ENABLE.name:
        config.defaults.ch_add_c_prefix = True
    else:
        config.defaults.ch_add_c_prefix = False
    return config


def _loop_defaults_chapter_special_tag(config: config.Config) -> config.Config:
    CHOICE_ENABLE = term.ConsoleChoice("use_hashtag", "Use `#`")
    CHOICE_DISABLE = term.ConsoleChoice("use_xmark", "Use `x`")

    message = "Use `#` instead of `x` as special separator"
    message += f" [Current: {config.defaults.is_special_x}]"

    select_option = console.choice(
        message=message,
        choices=[CHOICE_ENABLE, CHOICE_DISABLE],
        default=CHOICE_DISABLE if config.defaults.is_special_x else CHOICE_ENABLE,
    )

    option = select_option.name
    if option == CHOICE_ENABLE.name:
        config.defaults.ch_special_tag = "#"
    else:
        config.defaults.ch_special_tag = "x"
    return config


def _loop_defaults_release_publication_type(config: config.Config, default_now: str) -> str:
    choices_raw: List[term.ConsoleChoice] = []
    selected_choice = 0
    for idx, (key_name, key_value) in enumerate(M_PUBLICATION_TYPES.items()):
        if key_name == default_now:
            selected_choice = idx
        fmt_desc = f"{key_name.capitalize()}: {key_value.description} ({key_value.image!r}/{key_value.archive!r})"
        choices_raw.append(term.ConsoleChoice(key_name, fmt_desc))

    select_option = console.choice(
        f"Select default bracket type [current: {config.defaults.bracket_type}]",
        choices=choices_raw,
        default=choices_raw[selected_choice],
    )

    return select_option.name


def _loop_defaults_sections(config: config.Config) -> config.Config:
    while True:
        select_option = console.choice(
            "Select what you want to do for defaults section",
            choices=[
                term.ConsoleChoice("bracket_type", "Configure default bracket type"),
                term.ConsoleChoice("rip_credit", "Configure default ripper credit name"),
                term.ConsoleChoice("rip_email", "Configure default ripper credit email"),
                term.ConsoleChoice("ch_add_prefix", "Enable `c` prefixing for chapter packing/tagging"),
                term.ConsoleChoice("hashtag_special", "Use `#` instead of `x` as special separator"),
                term.ConsoleChoice("rls_pub_type", "Configure default publication type for releases command"),
                term.ConsoleChoice("rls_ch_pub_type", "Configure default publication type for releasesch command"),
                SAVE_CHOICE,
            ],
        )

        option = select_option.name
        if option == SAVE_CHOICE.name:
            return config
        elif option == "bracket_type":
            config = _loop_defaults_bracket_type(config)
        elif option == "rip_credit":
            config = _loop_defaults_rip_credit(config)
        elif option == "rip_email":
            config = _loop_defaults_rip_email(config)
        elif option == "ch_add_prefix":
            config = _loop_defaults_chapter_prefixed(config)
        elif option == "hashtag_special":
            config = _loop_defaults_chapter_special_tag(config)
        elif option == "rls_pub_type":
            config.defaults.rls_pub_type = _loop_defaults_release_publication_type(config, config.defaults.rls_pub_type)
        elif option == "rls_ch_pub_type":
            config.defaults.rls_ch_pub_type = _loop_defaults_release_publication_type(
                config, config.defaults.rls_ch_pub_type
            )
        else:
            console.warning("Invalid option selected")
            console.sleep(2)
        console.enter()


# --- Executables --- #


def _check_executables_inquire_validation(text: str, validator_func: Callable[[str, bool], Optional[str]]):
    if not _check_defaults_inquire_validator(text):
        return False

    if text.lower() == "skip this":
        return True

    validate_res = validator_func(text, False)

    return validate_res is not None


def _loop_executables_check_single(
    executable: str,
    default: str,
    validator_func: Callable[[str, bool], Optional[str]],
) -> Optional[str]:
    console.info(f"Configuring executable `{executable}`")
    console.info("You can skip or cancel this by typing `skip this` (without the backticks)")
    console.info("This section will check if the executable is valid or not")

    validation_wrap = functools.partial(_check_executables_inquire_validation, validator_func=validator_func)

    executable_path = console.inquire(
        f"Executable path for `{executable}`",
        validation=validation_wrap,
        default=default,
    )

    return executable_path if executable_path.lower() != "skip this" else None


def _loop_executables_sections(config: config.Config):
    while True:
        select_option = console.choice(
            "Select what you want to do for executables section",
            choices=[
                term.ConsoleChoice("pingo_path", "Configure `pingo` path"),
                term.ConsoleChoice("exiftool_path", "Configure `exiftool` path"),
                term.ConsoleChoice("magick_path", "Configure `magick` path"),
                SAVE_CHOICE,
            ],
        )

        option = select_option.name
        if option == SAVE_CHOICE.name:
            return config
        elif option == "pingo_path":
            result = _loop_executables_check_single("pingo", config.executables.pingo_path, test_or_find_pingo)
            if result is not None:
                config.executables.pingo_path = result
        elif option == "rip_credit":
            result = _loop_executables_check_single("exiftool", config.executables.exiftool_path, test_or_find_exiftool)
            if result is not None:
                config.executables.exiftool_path = result
        elif option == "rip_email":
            result = _loop_executables_check_single("magick", config.executables.magick_path, test_or_find_magick)
            if result is not None:
                config.executables.magick_path = result
        else:
            console.warning("Invalid option selected")
            console.sleep(2)
        console.enter()


# --- Main --- #


def _loop_main_sections(config: config.Config) -> Tuple[bool, config.Config]:
    while True:
        select_option = console.choice(
            "Select what you want to configure",
            choices=[
                term.ConsoleChoice("defaults", "Configure defaults"),
                term.ConsoleChoice("executables", "Configure executables"),
                SAVE_CHOICE,
                CANCEL_CHOICE,
            ],
        )

        option = select_option.name
        if option == SAVE_CHOICE.name:
            return True, config
        elif option == CANCEL_CHOICE.name:
            return False, config
        elif option == "defaults":
            console.enter()
            config = _loop_defaults_sections(config)
        elif option == "executables":
            console.enter()
            config = _loop_executables_sections(config)
        console.enter()


@click.command("config", help="Configure nn CLI", cls=NNCommandHandler)
def cli_config():
    config = cfhandler.config

    do_save, config = _loop_main_sections(config)

    console.enter()
    if do_save:
        console.info("Saving configuration...")
        cfhandler.save_config(config)
        console.info("Configuration saved!")
    else:
        console.warning("Canceling configuration...")
        # This will just stop the first time warning
        cfhandler.save_config(config)