from dataclasses import dataclass

__all__ = (
    "MPublication",
    "M_PUBLICATION_TYPES",
    "TARGET_FORMAT",
    "TARGET_FORMAT_ALT",
    "TARGET_TITLE",
)


@dataclass
class MPublication:
    image: str
    """Used in the image filename"""
    archive: str
    """Used in the archive filename"""
    description: str
    """Description, this will be used in the config command for what it means."""


M_PUBLICATION_TYPES = {
    "digital": MPublication("dig", "Digital", "Digital manga release from Amazon, etc."),
    "magazine": MPublication("mag", "c2c", "Magazine release, can be used for scanlation batch."),
    "scan": MPublication("c2c", "c2c", "Scanned manga release, physical turned to digital."),
    "web": MPublication(
        "web", "Digital", "Webcomic release, from many kind of website that are not using volume format."
    ),
    "mix": MPublication("mix", "Digital", "Mixed release format"),
    "none": MPublication("", "Digital", "No publication type used in image filename, Digital in archive filename"),
}

TARGET_FORMAT = "{mt} - c{ch}{chex} ({vol}) - p{pg}{ex}{pt} [{t}] [{pb}] [{c}]"  # noqa
TARGET_FORMAT_ALT = "{mt} - c{ch}{chex} ({vol}) - p{pg}{ex}{pt} [{pb}] [{c}]"  # noqa
TARGET_TITLE = "{mt}{vol} ({year}) ({pt}) {cpa}{c}{cpb}"