import re
import subprocess as sp
from pathlib import Path
from typing import Dict, List, Match, Optional, Pattern, Tuple, Union, overload

from . import config, term, utils
from .constants import TARGET_FORMAT, TARGET_FORMAT_ALT, TARGET_TITLE, MPublication

__all__ = (
    "BRACKET_MAPPINGS",
    "PseudoChapterMatch",
    "ChapterRange",
    "RegexCollection",
    "check_cbz_exist",
    "actual_or_fallback",
    "create_chapter",
    "inquire_chapter_ranges",
    "safe_int",
    "inject_metadata",
    "optimize_images",
    "format_archive_filename",
    "format_volume_text",
    "format_daiz_like_filename",
)


console = term.get_console()
conf = config.get_config()


BRACKET_MAPPINGS = {
    "square": ["[", "]"],
    "round": ["(", ")"],
    "curly": ["{", "}"],
}


class PseudoChapterMatch:
    def __init__(self):
        self._contents: Dict[str, str] = {}

    def set(self, key: str, value: str):
        self._contents[key] = value

    def get(self, key: str):
        return self._contents.get(key)

    def group(self, key: Union[str, int]):
        if isinstance(key, int):
            try:
                actual = list(self._contents.keys())[key]
            except IndexError:
                return None
            return self.get(actual)
        return self.get(key)

def format_daiz_like_numbering(
    number: Union[int, float], digit: int = 3, use_minus: bool = True, separator: str = conf.defaults.ch_special_tag
):
    if isinstance(number, int):
        return f"{int(number):0{digit}d}"
    base, floating = str(number).split(".")
    floating = int(floating)
    if floating - 4 >= 1 and use_minus:
        # Handle split chapter (.1, .2, etc)
        floating -= 4
    return f"{int(base):0{digit}d}{separator}{floating}"

class ChapterRange:
    def __init__(self, number: Union[int, float], name: Optional[str] = None, range: List[int] = list(), is_single: bool = False):
        self.number = number
        self.name = name
        self.range = range
        self.is_single = is_single

    def __repr__(self):
        if isinstance(self.number, float):
            return f"<ChapterRange c{self.number} - {self.name}>"
        return f"<ChapterRange c{self.number:03d} - {self.name}>"

    def __eq__(self, other: Union[int, float, "ChapterRange"]):
        if isinstance(other, ChapterRange):
            other = other.number
        return self.number == other

    @property
    def bnum(self):
        return format_daiz_like_numbering(self.number)

    @property
    def base(self):
        if isinstance(self.number, int):
            return self.number
        b, _ = str(self.number).split(".")
        return int(b)

    @property
    def floating(self) -> Optional[int]:
        if not isinstance(self.number, float):
            return None
        _, f = str(self.number).split(".")
        return int(f)


def check_cbz_exist(base_path: Path, filename: str):
    full_path = base_path / f"{filename}.cbz"
    return full_path.exists() and full_path.is_file()


def actual_or_fallback(actual_ch: Optional[str], chapter_num: int) -> str:
    proper_ch = f"{chapter_num:03d}"
    if not actual_ch:
        return proper_ch
    if "." in actual_ch:
        try:
            base, floating = str(float(actual_ch)).split(".", 1)
        except ValueError:
            return proper_ch
        try:
            return f"{int(base):03d}.{floating}"
        except ValueError:
            return proper_ch
    try:
        return f"{int(actual_ch):03d}"
    except ValueError:
        return proper_ch


