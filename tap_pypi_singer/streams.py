import logging
import random
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

import requests
from singer_sdk import typing as th  # JSON Schema typing helpers
from singer_sdk.streams import RESTStream


class PluginUsageStream(RESTStream):
    name = "plugin_usage"
    url_base = "https://api.pepy.tech/api/v2/projects/"
    plugins = None
    path = ""

    schema = th.PropertiesList(
        th.Property("plugin", th.StringType),
        th.Property("date", th.DateTimeType),
        th.Property("total_downloads", th.IntegerType),
        th.Property("downloads_day", th.IntegerType),
        th.Property("downloads_7d", th.IntegerType),
        th.Property("downloads_30d", th.IntegerType),
    ).to_dict()

    def set_meltano_plugins(self):
        taps = requests.get("https://hub.meltano.com/singer/api/v1/taps.json").json()
        targets = requests.get("https://hub.meltano.com/singer/api/v1/targets.json").json()
        dedup_plugins = {plugin_def.get("singer_name") for plugin_def in taps + targets}
        self.plugins = list(dedup_plugins)

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        return headers

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        yield response.json()

    def package_exists(self, plugin):
        response = requests.get("".join([self.url_base, plugin]))
        return response.status_code == 200

    def get_pypi_available_plugin(self):
        for plugin_name in self.plugins:
            self.plugins.remove(plugin_name)
            if self.package_exists(plugin_name):
                return plugin_name
            logging.info(f"Skipping plugin: {plugin_name}..")

    def get_url(self, context: Optional[dict]) -> str:
        # init plugins lookup
        if not self.plugins:
            self.set_meltano_plugins()

        plugin_name = self.get_pypi_available_plugin()

        self.path = plugin_name
        if not plugin_name:
            plugin_name = 'meltano'
        return "".join([self.url_base, plugin_name])

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Any:
        if self.plugins:
            # dummy next token until all plugins are iterated
            return self.path + str(random.random())

    def post_process(self, row: dict, context: Optional[dict] = None) -> dict:
        logging.info(f"Post processing {row.get('id')}")
        download_stats = row.get("downloads")
        today_cnt = 0
        month_cnt = 0
        week_cnt = 0
        max_date = datetime.today() - timedelta(days=1)
        if download_stats:
            for date, usage_dict in download_stats.items():
                d_date = datetime.strptime(date, "%Y-%m-%d")

                day_count = sum([count for _, count in usage_dict.items()])
                diff = (max_date - d_date)
                if d_date == max_date:
                    today_cnt += day_count
                if diff.days < 7:
                    week_cnt += day_count
                if diff.days < 30:
                    month_cnt += day_count

        return {
            "plugin": row.get("id"),
            "date": datetime.strftime(max_date, "%Y-%m-%d"),
            "total_downloads": row.get("total_downloads"),
            "downloads_day": today_cnt,
            "downloads_7d": week_cnt,
            "downloads_30d": month_cnt,
        }
