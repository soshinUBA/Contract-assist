import yaml
import os

class PromptLoader:
    _instance = None
    _prompts = {}

    def __new__(cls, file_path="prompts/prompts.yaml"):
        """Implements Singleton pattern to load YAML once and reuse it."""
        if cls._instance is None:
            cls._instance = super(PromptLoader, cls).__new__(cls)
            cls._instance.load(file_path)
        return cls._instance

    def load(self, file_path):
        """Loads the YAML file and stores prompts in memory."""
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),file_path)
        with open(full_path, "r", encoding="utf-8") as file:
            self._prompts = yaml.safe_load(file)

    def get_prompt(self, category, key, **kwargs):
        """Fetches and formats a prompt dynamically."""
        return self._prompts.get(category, {}).get(key, "").format(**kwargs)

# Singleton instance (global access)
PROMPT_MANAGER = PromptLoader()
