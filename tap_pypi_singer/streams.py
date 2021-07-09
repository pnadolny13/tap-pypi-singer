"""Stream type classes for tap-pypi-singer."""

from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_pypi_singer.client import PyPISingerStream


class UsageStream(PyPISingerStream):
    name = "usage_stream"
    path = ""
    schema = th.PropertiesList(
        th.Property(
            "data", th.ObjectType(
                th.Property("last_day", th.IntegerType),
                th.Property("last_month", th.IntegerType),
                th.Property("last_week", th.IntegerType),
            )
        ),
        th.Property("package", th.StringType),
        th.Property("type", th.StringType),
    ).to_dict()
