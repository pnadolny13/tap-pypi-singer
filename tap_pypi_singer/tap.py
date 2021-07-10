from typing import List

from singer_sdk import Tap, Stream

from tap_pypi_singer.streams import (
    PluginUsageStream,
)

STREAM_TYPES = [
    PluginUsageStream,
]


class TapPyPISinger(Tap):
    """PyPISinger tap class."""
    name = "tap-pypi-singer"

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]
