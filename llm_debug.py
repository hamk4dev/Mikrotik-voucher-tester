import os
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - exercised indirectly in runtime checks
    OpenAI = None


DEFAULT_ANALYZE_MODEL = "gpt-5-mini"
MAX_ANALYSIS_CHARS = 12000


class OpenAIDebugAnalyzer:
    def __init__(self, model=DEFAULT_ANALYZE_MODEL, client=None, max_chars=MAX_ANALYSIS_CHARS):
        self.model = model
        self.client = client
        self.max_chars = max_chars

    @staticmethod
    def mask_secret(value, visible_prefix=2, visible_suffix=2):
        if value is None:
            return ""

        text = str(value)
        visible_total = visible_prefix + visible_suffix
        if len(text) <= visible_total:
            return "*" * len(text)

        return f"{text[:visible_prefix]}***{text[-visible_suffix:]}"

    @staticmethod
    def shorten_text(value, max_chars=MAX_ANALYSIS_CHARS):
        text = value or ""
        if len(text) <= max_chars:
            return text

        omitted = len(text) - max_chars
        head_length = max_chars // 2
        tail_length = max_chars - head_length
        return (
            f"{text[:head_length]}\n\n"
            f"[... truncated {omitted} characters ...]\n\n"
            f"{text[-tail_length:]}"
        )

    @staticmethod
    def format_attempt_context(context):
        redirect_items = context.get("redirect_chain", [])
        if redirect_items:
            redirect_chain = " -> ".join(
                f"{item.get('status_code', '?')} {item.get('url', '')}"
                for item in redirect_items
            )
        else:
            redirect_chain = "none"

        payload = context.get("request_payload", {})
        lines = [
            f"Portal: {context.get('portal', '')}",
            f"Voucher: {context.get('voucher_masked', '')}",
            f"Auth method: {context.get('auth_method', 'unknown')}",
            f"CHAP ID: {context.get('chap_id_hex', 'n/a')}",
            f"Challenge length: {context.get('challenge_length', 0)}",
            f"Login URL: {context.get('login_url', '')}",
            f"Login page URL: {context.get('login_page_url', '')}",
            f"POST target: {context.get('post_target', '')}",
            f"Request payload: {payload}",
            f"Login page status: {context.get('login_status_code', 'n/a')}",
            f"Final status: {context.get('final_status_code', 'n/a')}",
            f"Final URL: {context.get('final_url', '')}",
            f"Detected success: {context.get('success_detected', False)}",
            f"Redirect chain: {redirect_chain}",
            "",
            "Login page preview:",
            context.get("login_page_preview", ""),
            "",
            "Final response preview:",
            context.get("final_response_preview", ""),
        ]
        return "\n".join(lines).strip()

    def build_prompt(self, source_name, content):
        return (
            "You are diagnosing a MikroTik HotSpot voucher login failure.\n"
            "Analyze the supplied debug material and answer using these headings:\n"
            "1. Summary\n"
            "2. Likely Root Cause\n"
            "3. Evidence\n"
            "4. Recommended Next Steps\n"
            "Focus on CHAP vs PAP behavior, redirects, hidden form fields, HTTP responses, "
            "and response-body indicators. If the evidence is insufficient, say exactly what "
            "additional data should be captured next.\n\n"
            f"Source: {source_name}\n\n"
            f"Debug material:\n{content}"
        )

    def get_client(self):
        if self.client is not None:
            return self.client

        if OpenAI is None:
            raise RuntimeError(
                "OpenAI SDK not installed. Install it with: pip install openai"
            )

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export the API key before using LLM analysis."
            )

        return OpenAI()

    def analyze_text(self, source_name, content):
        client = self.get_client()
        response = client.responses.create(
            model=self.model,
            input=self.build_prompt(source_name, self.shorten_text(content, self.max_chars)),
        )

        output_text = getattr(response, "output_text", "")
        if output_text:
            return output_text.strip()

        output = getattr(response, "output", None)
        if output is not None:
            return str(output)

        return str(response)

    def analyze_file(self, file_path):
        file_name = Path(file_path).name
        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            content = handle.read()
        return self.analyze_text(file_name, content)
