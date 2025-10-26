"""
Port for sports data repository.
"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID


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
