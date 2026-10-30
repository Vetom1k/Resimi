import unittest
from unittest import mock

import requests

import resimi
from resimi import ResimiAPIError, ResimiAuthError, ResimiClient, ResimiError

DUMMY_KEY = "test_dummy_key_0000"
BASE_URL = "https://resimismm.com/api/v2"


def fake_response(body=None, status=200, text=None):
    resp = mock.Mock()
    resp.status_code = status
    if text is not None:
        resp.text = text
        resp.json.side_effect = ValueError("not json")
    else:
        resp.text = repr(body)
        resp.json.return_value = body
    return resp


class PackageTests(unittest.TestCase):
    def test_metadata(self):
        self.assertEqual(resimi.__version__, "1.0.0")
        self.assertEqual(resimi.__author__, "Resimi")
        self.assertIs(resimi.ResimiClient, ResimiClient)

    def test_exception_hierarchy(self):
        self.assertTrue(issubclass(ResimiError, Exception))
        self.assertTrue(issubclass(ResimiAPIError, ResimiError))
        self.assertTrue(issubclass(ResimiAuthError, ResimiAPIError))


class AuthValidationTests(unittest.TestCase):
    def test_empty_key_rejected(self):
        for bad in ("", "   ", None, 123):
            with self.assertRaises(ResimiAuthError):
                ResimiClient(bad)

    def test_key_is_stripped_and_defaults_set(self):
        client = ResimiClient("  " + DUMMY_KEY + "\n")
        self.assertEqual(client.api_key, DUMMY_KEY)
        self.assertEqual(client.base_url, BASE_URL)
        self.assertEqual(client.timeout, 30)

    def test_custom_base_url_and_timeout(self):
        client = ResimiClient(DUMMY_KEY, base_url="https://example.test/api/v2/", timeout=5)
        self.assertEqual(client.base_url, "https://example.test/api/v2")
        self.assertEqual(client.timeout, 5)

    @mock.patch("resimi.client.requests.post")
    def test_invalid_key_raises_auth_error(self, post):
        post.return_value = fake_response({"error": "Invalid API key"})
        with self.assertRaises(ResimiAuthError) as ctx:
            ResimiClient(DUMMY_KEY).get_balance()
        self.assertEqual(str(ctx.exception), "Invalid API key")
        self.assertEqual(ctx.exception.code, 200)
        self.assertEqual(ctx.exception.response, {"error": "Invalid API key"})

    @mock.patch("resimi.client.requests.post")
    def test_child_panel_account_raises_auth_error(self, post):
        post.return_value = fake_response({"error": "API access not available on this account"})
        with self.assertRaises(ResimiAuthError):
            ResimiClient(DUMMY_KEY).get_services()


class PayloadTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("resimi.client.requests.post")
        self.post = patcher.start()
        self.addCleanup(patcher.stop)
        self.client = ResimiClient(DUMMY_KEY, timeout=12)

    def sent(self):
        args, kwargs = self.post.call_args
        return args, kwargs

    def test_request_shape(self):
        self.post.return_value = fake_response({"balance": "12.4800", "currency": "USD"})
        result = self.client.get_balance()
        self.assertEqual(result, {"balance": "12.4800", "currency": "USD"})
        args, kwargs = self.sent()
        self.assertEqual(args, (BASE_URL,))
        self.assertEqual(kwargs["data"], {"key": DUMMY_KEY, "action": "balance"})
        self.assertEqual(kwargs["timeout"], 12)
        self.assertTrue(kwargs["headers"]["User-Agent"].startswith("resimi-python/"))

    def test_get_services(self):
        services = [{"service": 1, "category": "Instagram", "name": "Followers", "rate": "0.30",
                     "min": "10", "max": "10000", "dripfeed": "1", "refill": "0", "cancel": "1",
                     "type": "Default"}]
        self.post.return_value = fake_response(services)
        self.assertEqual(self.client.get_services(), services)
        self.assertEqual(self.sent()[1]["data"], {"key": DUMMY_KEY, "action": "services"})

    def test_standard_order_payload(self):
        self.post.return_value = fake_response({"order": 23501})
        result = self.client.create_order(1234, "https://instagram.com/example", 1000)
        self.assertEqual(result, {"order": 23501})
        self.assertEqual(self.sent()[1]["data"], {
            "key": DUMMY_KEY,
            "action": "add",
            "service": 1234,
            "link": "https://instagram.com/example",
            "quantity": 1000,
        })

    def test_dripfeed_order_payload(self):
        self.post.return_value = fake_response({"order": 23502})
        self.client.create_order("1234", "https://instagram.com/example", "100", runs=7, interval=1440)
        self.assertEqual(self.sent()[1]["data"], {
            "key": DUMMY_KEY,
            "action": "add",
            "service": 1234,
            "link": "https://instagram.com/example",
            "quantity": 100,
            "runs": 7,
            "interval": 1440,
        })

    def test_dripfeed_needs_runs_and_interval(self):
        with self.assertRaises(ResimiError):
            self.client.create_order(1234, "https://instagram.com/example", 100, runs=7)
        with self.assertRaises(ResimiError):
            self.client.create_order(1234, "https://instagram.com/example", 100, interval=60)
        self.post.assert_not_called()

    def test_cancel_payload(self):
        self.post.return_value = fake_response({"success": True})
        self.client.cancel_order(98765)
        self.assertEqual(self.sent()[1]["data"], {"key": DUMMY_KEY, "action": "cancel", "order": 98765})

    def test_refill_payload(self):
        self.post.return_value = fake_response({"refill": "551"})
        self.assertEqual(self.client.request_refill("98765"), {"refill": "551"})
        self.assertEqual(self.sent()[1]["data"], {"key": DUMMY_KEY, "action": "refill", "order": 98765})


class StatusTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("resimi.client.requests.post")
        self.post = patcher.start()
        self.addCleanup(patcher.stop)
        self.client = ResimiClient(DUMMY_KEY)

    def test_single_status(self):
        body = {"charge": "0.5000", "start_count": "1520", "status": "In progress",
                "remains": "250", "currency": "USD"}
        self.post.return_value = fake_response(body)
        self.assertEqual(self.client.get_order_status(98765), body)
        data = self.post.call_args[1]["data"]
        self.assertEqual(data, {"key": DUMMY_KEY, "action": "status", "order": 98765})
        self.assertNotIn("orders", data)

    def test_single_status_not_found_raises(self):
        self.post.return_value = fake_response({"error": "Order not found"})
        with self.assertRaises(ResimiAPIError) as ctx:
            self.client.get_order_status(1)
        self.assertNotIsInstance(ctx.exception, ResimiAuthError)

    def test_multi_status(self):
        body = {
            "101": {"charge": "0.5000", "start_count": "0", "status": "Completed",
                    "remains": "0", "currency": "USD"},
            "102": {"error": "Order not found"},
        }
        self.post.return_value = fake_response(body)
        result = self.client.get_multiple_orders_status([101, "102"])
        self.assertEqual(result, body)
        data = self.post.call_args[1]["data"]
        self.assertEqual(data, {"key": DUMMY_KEY, "action": "status", "orders": "101,102"})
        self.assertNotIn("order", data)

    def test_multi_status_limits(self):
        with self.assertRaises(ResimiError):
            self.client.get_multiple_orders_status([])
        with self.assertRaises(ResimiError):
            self.client.get_multiple_orders_status(range(1, 102))
        self.post.assert_not_called()

    def test_invalid_order_ids(self):
        for bad in (0, -5, "abc", None):
            with self.assertRaises(ResimiError):
                self.client.get_order_status(bad)
        with self.assertRaises(ResimiError):
            self.client.get_multiple_orders_status([1, "x"])
        self.post.assert_not_called()


class ErrorHandlingTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("resimi.client.requests.post")
        self.post = patcher.start()
        self.addCleanup(patcher.stop)
        self.client = ResimiClient(DUMMY_KEY)

    def test_api_error_carries_code_and_response(self):
        body = {"error": "Insufficient balance. Please add funds."}
        self.post.return_value = fake_response(body)
        with self.assertRaises(ResimiAPIError) as ctx:
            self.client.create_order(1, "https://instagram.com/example", 100)
        err = ctx.exception
        self.assertNotIsInstance(err, ResimiAuthError)
        self.assertEqual(str(err), "Insufficient balance. Please add funds.")
        self.assertEqual(err.code, 200)
        self.assertEqual(err.response, body)

    def test_http_error_without_error_key(self):
        self.post.return_value = fake_response({"message": "Server error"}, status=500)
        with self.assertRaises(ResimiAPIError) as ctx:
            self.client.get_balance()
        self.assertEqual(ctx.exception.code, 500)

    def test_non_json_response(self):
        self.post.return_value = fake_response(status=502, text="<html>Bad Gateway</html>")
        with self.assertRaises(ResimiAPIError) as ctx:
            self.client.get_services()
        self.assertEqual(ctx.exception.code, 502)
        self.assertEqual(ctx.exception.response, "<html>Bad Gateway</html>")

    def test_timeout_wrapped(self):
        self.post.side_effect = requests.Timeout("read timed out")
        with self.assertRaises(ResimiError) as ctx:
            self.client.get_balance()
        self.assertNotIsInstance(ctx.exception, ResimiAPIError)
        self.assertIsInstance(ctx.exception.__cause__, requests.Timeout)

    def test_connection_error_wrapped(self):
        self.post.side_effect = requests.ConnectionError("refused")
        with self.assertRaises(ResimiError):
            self.client.get_services()


if __name__ == "__main__":
    unittest.main()
