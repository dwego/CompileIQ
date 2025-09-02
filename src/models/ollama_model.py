from ollama import chat, ChatResponse
from src.models.base_model import BaseModel

class OllamaModel(BaseModel):
    def __init__(self, model_name: str = "qwen2.5-coder:1.5b", options: dict = None):  # type: ignore
        self.model_name = model_name
        self.options = options or {}

    def generate(self, messages: list[dict]) -> ChatResponse:
        resp: ChatResponse = chat(
            model=self.model_name,
            messages=messages,
            options=self.options
        )
        return resp
