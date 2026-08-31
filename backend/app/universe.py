"""The pickable asset catalog.

`source` decides which provider fetches it: "yahoo" for anything with a Yahoo
ticker, "binance" for spot crypto pairs. Add your own rows freely — nothing
downstream is hardcoded to these symbols.
"""
from __future__ import annotations

CURRENCY_SYMBOL = {"INR": "\u20b9", "USD": "$", "GBP": "\u00a3", "JPY": "\u00a5", "HKD": "HK$"}

UNIVERSE: dict[str, list[dict[str, str]]] = {
    "Indices": [
        {"name": "NIFTY 50", "symbol": "^NSEI", "source": "yahoo", "currency": "INR"},
        {"name": "BANK NIFTY", "symbol": "^NSEBANK", "source": "yahoo", "currency": "INR"},
        {"name": "SENSEX", "symbol": "^BSESN", "source": "yahoo", "currency": "INR"},
        {"name": "NIFTY Midcap 150", "symbol": "NIFTYMIDCAP150.NS", "source": "yahoo", "currency": "INR"},
        {"name": "S&P 500", "symbol": "^GSPC", "source": "yahoo", "currency": "USD"},
        {"name": "Nasdaq 100", "symbol": "^NDX", "source": "yahoo", "currency": "USD"},
        {"name": "Dow Jones", "symbol": "^DJI", "source": "yahoo", "currency": "USD"},
        {"name": "FTSE 100", "symbol": "^FTSE", "source": "yahoo", "currency": "GBP"},
        {"name": "Nikkei 225", "symbol": "^N225", "source": "yahoo", "currency": "JPY"},
        {"name": "Hang Seng", "symbol": "^HSI", "source": "yahoo", "currency": "HKD"},
    ],
    "Stocks — India": [
        {"name": "Reliance Industries", "symbol": "RELIANCE.NS", "source": "yahoo", "currency": "INR"},
        {"name": "TCS", "symbol": "TCS.NS", "source": "yahoo", "currency": "INR"},
        {"name": "HDFC Bank", "symbol": "HDFCBANK.NS", "source": "yahoo", "currency": "INR"},
        {"name": "Infosys", "symbol": "INFY.NS", "source": "yahoo", "currency": "INR"},
        {"name": "ICICI Bank", "symbol": "ICICIBANK.NS", "source": "yahoo", "currency": "INR"},
        {"name": "Bharti Airtel", "symbol": "BHARTIARTL.NS", "source": "yahoo", "currency": "INR"},
        {"name": "State Bank of India", "symbol": "SBIN.NS", "source": "yahoo", "currency": "INR"},
        {"name": "Larsen & Toubro", "symbol": "LT.NS", "source": "yahoo", "currency": "INR"},
        {"name": "ITC", "symbol": "ITC.NS", "source": "yahoo", "currency": "INR"},
        {"name": "Tata Motors", "symbol": "TATAMOTORS.NS", "source": "yahoo", "currency": "INR"},
        {"name": "Axis Bank", "symbol": "AXISBANK.NS", "source": "yahoo", "currency": "INR"},
        {"name": "Sun Pharma", "symbol": "SUNPHARMA.NS", "source": "yahoo", "currency": "INR"},
    ],
    "Stocks — US": [
        {"name": "Apple", "symbol": "AAPL", "source": "yahoo", "currency": "USD"},
        {"name": "Microsoft", "symbol": "MSFT", "source": "yahoo", "currency": "USD"},
        {"name": "Nvidia", "symbol": "NVDA", "source": "yahoo", "currency": "USD"},
        {"name": "Alphabet", "symbol": "GOOGL", "source": "yahoo", "currency": "USD"},
        {"name": "Amazon", "symbol": "AMZN", "source": "yahoo", "currency": "USD"},
        {"name": "Meta", "symbol": "META", "source": "yahoo", "currency": "USD"},
        {"name": "Tesla", "symbol": "TSLA", "source": "yahoo", "currency": "USD"},
        {"name": "AMD", "symbol": "AMD", "source": "yahoo", "currency": "USD"},
        {"name": "JPMorgan", "symbol": "JPM", "source": "yahoo", "currency": "USD"},
    ],
    "Crypto": [
        {"name": "Bitcoin", "symbol": "BTCUSDT", "source": "binance", "currency": "USD"},
        {"name": "Ethereum", "symbol": "ETHUSDT", "source": "binance", "currency": "USD"},
        {"name": "Solana", "symbol": "SOLUSDT", "source": "binance", "currency": "USD"},
        {"name": "BNB", "symbol": "BNBUSDT", "source": "binance", "currency": "USD"},
        {"name": "XRP", "symbol": "XRPUSDT", "source": "binance", "currency": "USD"},
        {"name": "Cardano", "symbol": "ADAUSDT", "source": "binance", "currency": "USD"},
        {"name": "Dogecoin", "symbol": "DOGEUSDT", "source": "binance", "currency": "USD"},
    ],
    "Metals": [
        {"name": "Gold (futures)", "symbol": "GC=F", "source": "yahoo", "currency": "USD"},
        {"name": "Silver (futures)", "symbol": "SI=F", "source": "yahoo", "currency": "USD"},
        {"name": "Platinum", "symbol": "PL=F", "source": "yahoo", "currency": "USD"},
        {"name": "Copper", "symbol": "HG=F", "source": "yahoo", "currency": "USD"},
        {"name": "Gold ETF (India)", "symbol": "GOLDBEES.NS", "source": "yahoo", "currency": "INR"},
        {"name": "Silver ETF (India)", "symbol": "SILVERBEES.NS", "source": "yahoo", "currency": "INR"},
        {"name": "Gold miners (GDX)", "symbol": "GDX", "source": "yahoo", "currency": "USD"},
    ],
}

_INDEX = {a["symbol"]: {**a, "category": cat}
          for cat, rows in UNIVERSE.items() for a in rows}


def lookup(symbol: str) -> dict[str, str] | None:
    return _INDEX.get(symbol)


def as_list() -> list[dict[str, str]]:
    return [{"category": cat, **a} for cat, rows in UNIVERSE.items() for a in rows]
