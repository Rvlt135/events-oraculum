"""
Port for external sports data provider.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class SportsProvider(ABC):
    """Port for external sports data provider."""

    @abstractmethod
    async def get_sports(self) -> List[Dict[str, Any]]:
        """
        Fetch sports data from external provider.
        
        Returns:
            List of sports data dictionaries
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close provider resources."""
        pass
