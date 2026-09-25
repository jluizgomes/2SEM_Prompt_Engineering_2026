import os
import unittest
from unittest.mock import patch

from scripts import integration_test
from scripts import langfuse_ollama_setup


class LangfuseValidationTests(unittest.TestCase):
    def test_required_service_failure_is_not_a_skip(self):
        with self.assertRaises(AssertionError):
            integration_test.exige(
                "http://127.0.0.1:1",
                "Langfuse",
                "/api/public/health",
                timeout=0.1,
                obrigatorio=True,
            )

    def test_embedding_models_are_excluded_by_capability(self):
        response = {
            "models": [
                {
                    "name": "nomic-embed-text:latest",
                    "capabilities": ["embedding"],
                },
                {
                    "name": "chat-bom:latest",
                    "capabilities": ["completion"],
                },
            ]
        }

        with patch.dict(
            os.environ,
            {"OLLAMA_PORT": "11434", "CHAT_MODEL": "chat-bom"},
        ):
            with patch.object(
                langfuse_ollama_setup,
                "http",
                return_value=(200, response),
            ):
                models = langfuse_ollama_setup.modelos_do_ollama()

        self.assertEqual(models, ["chat-bom:latest"])

    def test_missing_score_configs_are_fatal(self):
        def fake_http(url, metodo="GET", payload=None, auth=None, timeout=15):
            if metodo == "GET":
                return 200, {"data": []}
            return 201, payload

        with patch.object(langfuse_ollama_setup, "http", side_effect=fake_http):
            with self.assertRaises(RuntimeError):
                langfuse_ollama_setup.semear_score_configs(
                    "http://localhost:3001",
                    ("public", "secret"),
                )

    def test_existing_score_configs_are_accepted(self):
        data = [
            {"name": config["name"], "isArchived": False}
            for config in langfuse_ollama_setup.SCORE_CONFIGS
        ]

        with patch.object(
            langfuse_ollama_setup,
            "http",
            return_value=(200, {"data": data}),
        ):
            count = langfuse_ollama_setup.semear_score_configs(
                "http://localhost:3001",
                ("public", "secret"),
            )

        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
