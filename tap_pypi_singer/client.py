"""REST client handling, including PyPISingerStream base class."""

import random
import time
from typing import Any, Iterable, Optional, cast

import backoff
import requests
from singer_sdk.streams import RESTStream


class PyPISingerStream(RESTStream):
    """PyPISinger stream class."""

    url_base = "https://pypistats.org/api/packages"
    plugins = None
    BLACKLISTED = ['target-pardot']

    def set_meltano_plugins(self):
        taps = requests.get("https://hub.meltano.com/singer/api/v1/taps.json").json()
        targets = requests.get("https://hub.meltano.com/singer/api/v1/targets.json").json()
        self.plugins = taps + targets

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

    def test_endpoint(self, plugin):
        response = requests.get("/".join([self.url_base, plugin, "recent"]))
        return response.status_code == 200

    def get_plugin(self):
        for plugin in self.plugins:
            self.plugins.remove(plugin)
            plugin_name = plugin.get("singer_name")
            if self.test_endpoint(plugin_name):
                return plugin_name

    def get_url(self, context: Optional[dict]) -> str:
        # init plugins lookup
        if not self.plugins:
            self.set_meltano_plugins()

        plugin = self.get_plugin()
        self.path = plugin
        return "/".join([self.url_base, plugin, "recent"])

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Any:
        if self.plugins:
            # dummy next token until all plugins are iterated
            return self.path + str(random.random())

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException),
        max_tries=5,
        giveup=lambda e: e.response is not None and e.response.status_code != 429 and 400 <= e.response.status_code < 500,
        factor=2,
    )
    def _request_with_backoff(
        self, prepared_request, context: Optional[dict]
    ) -> requests.Response:
        response = self.requests_session.send(prepared_request)
        if self._LOG_REQUEST_METRICS:
            extra_tags = {}
            if self._LOG_REQUEST_METRIC_URLS:
                extra_tags["url"] = cast(str, prepared_request.path_url)
            self._write_request_duration_log(
                endpoint=self.path,
                response=response,
                context=context,
                extra_tags=extra_tags,
            )
        if response.status_code == 429:
            self.logger.info("Rate Limit Hit, sleeping....")
            time.sleep(20)
            response.raise_for_status()
        if response.status_code in [401, 403]:
            self.logger.info("Failed request for {}".format(prepared_request.url))
            self.logger.info(
                f"Reason: {response.status_code} - {str(response.content)}"
            )
            raise RuntimeError(
                "Requested resource was unauthorized, forbidden, or not found."
            )
        elif response.status_code != 429 and response.status_code >= 400:
            self.logger.info("Failed request for {}".format(prepared_request.url))
            self.logger.info(
                f"Reason: {response.status_code} - {str(response.content)}"
            )
        self.logger.debug("Response received successfully.")
        return response
