import time

from .. import config, term

__all__ = (
    "check_config_first",
    "time_program",
)

console = term.get_console()
cfhandler = config.get_config_handler()


def time_program(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        delta = end - start
        if isinstance(result, int) and result > 0:
            console.error(f"Failure! (Took {delta:.2f}s) [exit code {result}]")
        else:
            console.info(f"Done! (Took {delta:.2f}s)")
        return result

    return wrapper


def check_config_first(func):
    def wrapper(*args, **kwargs):
        if cfhandler.is_first_time():
            console.warning("First time setup not complete, please run `nn config`")
        result = func(*args, **kwargs)
        return result

    return wrapper