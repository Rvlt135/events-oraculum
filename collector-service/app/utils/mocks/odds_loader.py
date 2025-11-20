"""
Utility for loading mock odds_models data from JSON file.
"""
import json
from pathlib import Path
from typing import List, Dict, Any


def load_mock_odds() -> List[Dict[str, Any]]:
    """
    Load mock odds_models data from JSON file.
    
    Reads JSON from app/utils/mocks/odds_list.json and returns list of dictionaries.
    
    Returns:
        List of odds_models data dictionaries
        
    Raises:
        FileNotFoundError: If odds_list.json file doesn't exist
        json.JSONDecodeError: If JSON file is malformed
        ValueError: If loaded data is not a list
    """
    # Get path relative to this file's directory
    mock_file = Path(__file__).parent / "odds_list.json"
    
    if not mock_file.exists():
        raise FileNotFoundError(
            f"Mock odds_models file not found: {mock_file}. "
            "Please create odds_list.json in app/utils/mocks/ directory."
        )
    
    try:
        with open(mock_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Failed to parse JSON from {mock_file}: {e.msg}",
            e.doc,
            e.pos
        ) from e
    
    if not isinstance(data, list):
        raise ValueError(
            f"Mock odds_models file {mock_file} must contain a JSON array (list), "
            f"but got {type(data).__name__}"
        )
    
    return data

