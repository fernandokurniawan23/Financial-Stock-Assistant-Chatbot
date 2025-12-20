import os
import json
import tempfile
import shutil
import pandas as pd
import yfinance as yf
from typing import Dict, Any, List, Optional
from modules.stock_tools import get_batch_stock_data

"""
WATCHLIST MODEL MODULE
----------------------
Responsibility: Data Persistence and Financial Calculations.
Handles loading/saving user JSON data and calculating portfolio performance metrics.
Contains NO UI code.
"""

DATA_DIR = "data"

def _get_user_filepath(username: str) -> str:
    """Sanitizes username and returns secure file path."""
    clean_name = "".join(x for x in username if x.isalnum() or x in "_-")
    return os.path.join(DATA_DIR, f"portfolio_{clean_name}.json")

def load_user_data(username: str) -> Dict[str, Any]:
    """
    Loads user data from disk. Returns default structure if new user.
    """
    default_data = {"watchlist": [], "portfolio": []}
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    file_path = _get_user_filepath(username)
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                loaded = json.load(f)
                # Merge to ensure schema integrity
                default_data.update(loaded)
                return default_data
        except (json.JSONDecodeError, IOError):
            return default_data
    return default_data

def save_user_data(username: str, data: Dict[str, Any]) -> None:
    """
    Atomically saves user data using write-and-replace strategy.
    """
    try:
        file_path = _get_user_filepath(username)
        # Write to temp file first to prevent corruption
        with tempfile.NamedTemporaryFile("w", delete=False, dir=DATA_DIR) as tmp:
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.move(tmp.name, file_path)
    except Exception as e:
        print(f"Error saving data: {e}")

def calculate_portfolio_performance(portfolio_items: List[Dict]) -> Dict[str, Any]:
    """
    Processes raw portfolio items, fetches real-time prices, and calculates 
    Profit/Loss summaries for IDR and USD.
    """
    if not portfolio_items:
        return {"items": [], "summary": {}}

    # 1. Bulk Fetch Data (Optimization)
    tickers = list(set([item["symbol"] for item in portfolio_items]))
    batch_data = get_batch_stock_data(tickers, period="1d")

    processed_items = []
    totals = {
        "IDR": {"invested": 0, "value": 0},
        "USD": {"invested": 0, "value": 0}
    }

    for idx, item in enumerate(portfolio_items):
        sym = item["symbol"]
        qty = float(item["quantity"])
        buy_price = float(item["buy_price"])
        currency = item.get("currency", "USD")
        
        # Price Retrieval
        curr_price = buy_price # Fallback
        is_error = True
        
        # Try retrieving from batch
        try:
            if not batch_data.empty:
                if isinstance(batch_data.columns, pd.MultiIndex) and sym in batch_data.columns.levels[0]:
                     val = batch_data[sym]["Close"].iloc[-1]
                     if not pd.isna(val): 
                         curr_price = val
                         is_error = False
                elif len(tickers) == 1 and "Close" in batch_data.columns:
                     val = batch_data["Close"].iloc[-1]
                     if not pd.isna(val): 
                         curr_price = val
                         is_error = False
        except Exception:
            pass

        # Calculations
        inv_val = buy_price * qty
        curr_val = curr_price * qty
        gain_loss = curr_val - inv_val
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