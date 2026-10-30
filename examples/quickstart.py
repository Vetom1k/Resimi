"""Resimi SDK quickstart.

Usage:
    export RESIMI_API_KEY="your-api-key"        # from https://resimismm.com/api-access
    python examples/quickstart.py

Placing an order spends balance, so this script only does it when you also set
RESIMI_SERVICE_ID, RESIMI_LINK and RESIMI_QUANTITY.
"""

import os
import sys

from resimi import ResimiAPIError, ResimiAuthError, ResimiClient, ResimiError


def main():
    api_key = os.environ.get("RESIMI_API_KEY")
    if not api_key:
        sys.exit("Set RESIMI_API_KEY first (get one at https://resimismm.com/api-access).")

    client = ResimiClient(api_key)

    try:
        # 1. Balance
        balance = client.get_balance()
        print("Balance: {} {}".format(balance["balance"], balance["currency"]))

        # 2. Services
        services = client.get_services()
        print("{} active services. First five:".format(len(services)))
        for svc in services[:5]:
            print("  [{}] {} - ${}/1K (min {}, max {})".format(
                svc["service"], svc["name"], svc["rate"], svc["min"], svc["max"]))

        # 3. Place an order (opt-in)
        service_id = os.environ.get("RESIMI_SERVICE_ID")
        link = os.environ.get("RESIMI_LINK")
        quantity = os.environ.get("RESIMI_QUANTITY")
        if service_id and link and quantity:
            order = client.create_order(int(service_id), link, int(quantity))
            print("Order placed: #{}".format(order["order"]))
            status = client.get_order_status(order["order"])
            print("Status: {} | Remains: {}".format(status["status"], status["remains"]))
        else:
            print("Skipping order: set RESIMI_SERVICE_ID, RESIMI_LINK and RESIMI_QUANTITY to place one.")

    except ResimiAuthError as exc:
        sys.exit("Authentication failed: {}".format(exc))
    except ResimiAPIError as exc:
        sys.exit("API error: {} (HTTP {})".format(exc, exc.code))
    except ResimiError as exc:
        sys.exit("Request failed: {}".format(exc))


if __name__ == "__main__":
    main()
