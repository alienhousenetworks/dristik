from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseCrawler(ABC):
    @abstractmethod
    async def fetch_page(self, url: str) -> Dict[str, Any]:
        pass
