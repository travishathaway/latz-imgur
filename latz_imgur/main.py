import urllib.parse

import httpx
from pydantic import BaseModel, Field
from latz.image import (
    ImageAPI,
    ImageAPIContextManager,
    ImageSearchResultSet,
    ImageSearchResult
)
from latz.plugins.types import ImageAPIPlugin
from latz.plugins.hookspec import hookimpl

PLUGIN_NAME = "imgur"


class ImgurBackendConfig(BaseModel):
    """
    Imgur requires the usage of an ``access_key`` and ``secret_key``
    when using their API. We expose these settings here so users of the CLI
    tool can use it.
    """

    access_key: str = Field(description="Access key for the Imgur API")

    secret_key: str = Field(description="Secret key for the Imgur API")


CONFIG_FIELDS = {
    f"{PLUGIN_NAME}_config": (
        ImgurBackendConfig,
        {"access_key": "", "secret_key": ""},
    )
}


class ImgurImageAPI(ImageAPI):
    """
    Implementation of ImageAPI for use with the Imgur API: https://apidocs.imgur.com/
    """

    #: Base URL for the Imgur API
    base_url = "https://api.imgur.com/3/"

    #: Endpoint used for searching images
    search_endpoint = "/gallery/search"

    def __init__(self, client_id: str, client: httpx.Client):
        """We use this initialization method to properly configure the ``httpx.Client`` object"""
        self._client_id = client_id
        self._headers = {"Authorization": f"Client-ID {client_id}"}
        self._client = client
        self._client.headers = httpx.Headers(self._headers)

    def search(self, query: str) -> ImageSearchResultSet:
        """
        Find images based on a ``query`` and return an ``ImageSearchResultSet``
        """
        search_url = urllib.parse.urljoin(self.base_url, self.search_endpoint)

        resp = self._client.get(search_url, params={"q": query})
        resp.raise_for_status()

        json_data = resp.json()

        breakpoint()

        search_results = tuple(
            ImageSearchResult(
                url=record.get("links", {}).get("download"),
                width=record.get("width"),
                height=record.get("height"),
            )
            for record in json_data.get("results", tuple())
        )

        return ImageSearchResultSet(search_results, json_data.get("total"))


class ImgurImageAPIContextManager(ImageAPIContextManager):
    """
    Context manager that returns the ``ImgurImageAPI`` we wish to use.
    This specific context manager handles setting up and tearing down the ``httpx.Client``
    connection that we use in this plugin.
    """

    def __enter__(self) -> ImgurImageAPI:
        self.__client = httpx.Client()
        return ImgurImageAPI(self._config.unsplash_config.access_key, self.__client)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__client.close()


@hookimpl
def image_api():
    """
    Registers our Imgur image API backend
    """
    return ImageAPIPlugin(
        name=PLUGIN_NAME,
        image_api_context_manager=ImgurImageAPIContextManager,
        config_fields=CONFIG_FIELDS,
    )
