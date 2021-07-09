"""PyPISinger tap class."""

from typing import List

from singer_sdk import Tap, Stream
from singer_sdk import typing as th  # JSON schema typing helpers

# TODO: Import your custom stream types here:
from tap_pypi_singer.streams import (
    UsageStream,
)

STREAM_TYPES = [
    UsageStream,
]


class TapPyPISinger(Tap):
    """PyPISinger tap class."""
    name = "tap-pypi-singer"

    # config_jsonschema = th.PropertiesList().to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]
