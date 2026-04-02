import unittest

from mikrotik_jsmd5_loginv2 import MikroTikLoginTester


class DummyHistoryResponse:
    def __init__(self, status_code, url):
        self.status_code = status_code
        self.url = url


class DummyResponse:
    def __init__(self, text, status_code=200, history=None, url="http://portal/login"):
        self.text = text
        self.status_code = status_code
        self.history = history or []
        self.url = url


class MikroTikLoginTesterTests(unittest.TestCase):
    def setUp(self):
        self.tester = MikroTikLoginTester()

    def test_redirect_back_to_login_with_failure_text_is_not_success(self):
        response = DummyResponse(
            text="login again invalid voucher",
            history=[DummyHistoryResponse(302, "http://portal/login?dst=%2F")],
            url="http://portal/login?error=1",
        )

        self.assertFalse(self.tester.is_successful_response(response, "ABC123"))

    def test_redirect_to_status_page_is_success(self):
        response = DummyResponse(
            text="status connected remaining time logout",
            history=[DummyHistoryResponse(302, "http://portal/status")],
            url="http://portal/status",
        )

        self.assertTrue(self.tester.is_successful_response(response, "ABC123"))

    def test_extract_login_data_falls_back_to_hidden_chap_fields(self):
        page_html = """
        <form name="sendin" action="/login" method="post"></form>
        <input type="hidden" name="chap-id" value="01" />
        <input type="hidden" name="chap-challenge" value="11223344556677889900aabbccddeeff" />
        """

        action, chap_pair = self.tester.extract_login_data(page_html, "http://portal/login")

        self.assertEqual(action, "http://portal/login")
        self.assertEqual(
            chap_pair,
            (b"\x01", bytes.fromhex("11223344556677889900aabbccddeeff")),
        )


if __name__ == "__main__":
    unittest.main()