def create_chapter(match: Union[Match[str], PseudoChapterMatch], has_publisher: bool = False):
    chapter_num = int(match.group("ch"))
    chapter_extra = match.group("ex")
    chapter_vol = match.group("vol")
    chapter_actual = match.group("actual")
    chapter_vol_ex = match.group("volex")
    if chapter_vol is not None:
        if utils.is_oneshot(chapter_vol):
            chapter_vol = 0
        else:
            if chapter_vol_ex is not None:
                chapter_vol = chapter_vol.replace(chapter_vol_ex, "")
                chapter_vol_ex = int(chapter_vol_ex[1:]) + 4
                chapter_vol = float(f"{chapter_vol[1:]}.{chapter_vol_ex}")
            else:
                chapter_vol = int(chapter_vol[1:])

    chapter_title: Optional[str] = None
    try:
        chapter_title = match.group("title")
        if chapter_title is not None:
            chapter_title = utils.clean_title(chapter_title)
    except IndexError:
        pass

    act_ch_num = actual_or_fallback(chapter_actual, chapter_num)

    if chapter_vol is not None:
        chapter_data = f"{format_daiz_like_numbering(chapter_vol, 2, False, '.')}.{act_ch_num}"
    else:
        chapter_data = act_ch_num
    if chapter_extra is not None and chapter_actual is None:
        add_num = int(chapter_extra[1:])
        chapter_data += f".{add_num}"
    if chapter_title is not None:
        chapter_data += f" - {chapter_title}"
    if chapter_title is None and has_publisher and chapter_extra is not None:
        ch_ex = int(chapter_extra[1:])
        if "." in chapter_extra:
            ch_ex -= 4
        chapter_data += f" - Extra {ch_ex}"

    return chapter_data


def safe_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return None


def int_or_float(value: str) -> Optional[Union[int, float]]:
    if "." in value:
        try:
            return float(value)
        except ValueError:
            pass
    return safe_int(value)


def parse_ch_ranges(data: str) -> Tuple[List[int], bool]:
    split_range = data.split("-")
    if len(split_range) < 2:
        return [int(data)], True

    first, second = split_range
    return list(range(int(first), int(second) + 1)), False


def validate_ch_ranges(current: str):
    split_range = current.strip().split("-")
    if len(split_range) < 2:
        return safe_int(current) is not None

    first, second = split_range
    if not isinstance(second, str):
        return False

    first = safe_int(first)
    second = safe_int(second)
    if first is None or second is None:
        return False
    return True


def inquire_chapter_ranges(initial_prompt: str, continue_prompt: str, ask_title: bool = False) -> List[ChapterRange]:
    chapter_ranges: List[ChapterRange] = []
    while True:
        console.info(initial_prompt)

        ch_number = console.inquire("Chapter number", lambda y: int_or_float(y) is not None)
        ch_number = int_or_float(ch_number)

        ch_ranges = console.inquire("Chapter ranges (x-y or x)", validate_ch_ranges)
        actual_ranges, is_single = parse_ch_ranges(ch_ranges)

        ch_title: Optional[str] = None
        if ask_title:
            ch_title = console.inquire("Chapter title", lambda y: len(y.strip()) > 0)
        simple_range = ChapterRange(ch_number, ch_title, actual_ranges, is_single)
        chapter_ranges.append(simple_range)

        do_more = console.confirm(continue_prompt)
        if not do_more:
            break

    return chapter_ranges


