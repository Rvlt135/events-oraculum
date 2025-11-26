"""
Port for external sports data provider.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID


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


class SportsRepository(ABC):
    """Port for sports data repository."""

    @abstractmethod
    async def get_by_key(self, key: str) -> Optional[UUID]:
        """
        Get sport ID by key.

        Args:
            key: Sport key (e.g., 'football')

        Returns:
            Sport ID if found, None otherwise
        """
        pass

    @abstractmethod
    async def upsert(self, key: str, name: str) -> UUID:
        """
        Upsert sport by key.

        Args:
            key: Sport key
            name: Sport display name

        Returns:
            Sport ID
        """
        pass

    @abstractmethod
    async def get_all(self) -> list:
        """
        Get all sports.

        Returns:
            List of sports
        """
        pass