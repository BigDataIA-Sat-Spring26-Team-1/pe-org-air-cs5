"""
Decimal utilities for precise financial calculations.

All scoring calculations use Decimal to avoid floating-point precision errors,
which is critical for financial data where small deviations compound.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List


def to_decimal(value: float, places: int = 4) -> Decimal:
    """
    Convert float to Decimal with explicit precision.
    
    Args:
        value: Float value to convert
        places: Number of decimal places (default 4)
    
    Returns:
        Decimal with specified precision
    """
    return Decimal(str(value)).quantize(
        Decimal(10) ** -places,
        rounding=ROUND_HALF_UP
    )


def clamp(value: Decimal, min_val: Decimal = Decimal(0), max_val: Decimal = Decimal(100)) -> Decimal:
    """
    Clamp value to range [min_val, max_val].
    
    Args:
        value: Value to clamp
        min_val: Minimum bound (default 0)
        max_val: Maximum bound (default 100)
    
    Returns:
        Clamped value
    """
    return max(min_val, min(max_val, value))


def weighted_mean(values: List[Decimal], weights: List[Decimal]) -> Decimal:
    """
    Calculate weighted mean.
    
    Args:
        values: List of values
        weights: List of weights (must sum to 1.0 or will be normalized)
    
    Returns:
        Weighted mean as Decimal
    
    Raises:
        ValueError: If values and weights have different lengths
    """
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")
    
    if not values:
        return Decimal("0")
    
    total_weight = sum(weights)
    if total_weight == 0:
        return Decimal("0")
    
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / total_weight


def weighted_std_dev(
    values: List[Decimal],
    weights: List[Decimal],
    mean: Decimal
) -> Decimal:
    """
    Calculate weighted standard deviation.
    
    Args:
        values: List of values
        weights: List of weights
        mean: Pre-calculated weighted mean
    
    Returns:
        Weighted standard deviation as Decimal
    
    Raises:
        ValueError: If values and weights have different lengths
    """
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")
    
    if not values:
        return Decimal("0")
    
    total_weight = sum(weights)
    if total_weight == 0:
        return Decimal("0")
    
    variance = sum(w * (v - mean) ** 2 for v, w in zip(values, weights)) / total_weight
    return variance.sqrt()


def coefficient_of_variation(std_dev: Decimal, mean: Decimal) -> Decimal:
    """
    Calculate CV with zero-division protection.
    
    CV = std_dev / mean
    
    Args:
        std_dev: Standard deviation
        mean: Mean value
    
    Returns:
        Coefficient of variation (0 if mean is 0)
    """
    if mean == 0:
        return Decimal("0")
    
    return std_dev / mean
