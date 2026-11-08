"""Characterization tests for unmodified scripts/fetch_fmp.py fallbacks."""

from research.tests.conftest import load_script

fmp = load_script("fetch_fmp.py", "fetch_fmp_original")


def _route(endpoint, api_key, params=None):
    if endpoint.startswith("key-metrics"):
        return [{}]
    if endpoint.startswith("profile"):
        return [
            {
                "companyName": "Example",
                "mktCap": 2_000_000_000,
                "enterpriseValue": 2_200_000_000,
                "sector": "Technology",
                "industry": "Software",
                "price": 20,
            }
        ]
    if endpoint.startswith("ratios"):
        return [{}]
    if endpoint.startswith("income-statement"):
        return [{"ebitda": 80}]
    if endpoint.startswith("balance-sheet"):
        return [
            {
                "totalCurrentAssets": 30,
                "totalCurrentLiabilities": 10,
                "propertyPlantEquipmentNet": 40,
                "totalDebt": 5,
                "totalStockholdersEquity": 20,
            }
        ]
    raise AssertionError(endpoint)


def test_missing_operating_income_uses_ebitda(monkeypatch):
    monkeypatch.setattr(fmp, "fmp_get", _route)
    row = fmp.fetch_stock_data("EX", "key")
    assert row["ebit"] == 80
    assert row["data_complete"] is True


def test_zero_operating_income_is_replaced_by_ebitda(monkeypatch):
    def route(endpoint, api_key, params=None):
        if endpoint.startswith("income-statement"):
            return [{"operatingIncome": 0, "ebitda": 80}]
        return _route(endpoint, api_key, params)

    monkeypatch.setattr(fmp, "fmp_get", route)
    row = fmp.fetch_stock_data("EX", "key")
    assert row["ebit"] == 80


def test_zero_current_liabilities_drops_working_capital(monkeypatch):
    def route(endpoint, api_key, params=None):
        if endpoint.startswith("balance-sheet"):
            return [
                {
                    "totalCurrentAssets": 30,
                    "totalCurrentLiabilities": 0,
                    "propertyPlantEquipmentNet": 40,
                    "totalDebt": 5,
                    "totalStockholdersEquity": 20,
                }
            ]
        if endpoint.startswith("income-statement"):
            return [{"operatingIncome": 12}]
        return _route(endpoint, api_key, params)

    monkeypatch.setattr(fmp, "fmp_get", route)
    row = fmp.fetch_stock_data("EX", "key")
    assert row["net_working_capital"] is None
    assert row["current_ratio"] is None
    assert row["current_liabilities"] == 0


def test_zero_total_debt_falls_through_to_components(monkeypatch):
    def route(endpoint, api_key, params=None):
        if endpoint.startswith("balance-sheet"):
            return [
                {
                    "totalCurrentAssets": 30,
                    "totalCurrentLiabilities": 10,
                    "propertyPlantEquipmentNet": 40,
                    "totalDebt": 0,
                    "longTermDebt": 7,
                    "shortTermDebt": 1,
                    "totalStockholdersEquity": 20,
                }
            ]
        if endpoint.startswith("income-statement"):
            return [{"operatingIncome": 12}]
        return _route(endpoint, api_key, params)

    monkeypatch.setattr(fmp, "fmp_get", route)
    row = fmp.fetch_stock_data("EX", "key")
    assert row["total_debt"] == 8
