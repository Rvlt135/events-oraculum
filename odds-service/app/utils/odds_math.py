"""
Utility functions for odds calculations with proper Decimal rounding.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Union, Optional


def safe_avg(values: List[Union[float, Decimal]], default: Optional[Decimal] = Decimal("0.00")) -> Optional[Decimal]:
    """
    Calculate average of values and round to 2 decimal places.
    
    Args:
        values: List of numeric values (float or Decimal)
        default: Value to return if list is empty. Defaults to Decimal("0.00").
                 Pass None to return None for empty lists (e.g., for draw odds).
    
    Returns:
        Decimal rounded to 2 decimal places, or default if list is empty
    """
    if not values:
        return default
    
    avg = Decimal(sum(values) / len(values))
    quantize_value = Decimal("0.01")
    return avg.quantize(quantize_value, rounding=ROUND_HALF_UP)


def safe_best(values: List[Union[float, Decimal]], default: Optional[Decimal] = Decimal("0.00")) -> Optional[Decimal]:
    """
    Calculate maximum (best) value and round to 2 decimal places.
    
    Args:
        values: List of numeric values (float or Decimal)
        default: Value to return if list is empty. Defaults to Decimal("0.00").
                 Pass None to return None for empty lists (e.g., for draw odds).
    
    Returns:
        Decimal rounded to 2 decimal places, or default if list is empty
    """
    if not values:
        return default
    
    best = Decimal(max(values))
    quantize_value = Decimal("0.01")
    return best.quantize(quantize_value, rounding=ROUND_HALF_UP)

