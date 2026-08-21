from __future__ import annotations

import unittest

from easy_language_learning_tool.config.logging import redact_secrets


class LoggingTests(unittest.TestCase):
    def test_common_api_key_shapes_are_redacted(self) -> None:
        message = "api_key=secret-value Authorization failed for sk-example123456789"
        redacted = redact_secrets(message)
        self.assertNotIn("secret-value", redacted)
        self.assertNotIn("sk-example123456789", redacted)
        self.assertEqual(redacted.count("[REDACTED]"), 2)


if __name__ == "__main__":
    unittest.main()
