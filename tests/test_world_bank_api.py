import io
import json
import unittest

from src.world_bank_api import WorldBankApiError, WorldBankClient


class FakeResponse:
    status = 200

    def __init__(self, payload: object) -> None:
        self._buffer = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        self._buffer.close()

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def getcode(self) -> int:
        return self.status


class WorldBankClientTests(unittest.TestCase):
    def test_get_page_returns_valid_api_envelope(self) -> None:
        payload = [{"page": "1", "pages": "1", "total": "1"}, [{"id": "USA"}]]
        client = WorldBankClient(
            opener=lambda *_args, **_kwargs: FakeResponse(payload), sleep=lambda _: None
        )
        self.assertEqual(client.get_page("country", {"format": "json"}, page=1), payload)

    def test_get_page_rejects_invalid_api_envelope(self) -> None:
        client = WorldBankClient(
            opener=lambda *_args, **_kwargs: FakeResponse({"message": "invalid"}),
            sleep=lambda _: None,
            max_retries=1,
        )
        with self.assertRaises(WorldBankApiError) as context:
            client.get_page("country", {"format": "json"}, page=1)
        self.assertIn("Could not fetch", str(context.exception))


if __name__ == "__main__":
    unittest.main()
