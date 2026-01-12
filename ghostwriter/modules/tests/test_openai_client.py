from unittest import mock

from django.test import TestCase

from ghostwriter.factories import OpenAIConfigurationFactory
from ghostwriter.modules.openai_client import submit_prompt_to_assistant


class OpenAIClientTests(TestCase):
    def test_returns_none_when_disabled(self):
        config = OpenAIConfigurationFactory(enable=False)
        self.assertIsNone(submit_prompt_to_assistant("Example", config=config))

    @mock.patch("ghostwriter.modules.openai_client.OpenAI")
    def test_submits_prompt_and_returns_text(self, mock_openai):
        config = OpenAIConfigurationFactory(enable=True, prompt_id="prompt_123", api_key="sk-test")

        client = mock.Mock()
        response_payload = mock.Mock(output_text="First Second")
        client.responses.create.return_value = response_payload
        mock_openai.return_value = client

        response = submit_prompt_to_assistant("Prompt", config=config)
        self.assertEqual(response, "First Second")
        mock_openai.assert_called_once_with(api_key="sk-test")
        client.responses.create.assert_called_once_with(prompt={"id": "prompt_123"}, input="Prompt")
