from abc import ABC, abstractmethod
from ollama import ChatResponse

class BaseModel(ABC):
    @abstractmethod
    def generate(self, messages: list[dict]) -> ChatResponse:
        pass
