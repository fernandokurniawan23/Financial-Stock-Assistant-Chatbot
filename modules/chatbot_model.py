import os
import json
import pandas as pd
from typing import List, Dict, Any, Optional

# IMPORT TOOLS & UTILS
from modules.finance_tools import (
    get_stock_price, 
    calculate_SMA, 
    calculate_EMA,
    calculate_RSI, 
    calculate_MACD, 
    plot_interactive_chart,
    get_fundamental_data, 
    analyze_stock_recommendation, 
    analyze_news_relevance,
    get_my_portfolio
)

from modules.gemini_utils import load_gemini_model

from modules.watchlist_model import load_user_data, calculate_portfolio_performance

"""
CHATBOT MODEL MODULE
--------------------
Responsibility: Data Persistence, Tool Registry, and Context Injection Service.
Architecture: Implements an institutional-grade investment framework within the 
              LLM context, utilizing shared valuation logic from the Watchlist model.
"""

DATA_DIR = "data"
ROLE_USER = "user"
ROLE_MODEL = "model"

#CORE INITIALIZATION
def initialize_chat_session():
    """
    Menginisialisasi sesi chat Gemini dan menyuntikkan (Inject) semua tools.
    Fungsi ini dipanggil oleh main.py / chatbot.py.
    """
    # 1. semua fungsi tools
    tools_list = [
        get_stock_price, 
        calculate_SMA, 
        calculate_EMA,
        calculate_RSI, 
        calculate_MACD, 
        plot_interactive_chart,
        get_fundamental_data, 
        analyze_stock_recommendation, 
        analyze_news_relevance,
        get_my_portfolio
    ]

    # 2. Load model dengan tools list (Dependency Injection)
    model = load_gemini_model(tools=tools_list)
    
    # 3. Return chat object
    chat = model.start_chat(enable_automatic_function_calling=True)
    return chat


# CONTEXT SERVICE

def get_portfolio_context(username: str) -> str:
    """
    Retrieves the current portfolio state and constructs a strategic analysis 
    context based on Asset Allocation and Trend Following principles.

    Args:
        username (str): The unique identifier of the active user.

    Returns:
        str: A structured context payload containing the portfolio composition,
             valuation metrics, and strict analytical guidelines for the LLM.
    """
    try:
        # 1. Retrieve & Calculate Data
        user_data = load_user_data(username)
        raw_portfolio = user_data.get("portfolio", [])
        
        if not raw_portfolio:
            return "[SYSTEM INFO]: Portfolio is currently empty. No analysis possible."

        performance_data = calculate_portfolio_performance(raw_portfolio)
        items = performance_data.get("items", [])
        summary = performance_data.get("summary", {})
        
        if not items:
            return "[SYSTEM INFO]: Portfolio data exists but valuation returned no results."

        # 2. Data Transformation & Allocation Logic
        df = pd.DataFrame(items)
        
        # Calculate Aggregates for Weighting
        total_val_idr = summary.get("IDR", {}).get("value", 0)
        total_val_usd = summary.get("USD", {}).get("value", 0)
        
        # Projection
        target_cols = ['symbol', 'qty', 'buy_price', 'curr_price', 'gain_pct', 'curr_val', 'currency']
        valid_cols = [c for c in target_cols if c in df.columns]
        display_df = df[valid_cols].copy()
        
        # Compute Portfolio Weight (Allocation %)
        def calc_weight(row):
            total = total_val_idr if row['currency'] == 'IDR' else total_val_usd
            return (row['curr_val'] / total * 100) if total > 0 else 0
            
        display_df['weight'] = display_df.apply(calc_weight, axis=1)

        # String Formatting for LLM Context
        display_df['gain_fmt'] = display_df['gain_pct'].map('{:+.2f}%'.format)
        display_df['weight_fmt'] = display_df['weight'].map('{:.1f}%'.format)
        display_df['price_fmt'] = display_df['curr_price'].map('{:,.2f}'.format)
        display_df['val_fmt'] = display_df.apply(
            lambda x: f"{x['curr_val']:,.0f}" if x['currency'] == 'IDR' else f"{x['curr_val']:,.2f}", 
            axis=1
        )

        # Final Context Table
        final_table = display_df[['symbol', 'price_fmt', 'gain_fmt', 'weight_fmt', 'val_fmt', 'currency']]
        
        try:
            table_str = final_table.to_markdown(index=False)
        except ImportError:
            table_str = final_table.to_string(index=False)

        # Total Values for Prompt
        total_idr = summary.get("IDR", {}).get("value", 0)
        total_usd = summary.get("USD", {}).get("value", 0)

        # 3. Construct Institutional Analysis Prompt
        context_payload = (
            f"=== INSTITUTIONAL PORTFOLIO SNAPSHOT ({username}) ===\n"
            f"TOTAL ASSETS: IDR {total_idr:,.0f} | USD {total_usd:,.2f}\n\n"
            f"ASSET ALLOCATION TABLE:\n{table_str}\n"
            f"============================================\n"
            f"ANALYST FRAMEWORK (INSTITUTIONAL GRADE):\n"
            f"You are a Senior Investment Strategist. Analyze the portfolio using a hybrid of 'Trend Following' and 'Risk Rebalancing'.\n\n"
            f"1. RATING LOGIC (Buy/Hold/Sell):\n"
            f"   - STRONG BUY: If Gain is negative (-5% to -15%) AND the asset is a high-quality blue chip. Treat as Undervalued.\n"
            f"   - HOLD: If Gain is stable (0% to 20%). Maintain position.\n"
            f"   - TAKE PROFIT / TRIM: If Gain > 20% OR Weight > 40%. Recommend locking in profits or rebalancing.\n"
            f"   - CUT LOSS / SELL: If Gain < -15% (Trend Broken/Bearish).\n\n"
            f"2. RISK MANAGEMENT (Concentration Check):\n"
            f"   - Evaluate 'weight_fmt'. If a single asset exceeds 35% of the currency portfolio, issue a Concentration Risk warning.\n\n"
            f"INSTRUCTION:\n"
            f"Provide a tactical recommendation for each holding based strictly on the rules above. Be professional, concise, and objective."
        )
        return context_payload

    except Exception as e:
        return f"[SYSTEM ERROR in Portfolio Context]: {str(e)}"

