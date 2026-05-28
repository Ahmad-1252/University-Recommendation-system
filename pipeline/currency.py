"""
Currency normalization — converts local currency amounts to USD.

Used by:
  - generate_programs.py  → adds *_usd columns at data generation time
  - retrain_model.py      → trains on USD-normalized features
  - recommendation_service.py → normalizes user budget at inference

These are STATIC rates (suitable for synthetic/annually-refreshed data).
For live production, integrate a currency API (e.g. exchangerate.host).
"""

from typing import Dict, Optional

# Static USD exchange rates (1 unit of foreign currency → how many USD)
# Source: approximate rates, sufficient for training data normalization.
USD_RATES: Dict[str, float] = {
    "USD": 1.0,
    "GBP": 1.27,
    "EUR": 1.08,
    "CAD": 0.74,
    "AUD": 0.65,
    "CHF": 1.13,
    "JPY": 0.0067,
    "CNY": 0.14,
    "INR": 0.012,
    "KRW": 0.00075,
    "SGD": 0.74,
    "HKD": 0.13,
    "SEK": 0.096,
    "DKK": 0.145,
    "NOK": 0.094,
    "NZD": 0.60,
    "RUB": 0.011,
    "BRL": 0.20,
    "MXN": 0.058,
    "SAR": 0.27,
    "AED": 0.27,
    "TRY": 0.031,
    "PLN": 0.25,
    "CZK": 0.044,
    "TWD": 0.031,
    "THB": 0.028,
    "IDR": 0.000063,
    "PKR": 0.0036,
    "EGP": 0.020,
    "ZAR": 0.055,
    "ARS": 0.0010,
    "CLP": 0.0011,
    "COP": 0.00024,
    "PHP": 0.018,
    "ILS": 0.27,
    "MYR": 0.22,
}


def to_usd(amount: float, currency: str) -> float:
    """Convert an amount from local currency to USD.

    Args:
        amount: value in local currency.
        currency: ISO 4217 currency code (e.g. "GBP", "JPY").

    Returns:
        Equivalent amount in USD.  If the currency is unknown,
        assumes 1:1 (treats it as USD) and logs a warning.
    """
    rate = USD_RATES.get(currency.upper(), None)
    if rate is None:
        import logging
        logging.getLogger(__name__).warning(
            f"Unknown currency '{currency}' — treating as 1:1 with USD"
        )
        rate = 1.0
    return round(amount * rate, 2)


def normalize_tuition_columns(
    tuition_domestic: float,
    tuition_international: float,
    cost_of_living: float,
    currency: str,
) -> Dict[str, float]:
    """Normalize all monetary columns to USD.

    Returns:
        Dict with keys: tuition_domestic_usd, tuition_international_usd,
        cost_of_living_usd.
    """
    return {
        "tuition_domestic_usd": to_usd(tuition_domestic, currency),
        "tuition_international_usd": to_usd(tuition_international, currency),
        "cost_of_living_usd": to_usd(cost_of_living, "USD"),  # COL is already in USD
    }
