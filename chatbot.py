import streamlit as st
import google.generativeai as genai
from typing import Any

# MVC Modules
import modules.chatbot_model as model
import modules.chatbot_view as view

# Core Logic Modules
from modules.gemini_utils import load_gemini_model
from modules.auth_manager import check_quota_available, increment_usage

"""
CHATBOT CONTROLLER
------------------
Responsibility: Application Flow and Logic Orchestration.
Acts as the glue between the Data Model (History/Gemini) and the View (UI).
"""

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

def show_chatbot() -> None:
    """
    Main Entry Point for the Chatbot Module.
    Orchestrates: Auth -> Quota -> UI Rendering -> Event Loop.
    """
    
    # 1. Authentication Check
    current_user = st.session_state.get("username")
    is_logged_in = st.session_state.get("logged_in", False)
    
    if not is_logged_in or not current_user:
        view.render_access_denied()
        return

    # 2. Render Static UI
    view.render_header()

    # 3. Check Quota (Read-Only Mode Logic)
    is_allowed, status_msg = check_quota_available(current_user)
    
    if is_allowed:
        view.render_account_status(status_msg)
    else:
        view.render_quota_error(status_msg)
        # Note: We continue execution to show history, but input will be blocked later logic

    # 4. Initialize Session Data (Model)
    # Ensure history is loaded for the correct user
    if st.session_state.get("_chat_loaded_user") != current_user:
        st.session_state.messages = model.load_history(current_user)
        st.session_state["_chat_loaded_user"] = current_user
        # Reset Gemini session on user switch
        if "chat_session" in st.session_state:
            del st.session_state.chat_session

    # 5. Initialize Gemini AI Service
    try:
        if "chat_session" not in st.session_state:
            gemini_model = load_gemini_model()
            formatted_history = model.convert_to_gemini_format(st.session_state.messages)
            st.session_state.chat_session = gemini_model.start_chat(history=formatted_history)
    except Exception as e:
        st.error(f"AI Service Unavailable: {e}")
        return

    # 6. Render Chat History (View)
    view.render_chat_messages(st.session_state.messages)

    # 7. Interaction Event Loop
    # Only show input if quota is allowed
    if is_allowed:
        if prompt := view.get_user_input():
            
            # 7a. Double Check Quota (Concurrency safety)
            can_chat, _ = check_quota_available(current_user)
            if not can_chat:
                st.error("Quota limit reached just now.")
                st.stop()
            
            # 7b. Process User Input
            st.session_state.messages.append({"role": ROLE_USER, "content": prompt})
            with st.chat_message(ROLE_USER):
                st.markdown(prompt)
            model.save_history(current_user, st.session_state.messages)

            # 7c. Process Assistant Response
            process_ai_response(current_user, prompt)

def process_ai_response(user: str, prompt: str):
    """
    Handles the complex logic of sending data to AI, executing tools, 
    and updating the UI with results.
    """
    try:
        # Get Tools Registry from Model
        tools_map = model.get_tools_map()
        tools_list = list(tools_map.values())
        
        # Send Message
        response = st.session_state.chat_session.send_message(prompt, tools=tools_list)
        first_part = response.parts[0]
        
        # Logic: Function Calling vs Text
        if hasattr(first_part, "function_call") and first_part.function_call:
            _handle_tool_execution(user, first_part.function_call, tools_map)
        else:
            _handle_text_response(user, response.text)
            
        # Finalize
        increment_usage(user)
        st.rerun() # Refresh to show updated state clearly

    except Exception as e:
        st.error(f"Processing Error: {str(e)}")

def _handle_tool_execution(user: str, function_call: Any, tools_map: dict):
    """
    Private helper to execute a tool requested by the AI.
    """
    tool_name = function_call.name
    tool_args = dict(function_call.args)
    
    if tool_name in tools_map:
        with st.spinner(f"Analyzing data with {tool_name}..."):
            # Execute logic
            func = tools_map[tool_name]
            
            # Data cleaning for arguments (Model logic)
            if "window" in tool_args:
                tool_args["window"] = int(tool_args["window"])
            
            tool_result = func(**tool_args)
            
            # Send result back to AI
            final_res = st.session_state.chat_session.send_message(
                genai.protos.Part(
                    function_response=genai.protos.FunctionResponse(
                        name=tool_name, 
                        response={"content": tool_result}
                    )
                )
            )
            
            answer_text = final_res.text
            
            # Check if tool generated a chart (stored in session by finance_tools)
            current_chart = None
            if "last_chart" in st.session_state:
                current_chart = st.session_state.last_chart
                del st.session_state.last_chart

            # Update State
            st.session_state.messages.append({
                "role": ROLE_ASSISTANT, 
                "content": answer_text,
                "chart": current_chart
            })
            model.save_history(user, st.session_state.messages)

def _handle_text_response(user: str, text: str):
    """Private helper to handle simple text responses."""
    st.session_state.messages.append({
        "role": ROLE_ASSISTANT, 
        "content": text
    })
    model.save_history(user, st.session_state.messages)