# TOOL REGISTRY

def get_tools_map() -> Dict[str, Any]:
    """
    Returns the registry of callable tools available to the AI model.
    """
    return {
        "get_stock_price": get_stock_price,
        "calculate_SMA": calculate_SMA,
        "calculate_EMA": calculate_EMA,
        "calculate_RSI": calculate_RSI,
        "calculate_MACD": calculate_MACD,
        "plot_interactive_chart": plot_interactive_chart,
        "get_fundamental_data": get_fundamental_data,
        "analyze_stock_recommendation": analyze_stock_recommendation,
        "analyze_news_relevance": analyze_news_relevance,
        "get_my_portfolio": get_my_portfolio
    }

# PERSISTENCE LAYER

def _get_chat_filepath(username: str) -> str:
    """Generates the secure file path for chat history storage."""
    clean_name = "".join(x for x in username if x.isalnum() or x in "_-")
    return os.path.join(DATA_DIR, f"chat_history_{clean_name}.json")

def load_history(username: str) -> List[Dict[str, Any]]:
    """
    Loads chat history from the local filesystem.
    
    Returns:
        List[Dict[str, Any]]: The message history list.
    """
    filepath = _get_chat_filepath(username)
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_history(username: str, messages: List[Dict[str, Any]]) -> None:
    """
    Atomically saves chat history to the local filesystem.
    Removes non-serializable objects (e.g., charts) prior to dumping.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    filepath = _get_chat_filepath(username)
    try:
        serializable = []
        for msg in messages:
            clean = msg.copy()
            if "chart" in clean:
                clean["chart"] = None
            serializable.append(clean)
            
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f"Error persisting chat history: {e}")

def convert_to_gemini_format(ui_messages: List[Dict]) -> List[Dict]:
    """
    Adapts internal message format to the Gemini API schema.
    """
    gemini_history = []
    for msg in ui_messages:
        role = ROLE_USER if msg["role"] == ROLE_USER else ROLE_MODEL
        if msg.get("content"):
            gemini_history.append({"role": role, "parts": [msg["content"]]})
    return gemini_history