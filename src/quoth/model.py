import json
from asyncio import Lock, sleep
from datetime import datetime, timedelta
from itertools import count
from typing import Any, TypeVar

from aiohttp import ClientSession

from quoth.utils.config import read_from_env_var
from quoth.utils.logging import get_logger

LOGGER = get_logger(__name__)

T = TypeVar("T")


class RetryLater(Exception):
    def __init__(self, error: str, delay: timedelta, *args: object) -> None:
        self.error = error
        self.delay = delay
        super().__init__(*args)


class QuothModel:
    def __init__(self, model_name: str) -> None:
        token = read_from_env_var("HUGGINGFACE_TOKEN_FILE")
        self.headers = dict(Authorization=f"Bearer {token}")
        self.url = f"https://api-inference.huggingface.co/models/{model_name}"
        self.later = datetime.now()
        self.lock = Lock()

    def get_delay(self) -> timedelta:
        return self.later - datetime.now()

    async def set_delay(self, delta: timedelta) -> None:
        async with self.lock:
            if self.get_delay().total_seconds() < 0:
                self.later = datetime.now() + delta

    async def query(self, payload: Any) -> Any:
        data = json.dumps(payload)

        async with ClientSession() as session:
            async with session.post(
                url=self.url, headers=self.headers, data=data
            ) as response:
                status = response.status
                content = await response.json()

        def _get(key: str, default: T) -> T:
            if isinstance(content, dict):
                if isinstance(value := content.get(key), type(default)):
                    return value

            return default

        if status == 200:
            return content
        elif status == 429:
            raise RetryLater(
                error=_get("error", "Rate limit reached"),
                delay=timedelta(hours=1.0),
            )
        elif status == 503:
            raise RetryLater(
                error=_get("error", "Model is currently loading"),
                delay=timedelta(seconds=_get("estimated_time", 10.0)),
            )
        else:
            error = _get("error", "No error message provided")
            raise ValueError(f"Unexpected status: {status} ({error})")

    async def query_with_retries(self, payload: Any) -> Any:
        for retries in count():
            await sleep(self.get_delay().total_seconds())

            try:
                response = await self.query(payload)
            except RetryLater as retry:
                await self.set_delay(retry.delay)
                LOGGER.warning(
                    f"{retry.error} - Retrying in "
                    f"{self.get_delay().total_seconds():.2f} seconds "
                    f"({retries = })"
                )
            else:
                break

        return response

    async def embed(self, content: str) -> list[float]:
        response = await self.query_with_retries(content)

        if not isinstance(response, list) or not all(
            isinstance(value, float) for value in response
        ):
            raise ValueError(f"Expected response to be a list of floats")

        return response
