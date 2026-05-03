import time
import pandas as pd
import yfinance as yf

START_DATE = "2016-05-01"
END_DATE   = "2026-05-01"
TICKERS    = []

def fetch_data(
    tickers: list = TICKERS,
    start: str = START_DATE,
    end: str = END_DATE,
    retries: int = 3,
    retry_delay: float = 2.0,
) -> pd.DataFrame:
    
    all_data = []
    failed   = []

    for ticker in tickers:
        for attempt in range(1, retries + 1):
            try:
                df = yf.Ticker(ticker).history(start=start, end=end)
                if df.empty:
                    raise ValueError(f"Empty response for {ticker}")
                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                df["Ticker"] = ticker
                all_data.append(df)
                break
            except Exception as exc:
                if attempt < retries:
                    print(f"  [{ticker}] attempt {attempt} failed: {exc}. Retrying...")
                    time.sleep(retry_delay)
                else:
                    print(f"  [{ticker}] SKIPPED after {retries} attempts: {exc}")
                    failed.append(ticker)

    if not all_data:
        raise RuntimeError("No data fetched. Check your internet connection or ticker list.")

    if failed:
        print(f"\n[data] Warning: {len(failed)} ticker(s) skipped: {failed}")

    data = pd.concat(all_data)
    print(f"[data] Fetched {len(data):,} rows for {len(all_data)} ticker(s)  ({start} -> {end})")
    return data
