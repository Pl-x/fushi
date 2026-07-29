"""Synchronous HTTP client for Paystack's REST API."""
import json
from typing import Any
from urllib.parse import quote

import requests


class InvalidDataError(Exception):
    """Raised when Paystack rejects a request payload or returns an API error."""


class UnwantedDataError(InvalidDataError):
    """Compatibility alias for older route-level validation handling."""


class _PaystackResource:
    def __init__(self, client: "Paystack", path: str):
        self.client = client
        self.path = path

    def create(self, **data: Any) -> dict[str, Any]:
        return self.client._request("POST", self.path, data)


class _TransactionResource:
    def __init__(self, client: "Paystack"):
        self.client = client

    def initialize(self, **data: Any) -> dict[str, Any]:
        return self.client._request("POST", "/transaction/initialize", data)

    def verify(self, reference: str) -> dict[str, Any]:
        return self.client._request("GET", f"/transaction/verify/{quote(reference, safe='')}")

    def charge(self, **data: Any) -> dict[str, Any]:
        return self.client._request("POST", "/transaction/charge_authorization", data)


class _TransferResource:
    def __init__(self, client: "Paystack"):
        self.client = client

    def initiate(self, **data: Any) -> dict[str, Any]:
        return self.client._request("POST", "/transfer", data)

    def verify(self, reference: str) -> dict[str, Any]:
        return self.client._request("GET", f"/transfer/verify/{quote(reference, safe='')}")


class Paystack:
    """Minimal Paystack client with the route layer's existing method names."""

    base_url = "https://api.paystack.co"

    def __init__(self, secret_key: str, timeout: int = 20):
        if not secret_key:
            raise ValueError("A Paystack secret key is required")
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.transaction = _TransactionResource(self)
        self.transfer_recipient = _PaystackResource(self, "/transferrecipient")
        self.transfer = _TransferResource(self)
        self.refund = _PaystackResource(self, "/refund")

    def _request(self, method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {key: value for key, value in (data or {}).items() if value is not None}
        # Paystack expects metadata as a stringified JSON object even when the
        # surrounding request body is JSON.
        if isinstance(payload.get("metadata"), (dict, list)):
            payload["metadata"] = json.dumps(payload["metadata"])
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                json=payload if method != "GET" else None,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise InvalidDataError("Unable to reach Paystack") from error
        try:
            body = response.json()
        except ValueError as error:
            raise InvalidDataError("Paystack returned an invalid response") from error
        if response.status_code >= 400 or not body.get("status", False):
            raise InvalidDataError(body.get("message", "Paystack request failed"))
        return body
