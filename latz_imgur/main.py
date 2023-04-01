import urllib.parse

import httpx
from pydantic import BaseModel, Field
from latz.image import ImageSearchResultSet, ImageSearchResult
from latz.plugins import hookimpl, SearchBackendHook
from latz.exceptions import SearchBackendError

#: Name of the plugin that will be referenced in our configuration
PLUGIN_NAME = "imgur"

#: Base URL for the Imgur API
BASE_URL = "https://api.imgur.com/3/"

#: Endpoint used for searching images
SEARCH_ENDPOINT = urllib.parse.urljoin(BASE_URL, "gallery/search")


class ImgurBackendConfig(BaseModel):
    """
    Imgur requires the usage of an ``access_key`` and ``secret_key``
    when using their API. We expose these settings here so users of the CLI
    tool can use it.
    """

    access_key: str = Field(description="Access key for the Imgur API")


async def _get(client: httpx.AsyncClient, url: str, query: str) -> dict:
    """
    Wraps `client.get` call in a try, except so that we raise
    an application specific exception instead.

    :raises SearchBackendError: Encountered during problems querying the API
    """
    try:
        resp = await client.get(url, params={"q": query})
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise SearchBackendError(str(exc), original=exc)

    json_data = resp.json()

    if not isinstance(json_data, dict):
        raise SearchBackendError("Received malformed response from search backend")

    return json_data


async def search(client, config, query: str) -> ImageSearchResultSet:
    client.headers = httpx.Headers(
        {
            "Authorization": f"Client-ID {config.search_backend_settings.imgur.access_key}"
        }
    )
    json_data = await _get(client, SEARCH_ENDPOINT, query)

    search_results = tuple(
        ImageSearchResult(
            url=record_image.get("link"),
            width=record_image.get("width"),
            height=record_image.get("height")
        )
        for record in json_data.get("data", tuple())
        for record_image in record.get("images", tuple())
    )

    return ImageSearchResultSet(
        search_results, len(search_results), search_backend=PLUGIN_NAME
    )


@hookimpl
def search_backend():
    """
    Registers our Imgur image API backend
    """
    return SearchBackendHook(
        name=PLUGIN_NAME,
        search=search,
        config_fields=ImgurBackendConfig(access_key=""),
    )
