# Resimi Python SDK

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![API v2 Compatible](https://img.shields.io/badge/Resimi%20API-v2%20compatible-7c3aed.svg)](https://resimismm.com/api-docs)

The official Python client for the **[Resimi](https://resimismm.com) SMM panel API v2**.

Resimi is a crypto-native SMM panel and wholesale API provider for resellers, agencies and developers. Fund your balance with cryptocurrency, browse a curated catalog of social media services, and automate ordering, status tracking, cancellations and refills from your own code or panel.

## Why Resimi

- **Crypto-native payments.** Top up with 300+ cryptocurrencies through NOWPayments, including Bitcoin (BTC), Tether (USDT), Ethereum (ETH) and Litecoin (LTC). No card or bank step.
- **No KYC.** Sign up with a username, email and password. No ID upload to deposit.
- **Low $2 minimum deposit.** Start small; your balance never expires. (Some coins carry higher network minimums at checkout.)
- **Curated catalog.** 2,147 active services at the time of writing (October 2026) instead of thousands of unvetted rows. Every price is public at [resimismm.com/services](https://resimismm.com/services), no signup needed.
- **Standard SMM panel API v2.** Same `key` + `action` format used across the industry, so existing integrations port over with little change. Full reference: [resimismm.com/api-docs](https://resimismm.com/api-docs).

## Installation

```bash
pip install git+https://github.com/Vetom1k/Resimi.git@v1.0.0
```

(PyPI release coming soon in v1.1)

Or install from source:

```bash
git clone https://github.com/Vetom1k/Resimi.git
cd Resimi
pip install .
```

Requires Python 3.8+ and [`requests`](https://pypi.org/project/requests/).

## Quickstart

Create an account at [resimismm.com](https://resimismm.com) and copy your API key from the **API** page in your dashboard.

```python
from resimi import ResimiClient

client = ResimiClient("YOUR_API_KEY")

print(client.get_balance())
# {'balance': '12.4800', 'currency': 'USD'}

services = client.get_services()
print(len(services), "services")

order = client.create_order(service_id=1234, link="https://instagram.com/yourprofile", quantity=1000)
print(order)
# {'order': 23501}
```

A runnable version lives in [`examples/quickstart.py`](examples/quickstart.py).

## Client options

```python
client = ResimiClient(
    api_key="YOUR_API_KEY",
    base_url="https://resimismm.com/api/v2",  # default
    timeout=30,                               # seconds, default
)
```

Keep your key out of source control, e.g. load it from an environment variable:

```python
import os
client = ResimiClient(os.environ["RESIMI_API_KEY"])
```

## API reference

Every method sends one `POST` request and returns the decoded JSON response.

### `get_balance()`

```python
client.get_balance()
# {'balance': '12.4800', 'currency': 'USD'}
```

### `get_services()`

Returns every active service.

```python
for svc in client.get_services():
    print(svc["service"], svc["category"], svc["name"], svc["rate"], svc["min"], svc["max"])
```

Each item contains `service` (ID), `category`, `name`, `type`, `rate` (USD per 1,000), `min`, `max`, and the `dripfeed`, `refill` and `cancel` flags.

### `create_order(service_id, link, quantity, runs=None, interval=None)`

Standard order:

```python
client.create_order(1234, "https://instagram.com/yourprofile", 1000)
# {'order': 23501}
```

Drip-feed order, delivered in `runs` batches every `interval` minutes (here: 7 daily runs of 100). Only services with `dripfeed` enabled accept these parameters, and you must pass both:

```python
client.create_order(1234, "https://instagram.com/yourprofile", 100, runs=7, interval=1440)
```

### `get_order_status(order_id)`

```python
client.get_order_status(23501)
# {'charge': '0.5000', 'start_count': '1520', 'status': 'In progress', 'remains': '250', 'currency': 'USD'}
```

### `get_multiple_orders_status(order_ids)`

Up to 100 orders per call. The result is keyed by order ID; unknown IDs come back as an error entry rather than raising.

```python
client.get_multiple_orders_status([23501, 23502, 99999])
# {
#   '23501': {'charge': '0.5000', 'start_count': '1520', 'status': 'Completed', 'remains': '0', 'currency': 'USD'},
#   '23502': {'charge': '0.3100', 'start_count': '0', 'status': 'Pending', 'remains': '100', 'currency': 'USD'},
#   '99999': {'error': 'Order not found'}
# }
```

### `cancel_order(order_id)`

Cancels an order where the service allows it. Refundable amounts are credited back to your balance.

```python
client.cancel_order(23501)
```

### `request_refill(order_id)`

Requests a refill for a completed order on a service with `refill` enabled. One refill request per order every 24 hours.

```python
client.request_refill(23501)
# {'refill': '5512'}
```

> Refill status lookup (`refill_status`) is not part of the Resimi API v2 yet, so the SDK does not expose it.

## Error handling

| Exception | When |
|---|---|
| `ResimiError` | Base class. Raised directly for network failures, timeouts and invalid arguments (caught before any request is sent). |
| `ResimiAPIError` | The API returned `{"error": "..."}`, a non-2xx status, or a non-JSON body. Has `.code` (HTTP status) and `.response` (decoded body or raw text). |
| `ResimiAuthError` | Subclass of `ResimiAPIError`: missing, invalid or unauthorised API key. |

```python
from resimi import ResimiClient, ResimiAPIError, ResimiAuthError, ResimiError

client = ResimiClient("YOUR_API_KEY")

try:
    client.create_order(1234, "https://instagram.com/yourprofile", 1000)
except ResimiAuthError:
    print("Check your API key.")
except ResimiAPIError as e:
    print("API error:", e, "| HTTP", e.code, "| body:", e.response)
except ResimiError as e:
    print("Request failed:", e)
```

## Running the tests

```bash
pip install requests
python3 -m unittest discover tests
```

The tests mock all HTTP calls; no API key or network access is needed.

## Links

- Website: [resimismm.com](https://resimismm.com)
- Services and prices: [resimismm.com/services](https://resimismm.com/services)
- API documentation: [resimismm.com/api-docs](https://resimismm.com/api-docs)
- Issues: [github.com/Vetom1k/Resimi/issues](https://github.com/Vetom1k/Resimi/issues)

## License

[MIT](LICENSE) © 2026 Resimi
