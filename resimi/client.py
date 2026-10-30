"""HTTP client for the Resimi SMM panel API v2."""

from typing import Any, Dict, Iterable, List, Optional, Union

import requests

from ._version import __version__
from .exceptions import ResimiAPIError, ResimiAuthError, ResimiError

DEFAULT_BASE_URL = "https://resimismm.com/api/v2"

#: Maximum number of order IDs the API accepts in one multi-status request.
MAX_ORDERS_PER_REQUEST = 100

# Error messages the API returns when the key itself is the problem.
_AUTH_ERRORS = (
    "invalid api key",
    "api access not available",
    "api not available on child panels",
)

OrderId = Union[int, str]


class ResimiClient:
    """Client for the Resimi API v2 (https://resimismm.com/api-docs).

    Every call is a form-encoded ``POST`` carrying your API key and an
    ``action``. Errors returned by the API as ``{"error": "..."}`` are raised
    as :class:`~resimi.exceptions.ResimiAPIError` (or
    :class:`~resimi.exceptions.ResimiAuthError` for key problems).

    Args:
        api_key: Your API key from https://resimismm.com/api-access.
        base_url: API endpoint. Defaults to ``https://resimismm.com/api/v2``.
        timeout: Request timeout in seconds.
    """

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout: int = 30) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ResimiAuthError("An API key is required.")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # Transport
    # ------------------------------------------------------------------ #

    def _post(self, data: Dict[str, Any]) -> Any:
        """Send one API call and return the decoded JSON body.

        Raises:
            ResimiAuthError: the API rejected the key.
            ResimiAPIError: the API returned ``{"error": ...}``, a non-2xx
                status, or a body that is not JSON.
            ResimiError: the request could not be completed (network error,
                timeout).
        """
        payload = {"key": self.api_key}
        payload.update(data)
        try:
            resp = requests.post(
                self.base_url,
                data=payload,
                timeout=self.timeout,
                headers={"User-Agent": "resimi-python/" + __version__},
            )
        except requests.RequestException as exc:
            raise ResimiError("Request to Resimi API failed: {}".format(exc)) from exc

        try:
            body = resp.json()
        except ValueError:
            raise ResimiAPIError(
                "Resimi API returned a non-JSON response (HTTP {}).".format(resp.status_code),
                code=resp.status_code,
                response=resp.text,
            )

        if isinstance(body, dict) and "error" in body:
            message = str(body["error"])
            if message.lower().startswith(_AUTH_ERRORS):
                raise ResimiAuthError(message, code=resp.status_code, response=body)
            raise ResimiAPIError(message, code=resp.status_code, response=body)

        if resp.status_code >= 400:
            raise ResimiAPIError(
                "Resimi API returned HTTP {}.".format(resp.status_code),
                code=resp.status_code,
                response=body,
            )
        return body

    @staticmethod
    def _order_id(value: OrderId) -> int:
        try:
            order_id = int(value)
        except (TypeError, ValueError):
            raise ResimiError("Invalid order ID: {!r}".format(value))
        if order_id <= 0:
            raise ResimiError("Invalid order ID: {!r}".format(value))
        return order_id

    # ------------------------------------------------------------------ #
    # Account
    # ------------------------------------------------------------------ #

    def get_balance(self) -> Dict[str, Any]:
        """Return the account balance, e.g. ``{"balance": "12.4800", "currency": "USD"}``."""
        return self._post({"action": "balance"})

    # ------------------------------------------------------------------ #
    # Catalog
    # ------------------------------------------------------------------ #

    def get_services(self) -> List[Dict[str, Any]]:
        """Return every active service.

        Each item has ``service``, ``category``, ``name``, ``type``, ``rate``
        (USD per 1,000), ``min``, ``max``, ``dripfeed``, ``refill`` and
        ``cancel``.
        """
        return self._post({"action": "services"})

    # ------------------------------------------------------------------ #
    # Orders
    # ------------------------------------------------------------------ #

    def create_order(
        self,
        service_id: int,
        link: str,
        quantity: int,
        runs: Optional[int] = None,
        interval: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Place an order and return ``{"order": <order_id>}``.

        For a drip-feed order pass both ``runs`` (number of deliveries) and
        ``interval`` (minutes between deliveries); ``quantity`` is then the
        amount per run. Only services with ``dripfeed`` enabled accept them.
        """
        if (runs is None) != (interval is None):
            raise ResimiError("Drip-feed orders need both `runs` and `interval`.")

        data = {
            "action": "add",
            "service": int(service_id),
            "link": link,
            "quantity": int(quantity),
        }
        if runs is not None:
            data["runs"] = int(runs)
            data["interval"] = int(interval)
        return self._post(data)

    def get_order_status(self, order_id: OrderId) -> Dict[str, Any]:
        """Return the status of one order.

        Example: ``{"charge": "0.5000", "start_count": "1520",
        "status": "In progress", "remains": "250", "currency": "USD"}``.
        """
        return self._post({"action": "status", "order": self._order_id(order_id)})

    def get_multiple_orders_status(self, order_ids: Iterable[OrderId]) -> Dict[str, Dict[str, Any]]:
        """Return the status of up to 100 orders in one call.

        The result is keyed by order ID (as a string). An ID that does not
        exist or belongs to another account maps to
        ``{"error": "Order not found"}``; it does not raise.
        """
        ids = [self._order_id(o) for o in order_ids]
        if not ids:
            raise ResimiError("At least one order ID is required.")
        if len(ids) > MAX_ORDERS_PER_REQUEST:
            raise ResimiError(
                "At most {} order IDs per request.".format(MAX_ORDERS_PER_REQUEST)
            )
        return self._post({"action": "status", "orders": ",".join(str(i) for i in ids)})

    def cancel_order(self, order_id: OrderId) -> Dict[str, Any]:
        """Cancel an order. Refundable amounts are credited back to your balance."""
        return self._post({"action": "cancel", "order": self._order_id(order_id)})

    # ------------------------------------------------------------------ #
    # Refills
    # ------------------------------------------------------------------ #

    def request_refill(self, order_id: OrderId) -> Dict[str, Any]:
        """Request a refill for a completed order and return ``{"refill": "<id>"}``.

        Only services with ``refill`` enabled qualify, and one refill request
        per order is accepted every 24 hours.
        """
        return self._post({"action": "refill", "order": self._order_id(order_id)})