def inject_metadata(exiftool_dir: str, current_directory: Path, image_title: str, image_email: str):
    resolve_dir = current_directory.resolve()
    any_jpg = len(list(resolve_dir.glob("*.jpg"))) > 0
    any_tiff = len(list(resolve_dir.glob("*.tiff"))) > 0
    png_files = list(resolve_dir.glob("*.png"))
    any_png = len(png_files) > 0
    if not any_jpg and not any_tiff and not any_png:
        console.warning("No valid images found in directory, skipping metadata injection")
        return
    base_cmd = [exiftool_dir]
    update_tags = {
        "XPComment": image_email,
        "Artist": image_email,
        "XPAuthor": image_email,
        "XPTitle": image_title,
        "ImageDescription": image_title,
        "Title": image_title,
        "Description": image_title,
    }
    for tag, value in update_tags.items():
        base_cmd.append(f"-{tag}={value}")
    base_cmd.append("-overwrite_original_in_place")
    if any_jpg:
        full_dir = current_directory.resolve() / "*.jpg"
        base_cmd.append(str(full_dir))
        console.info("Injecting metadata into JP(e)G files...")
        proc = sp.Popen(base_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        proc.wait()
        base_cmd.pop()
    if any_tiff:
        full_dir = current_directory.resolve() / "*.tiff"
        base_cmd.append(str(full_dir))
        console.info("Injecting metadata into TIFF files...")
        proc = sp.Popen(base_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        proc.wait()

    encoded_data = f"{image_title} ({image_email})".encode("ascii")
    if any_png and conf.experimentals.png_tag:
        console.warning("PNG files will use experimental metadata injection, please report any issues")
        console.status("Injecting metadata into PNG files...")
        for idx, png_img in enumerate(png_files, 1):
            console.status(f"Injecting metadata into ({idx}/{len(png_files)})...")
            with png_img.open("ab") as af:
                # Write pad data
                af.write(b"\x00" * 4)
                af.write(encoded_data)
                af.write(b"\x00" * 4)
        console.stop_status("Injected metadata into PNG files")

def _run_pingo_and_verify(pingo_cmd: List[str]):
    proc = sp.Popen(pingo_cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    proc.wait()

    stdout = proc.stdout.read().decode("utf-8")
    stderr = proc.stderr.read().decode("utf-8")
    output = stdout + stderr


    for line in output.splitlines():
        line = line.strip()
        if line.endswith("\n"):
            line = line[:-1]
        if line.casefold().endswith("saved"):
            return line
    return None 


def optimize_images(pingo_path: str, target_directory: Path, aggresive: bool = False):
    resolve_dir = target_directory.resolve()
    any_jpg = len(list(resolve_dir.glob("*.jpg"))) > 0
    any_png = len(list(resolve_dir.glob("*.png"))) > 0
    any_webp = len(list(resolve_dir.glob("*.webp"))) > 0

    base_cmd = [pingo_path, "-strip"]
    if any_jpg:
        pingo_cmd = base_cmd[:] + ["-s0"]
        if aggresive:
            pingo_cmd.append("-jpgtype=1")
        pingo_cmd.append(str(resolve_dir / "*.jpg"))
        console.status("Optimizing JP(e)G files...")
        proc = _run_pingo_and_verify(pingo_cmd)
        end_msg = "Optimized JPG files!"
        if proc is not None:
            end_msg += f" [{proc}]"
        console.stop_status(end_msg)
        console.enter()

    if any_png:
        pingo_cmd = base_cmd[:] + ["-sb"]
        pingo_cmd.append(str(resolve_dir / "*.png"))
        console.status("Optimizing PNG files...")
        proc = _run_pingo_and_verify(pingo_cmd)
        end_msg = "Optimized PNG files!"
        if proc is not None:
            end_msg += f" [{proc}]"
        console.stop_status(end_msg)
        console.enter()

    if any_webp:
        pingo_cmd = base_cmd[:] + ["-s9"]
        pingo_cmd.append(str(resolve_dir / "*.webp"))
        console.status("Optimizing WEBP files...")
        proc = _run_pingo_and_verify(pingo_cmd)
        end_msg = "Optimized WEBP files!"
        if proc is not None:
            end_msg += f" [{proc}]"
        console.stop_status(end_msg)
        console.enter()


def format_archive_filename(
    m_title: int,
    m_year: int,
    publication_type: MPublication,
    rip_credit: str,
    bracket_type: str,
    m_volume_text: Optional[str] = None,
    rls_revision: Optional[int] = None,
):
    pair_left, pair_right = BRACKET_MAPPINGS.get(bracket_type.lower(), BRACKET_MAPPINGS["square"])

    act_vol = ""
    if m_volume_text is not None:
        act_vol = f" {m_volume_text}"
    archive_filename = TARGET_TITLE.format(
        mt=m_title,
        vol=act_vol,
        year=m_year,
        pt=publication_type.archive,
        c=rip_credit,
        cpa=pair_left,
        cpb=pair_right,
    )

    if rls_revision is not None and rls_revision > 1:
        archive_filename += " (v%d)" % rls_revision

    return archive_filename

def format_volume_text(
    m_volume: Optional[Union[int, float]] = None,
    m_chapter: Optional[Union[int, float]] = None,
) -> Optional[str]:
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
        if conf.defaults.ch_add_c_prefix:  # pragma: no cover
            volume_text = f"c{volume_text}"  # pragma: no cover
    if m_volume is not None:
        volume_text = f"v{format_daiz_like_numbering(m_volume, 2, False, '.')}"
    return volume_text

def format_daiz_like_filename(
    m_title: str,
    m_publisher: str,
    m_year: int,
    chapter_info: ChapterRange,
    page_number: str,
    publication_type: MPublication,
    rip_credit: str,
    bracket_type: str,
    m_volume: Optional[Union[int, float]] = None,
    extra_metadata: Optional[str] = None,
    image_quality: Optional[str] = None,  # {HQ}/{LQ} thing
    rls_revision: Optional[int] = None,
    chapter_extra_maps: Dict[int, List[ChapterRange]] = dict(),
    fallback_volume_name: str = "OShot",
):
    pub_type = ""
    if publication_type.image:
        pub_type = f"[{publication_type.image}]"

    chapter_num = f"{chapter_info.base:03d}"

    chapter_ex_data = ""
    if chapter_extra_maps:
        pack_data = chapter_extra_maps[chapter_info.base]
        pack_data.sort(key=lambda x: x.number)
        if len(pack_data) > 1:
            smallest = pack_data[1].floating
            for pack in pack_data:
                if pack.floating is not None and pack.floating < smallest:
                    smallest = pack.floating
            if smallest is not None and chapter_info.floating is not None:
                if smallest >= 5:
                    float_act = chapter_info.floating - 4
                    chapter_num += f"x{float_act}"
                else:
                    idx = pack_data.index(chapter_info)
                    chapter_ex_data = f" (c{chapter_num}.{chapter_info.floating})"
                    chapter_num += f"x{idx + 1}"
        else:
            floaty = chapter_info.floating
            if floaty is not None:
                if floaty >= 5:
                    chapter_num += f"x{floaty - 4}"
                else:
                    chapter_ex_data = f" (c{chapter_num}.{floaty})"
                    chapter_num += "x1"
    else:
        if chapter_info.floating is not None:
            if chapter_info.floating >= 5:
                chapter_num += f"x{chapter_info.floating - 4}"
            else:
                chapter_ex_data = f" (c{chapter_num}.{chapter_info.floating})"
                chapter_num += "x1"

    act_vol = fallback_volume_name
    if m_volume is not None:
        act_vol = f"v{format_daiz_like_numbering(m_volume, 2, separator='x')}"

    extra_name = " "
    if extra_metadata is not None:
        extra_name = f" [{extra_metadata}]"

    if not pub_type and not extra_name.strip():
        extra_name = ""
    elif pub_type and extra_name.strip():
        pub_type = f" {pub_type}"

    image_filename = TARGET_FORMAT_ALT.format(
        mt=m_title,
        ch=chapter_num,
        chex=chapter_ex_data,
        vol=act_vol,
        pg=page_number,
        ex=extra_name,
        pt=pub_type,
        pb=m_publisher or "Unknown Publisher",
        c=rip_credit,
    )
    if chapter_info.name is not None:
        image_filename = TARGET_FORMAT.format(
            mt=m_title,
            ch=chapter_num,
            chex=chapter_ex_data,
            vol=act_vol,
            pg=page_number,
            ex=extra_name,
            t=chapter_info.name,
            pt=pub_type,
            pb=m_publisher or "Unknown Publisher",
            c=rip_credit,
        )

    if image_quality is not None:
        image_filename += " {" + image_quality + "}"

    if rls_revision is not None and rls_revision > 1:
        image_filename += " {r%d}" % rls_revision

    return image_filename, format_archive_filename(
        m_title=m_title,
        m_year=m_year,
        publication_type=publication_type,
        rip_credit=rip_credit,
        bracket_type=bracket_type,
        m_volume_text=format_volume_text(m_volume, chapter_info.number),
        rls_revision=rls_revision,
    )

_PublicationRegexMatch = [
    "dig",
    "web",
    "c2c",
    "mag",
    "scan",
    "paper",
    "raw",
    "raw-d",
    "raw-dig",
    "raw-digital",
    "raw-m",
    "raw-mag",
    "raw-magazine",
]
class RegexCollection:
    _VolumeRegex = r"CHANGETHIS v(\d+\.?[\d]{1,2}?).*"  # pragma: no cover
    _OneShotRegex = r"CHANGETHIS .*"  # pragma: no cover
    # fmt: off
    _ChapterTitleRe = r"CHANGETHIS - c(?P<ch>\d+)(?P<ex>[\#x.][\d]{1,2})? \(?c?(?P<actual>[\d]{1,3}[\.][\d]{1,3})?\)?" \
                      r" ?\(?(?P<vol>v[\d]+(?P<volex>[\#x][\d]{1,2})?|[Oo][Ss]hot|[Oo]ne[ -]?[Ss]hot|[Nn][Aa])?\)?" \
                      r" ?- p[\d]+x?[\d]?\-?[\d]+x?[\d]?.* \[(?:PUBREPLACE)] (?:\[(?P<title>.*)\] )" \
                      r"?\[CHANGEPUBLISHER.*"  # pragma: no cover
    _ChapterBasicRe = r"CHANGETHIS - c(?P<ch>\d+)(?P<ex>[\#x.][\d]{1,2})? \(?c?(?P<actual>[\d]{1,3}[\.][\d]{1,3})?\)?" \
                      r" ?\(?(?P<vol>v[\d]+(?P<volex>[\#x][\d]{1,2})?|[Oo][Ss]hot|[Oo]ne[ -]?[Ss]hot|[Nn][Aa])?\)?" \
                      r" ?- p[\d]+x?[\d]?\-?[\d]+x?[\d]?.*"  # pragma: no cover
    # fmt: on
    @classmethod
    def volume_re(cls, title: str, limit_credit: Optional[str] = None) -> Pattern[str]:
        re_fmt = cls._VolumeRegex.replace("CHANGETHIS", re.escape(title))
        if limit_credit is not None:
            re_fmt += r"[\[\(]" + limit_credit + r".*"
        return re.compile(re_fmt)
    @overload
    @classmethod
    def chapter_re(cls, title: str) -> Pattern[str]:  # pragma: no cover
        ...
    @overload
    @classmethod
    def chapter_re(cls, title: str, publisher: str) -> Pattern[str]:  # pragma: no cover
        ...
    @classmethod
    def chapter_re(cls, title: str, publisher: Optional[str] = None) -> Pattern[str]:
        if publisher is None:
            return re.compile(cls._ChapterBasicRe.replace("CHANGETHIS", re.escape(title)))
        return re.compile(
            cls._ChapterTitleRe.replace("CHANGETHIS", re.escape(title))
            .replace("CHANGEPUBLISHER", re.escape(publisher))
            .replace("PUBREPLACE", "|".join(_PublicationRegexMatch))
        )
    @classmethod
    def cmx_re(cls) -> Pattern[str]:
        return re.compile(
            r"(?P<t>[\w\W\D\d\S\s]+?)(?:\- (?P<vol>v[\d]{1,3}))?(?P<volex>\.[\d]{1,2})? \- "
            r"p(?P<a>[\d]{1,3})\-?(?P<b>[\d]{1,3})?"
        )
    @classmethod
    def page_re(cls) -> Pattern[str]:
        return re.compile(r"(?P<any>.*)p(?P<a>[\d]{1,3})\-?(?P<b>[\d]{1,3})?(?P<anyback>.*)")