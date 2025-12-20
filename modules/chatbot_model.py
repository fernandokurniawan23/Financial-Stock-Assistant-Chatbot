import os
import json
from typing import List, Dict, Any
from modules.finance_tools import (
    get_stock_price, calculate_SMA, calculate_EMA,
    calculate_RSI, calculate_MACD, plot_interactive_chart,
    get_fundamental_data, get_my_portfolio,
    analyze_stock_recommendation, analyze_portfolio_holdings,
    analyze_news_relevance
)

"""
CHATBOT MODEL MODULE
--------------------
Responsibility: Data Persistence, Tool Management, and API Formatting.
This module handles file I/O for chat history and maps available tools 
for the AI model. It does NOT interact with the UI.
"""

# Constants
DATA_DIR = "data"
ROLE_USER = "user"
ROLE_MODEL = "model"

def get_tools_map() -> Dict[str, Any]:
    """
    Returns the registry of available financial tools for the AI.
    """
    return {
        "get_stock_price": get_stock_price,
        "calculate_SMA": calculate_SMA,
        "calculate_EMA": calculate_EMA,
        "calculate_RSI": calculate_RSI,
        "calculate_MACD": calculate_MACD,
        "plot_interactive_chart": plot_interactive_chart,
        "get_fundamental_data": get_fundamental_data,
        "analyze_news_relevance": analyze_news_relevance,
        "get_my_portfolio": get_my_portfolio,
        "analyze_stock_recommendation": analyze_stock_recommendation,
        "analyze_portfolio_holdings": analyze_portfolio_holdings
    }

def _get_chat_filepath(username: str) -> str:
    """Helper: Sanitizes username and constructs file path."""
    clean_name = "".join(x for x in username if x.isalnum() or x in "_-")
    return os.path.join(DATA_DIR, f"chat_history_{clean_name}.json")

def load_history(username: str) -> List[Dict[str, Any]]:
    """
    Loads chat history from the local file system.
    Returns empty list if file not found or corrupted.
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
    Persists chat history to the local file system.
    Removes non-serializable objects (like Plotly figures) before saving.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    filepath = _get_chat_filepath(username)
    try:
        # Create serializable copy (exclude Plotly figures)
        serializable_msgs = []
        for msg in messages:
            clean_msg = msg.copy()
            if "chart" in clean_msg:
                clean_msg["chart"] = None
            serializable_msgs.append(clean_msg)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(serializable_msgs, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving chat history: {e}")

def convert_to_gemini_format(ui_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transforms UI-specific message format into Gemini API compatible format.
    """
    gemini_history = []
    for msg in ui_messages:
        # Map 'assistant' role to 'model' for API
        api_role = ROLE_USER if msg["role"] == ROLE_USER else ROLE_MODEL
        content_text = msg.get("content", "")
        if content_text:
            gemini_history.append({
                "role": api_role,
                "parts": [content_text]
            })
    return gemini_history