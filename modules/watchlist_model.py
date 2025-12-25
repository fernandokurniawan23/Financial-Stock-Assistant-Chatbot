import os
import json
import tempfile
import shutil
import pandas as pd
from typing import Dict, Any, List, Optional
from modules.stock_tools import get_batch_stock_data

"""
WATCHLIST MODEL MODULE
----------------------
Responsibility: Data Persistence and Portfolio Valuation.
Handles atomic file I/O operations and computes financial metrics 
(Market Value, Unrealized P/L, Allocation) using robust market data retrieval.
"""

DATA_DIR = "data"

def _get_user_filepath(username: str) -> str:
    """
    Constructs the secure file path for a specific user's data.

    Args:
        username (str): The unique identifier for the user.

    Returns:
        str: Absolute or relative file path to the user's JSON store.
    """
    clean_name = "".join(x for x in username if x.isalnum() or x in "_-")
    return os.path.join(DATA_DIR, f"portfolio_{clean_name}.json")

def load_user_data(username: str) -> Dict[str, Any]:
    """
    Retrieves user data from the persistent storage.
    
    Returns a default schema structure if the file does not exist 
    or encounters read errors.

    Args:
        username (str): The target user.

    Returns:
        Dict[str, Any]: The user's watchlist and portfolio data.
    """
    default_data = {"watchlist": [], "portfolio": []}
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    file_path = _get_user_filepath(username)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                loaded = json.load(f)
                default_data.update(loaded)
                return default_data
        except (json.JSONDecodeError, IOError):
            return default_data
    return default_data

def save_user_data(username: str, data: Dict[str, Any]) -> None:
    """
    Persists user data to disk using an atomic write-replace strategy.
    
    Uses a temporary file to prevent data corruption during the write process.

    Args:
        username (str): The target user.
        data (Dict[str, Any]): The data payload to serialize.
    """
    try:
        file_path = _get_user_filepath(username)
        # Write to temp file first to ensure atomicity
        with tempfile.NamedTemporaryFile("w", delete=False, dir=DATA_DIR) as tmp:
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.move(tmp.name, file_path)
    except Exception as e:
        print(f"I/O Error in save_user_data: {e}")

def calculate_portfolio_performance(portfolio_items: List[Dict]) -> Dict[str, Any]:
    """
    Computes portfolio valuation metrics based on real-time market data.

    Utilizes a 5-day lookback window with forward-fill propagation to ensure 
    valid pricing availability during market closures or cross-timezone latency.

    Args:
        portfolio_items (List[Dict]): Raw list of holding objects.

    Returns:
        Dict[str, Any]: A dictionary containing processed items with calculated 
                        metrics and aggregated totals by currency.
    """
    if not portfolio_items:
        return {"items": [], "summary": {}}

    # Extract unique tickers for batch processing
    tickers = list(set([item["symbol"] for item in portfolio_items]))
    
    # Fetch market data with 5-day lookback to capture Last Closing Price
    try:
        batch_data = get_batch_stock_data(tickers, period="5d")
    except Exception:
        batch_data = pd.DataFrame()

    processed_items = []
    totals = {
        "IDR": {"invested": 0, "value": 0},
        "USD": {"invested": 0, "value": 0}
    }

    # Propagate last valid observation forward to handle non-trading days
    if not batch_data.empty:
        batch_data = batch_data.ffill()

    for idx, item in enumerate(portfolio_items):
        sym = item["symbol"]
        qty = float(item["quantity"])
        buy_price = float(item["buy_price"])
        currency = item.get("currency", "USD")
        
        curr_price = 0.0
        is_error = True
        
        # Price Retrieval Logic
        try:
            if not batch_data.empty:
                # Handle MultiIndex DataFrame (Multiple Tickers)
                if isinstance(batch_data.columns, pd.MultiIndex):
                    if sym in batch_data.columns.levels[0]:
                        series = batch_data[sym]["Close"]
                        val = series.dropna().iloc[-1]
                        if pd.notna(val):
                            curr_price = float(val)
                            is_error = False
                            
                # Handle Single Index DataFrame (Single Ticker or Flattened)
                elif "Close" in batch_data.columns:
                    if len(tickers) == 1:
                        val = batch_data["Close"].dropna().iloc[-1]
                        if pd.notna(val):
                            curr_price = float(val)
                            is_error = False
                    elif sym in batch_data.columns:
                        val = batch_data[sym].dropna().iloc[-1]
                        if pd.notna(val):
                            curr_price = float(val)
                            is_error = False
        except Exception:
            pass

        # Metric Calculations
        inv_val = buy_price * qty
        curr_val = curr_price * qty
        gain_loss = curr_val - inv_val
        
        # Prevent division by zero
        gain_pct = (gain_loss / inv_val * 100) if inv_val > 0 else 0

        # Aggregation
        target_curr = "IDR" if currency == "IDR" else "USD"
        totals[target_curr]["invested"] += inv_val
        totals[target_curr]["value"] += curr_val

        processed_items.append({
            "index": idx,
            "symbol": sym,
            "qty": qty,
            "buy_price": buy_price,
            "curr_price": curr_price,
            "curr_val": curr_val,
            "gain_loss": gain_loss,
            "gain_pct": gain_pct,
            "currency": currency,
            "is_error": is_error
        })
        
    return {"items": processed_items, "summary": totals}