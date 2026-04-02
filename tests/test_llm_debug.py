import os
import tempfile
import unittest

from llm_debug import OpenAIDebugAnalyzer


class FakeResponse:
    output_text = "1. Summary\n2. Likely Root Cause\n3. Evidence\n4. Recommended Next Steps"


class FakeResponsesAPI:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.responses = FakeResponsesAPI()


class OpenAIDebugAnalyzerTests(unittest.TestCase):
    def test_mask_secret_obscures_middle_characters(self):
        self.assertEqual(OpenAIDebugAnalyzer.mask_secret("ABCDEFGH"), "AB***GH")

    def test_format_attempt_context_uses_masked_payload(self):
        context = {
            "portal": "http://portal",
            "voucher_masked": "AB***34",
            "auth_method": "chap-md5",
            "chap_id_hex": "01",
            "challenge_length": 16,
            "login_url": "http://portal/login",
            "login_page_url": "http://portal/login",
            "post_target": "http://portal/login",
            "request_payload": {"username": "AB***34", "password": "12***ef"},
            "login_status_code": 200,
            "final_status_code": 200,
            "final_url": "http://portal/login?error=1",
            "success_detected": False,
            "redirect_chain": [{"status_code": 302, "url": "http://portal/login?error=1"}],
            "login_page_preview": "<form>login</form>",
            "final_response_preview": "invalid voucher",
        }

        formatted = OpenAIDebugAnalyzer.format_attempt_context(context)

        self.assertIn("AB***34", formatted)
        self.assertNotIn("ABCDEFGH", formatted)
        self.assertIn("invalid voucher", formatted)

    def test_analyze_file_uses_responses_api(self):
        fake_client = FakeClient()
        analyzer = OpenAIDebugAnalyzer(model="gpt-5-mini", client=fake_client)

        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            handle.write("sample debug log")
            temp_path = handle.name

        try:
            output = analyzer.analyze_file(temp_path)
        finally:
            os.remove(temp_path)

        self.assertIn("Summary", output)
        self.assertEqual(fake_client.responses.calls[0]["model"], "gpt-5-mini")
        self.assertIn("sample debug log", fake_client.responses.calls[0]["input"])


if __name__ == "__main__":
    unittest.main()
