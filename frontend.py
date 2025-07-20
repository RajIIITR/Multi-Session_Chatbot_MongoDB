"""
Streamlit Frontend for Chat Summarization API
Clean, simple UI for user interaction with LangChain MongoDB backend
"""

import streamlit as st
import requests
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

class ChatAPIClient:
    """
    Simple API client for interacting with FastAPI backend
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def store_chat_session(self, session_id: str, chat_messages: List[Dict]) -> bool:
        """Store complete chat session"""
        try:
            response = requests.post(
                f"{self.base_url}/chats",
                json={
                    "session_id": session_id,
                    "chat_messages": chat_messages
                }
            )
            response.raise_for_status()
            return True
        except Exception as e:
            st.error(f"Error storing chat: {e}")
            return False
    
    def add_single_message(self, session_id: str, message: str, message_type: str = "human") -> bool:
        """Add single message using LangChain"""
        try:
            response = requests.post(
                f"{self.base_url}/chats/message",
                params={
                    "session_id": session_id,
                    "message": message,
                    "message_type": message_type
                }
            )
            response.raise_for_status()
            return True
        except Exception as e:
            st.error(f"Error adding message: {e}")
            return False
    
    def get_chat_session(self, session_id: str) -> Optional[Dict]:
        """Get chat session"""
        try:
            response = requests.get(f"{self.base_url}/chats/{session_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error retrieving chat: {e}")
            return None
    
    def summarize_chat(self, session_id: str) -> Optional[str]:
        """Generate chat summary"""
        try:
            response = requests.post(
                f"{self.base_url}/chats/summarize",
                json={"session_id": session_id}
            )
            response.raise_for_status()
            return response.json().get("summary")
        except Exception as e:
            st.error(f"Error generating summary: {e}")
            return None
    
    def ask_question(self, session_id: str, question: str) -> Optional[str]:
        """Ask question with context"""
        try:
            response = requests.post(
                f"{self.base_url}/chats/ask",
                json={
                    "session_id": session_id,
                    "question": question
                }
            )
            response.raise_for_status()
            return response.json().get("answer")
        except Exception as e:
            st.error(f"Error asking question: {e}")
            return None
    
    def chat_with_memory(self, session_id: str, message: str) -> Optional[str]:
        """Chat using LangChain memory"""
        try:
            response = requests.post(
                f"{self.base_url}/chats/chat",
                json={
                    "session_id": session_id,
                    "message": message
                }
            )
            response.raise_for_status()
            return response.json().get("ai_response")
        except Exception as e:
            st.error(f"Error in memory chat: {e}")
            return None
    
    def get_chat_history(self, limit: int = 5) -> List[Dict]:
        """Get recent chat history"""
        try:
            response = requests.get(
                f"{self.base_url}/users/demo_user/chats",
                params={"limit": limit}
            )
            response.raise_for_status()
            return response.json().get("conversations", [])
        except Exception as e:
            st.error(f"Error getting history: {e}")
            return []
    
    def search_chats(self, query: str) -> List[Dict]:
        """Search chats"""
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={"query": query, "limit": 10}
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except Exception as e:
            st.error(f"Error searching: {e}")
            return []
    
    def delete_session(self, session_id: str) -> bool:
        """Delete chat session"""
        try:
            response = requests.delete(f"{self.base_url}/chats/{session_id}")
            response.raise_for_status()
            return True
        except Exception as e:
            st.error(f"Error deleting session: {e}")
            return False

def init_session_state():
    """Initialize Streamlit session state"""
    if 'client' not in st.session_state:
        st.session_state.client = ChatAPIClient(API_BASE_URL)
    
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    
    if 'current_chat' not in st.session_state:
        st.session_state.current_chat = []

def display_sidebar():
    """Display sidebar with session management"""
    st.sidebar.title("🤖 Chat API")
    
    # Current session
    if st.session_state.current_session_id:
        st.sidebar.success(f"Session: {st.session_state.current_session_id[:8]}...")
        
        if st.sidebar.button("🗑️ Delete Session"):
            if st.session_state.client.delete_session(st.session_state.current_session_id):
                st.session_state.current_session_id = None
                st.session_state.current_chat = []
                st.sidebar.success("Session deleted!")
                st.rerun()
    else:
        st.sidebar.warning("No active session")
    
    # New session
    if st.sidebar.button("🆕 New Session", type="primary"):
        st.session_state.current_session_id = str(uuid.uuid4())
        st.session_state.current_chat = []
        st.sidebar.success("New session created!")
        st.rerun()
    
    # Load session
    st.sidebar.subheader("📂 Load Session")
    load_session_id = st.sidebar.text_input("Session ID:")
    if st.sidebar.button("📂 Load") and load_session_id:
        data = st.session_state.client.get_chat_session(load_session_id)
        if data:
            st.session_state.current_session_id = load_session_id
            st.session_state.current_chat = data.get("chat_messages", [])
            st.sidebar.success("Session loaded!")
            st.rerun()
    
    # API Status
    st.sidebar.subheader("🌐 API Status")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            st.sidebar.success("✅ Connected")
        else:
            st.sidebar.error("❌ Error")
    except:
        st.sidebar.error("❌ Unreachable")

def display_chat_tab():
    """Display basic chat interface"""
    st.header("💬 Basic Chat")
    
    # Message input
    message = st.text_area("Your message:", height=100, placeholder="Type your message...")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Send Message", type="primary"):
            if message and st.session_state.current_session_id:
                if st.session_state.client.add_single_message(
                    st.session_state.current_session_id, message, "human"
                ):
                    # Refresh chat
                    data = st.session_state.client.get_chat_session(
                        st.session_state.current_session_id
                    )
                    if data:
                        st.session_state.current_chat = data.get("chat_messages", [])
                    st.success("Message sent!")
                    st.rerun()
            elif not st.session_state.current_session_id:
                st.warning("Create a session first")
            else:
                st.warning("Enter a message")
    
    with col2:
        if st.button("🧠 Chat with Memory"):
            if message and st.session_state.current_session_id:
                with st.spinner("AI thinking..."):
                    ai_response = st.session_state.client.chat_with_memory(
                        st.session_state.current_session_id, message
                    )
                    
                    if ai_response:
                        st.success("AI Response:")
                        st.write(ai_response)
                        
                        # Refresh chat
                        data = st.session_state.client.get_chat_session(
                            st.session_state.current_session_id
                        )
                        if data:
                            st.session_state.current_chat = data.get("chat_messages", [])
                        st.rerun()
    
    # Display conversation
    if st.session_state.current_chat:
        st.subheader("💬 Conversation")
        for msg in st.session_state.current_chat:
            if msg.get("message_type") == "human":
                st.markdown(f"👤 **You:** {msg['message']}")
            else:
                st.markdown(f"🤖 **AI:** {msg['message']}")
        
    else:
        st.info("No messages yet. Start a conversation!")

def display_summary_tab():
    """Display summarization interface"""
    st.header("📄 Chat Summary")
    
    if st.session_state.current_session_id:
        if st.button("📊 Generate Summary", type="primary"):
            with st.spinner("Generating summary..."):
                summary = st.session_state.client.summarize_chat(
                    st.session_state.current_session_id
                )
                
                if summary:
                    st.subheader("📋 Summary")
                    st.write(summary)
    else:
        st.warning("No active session to summarize")
    
    # Summarize any session
    st.subheader("📊 Summarize Any Session")
    session_to_summarize = st.text_input("Enter Session ID:")
    
    if st.button("📊 Summarize") and session_to_summarize:
        with st.spinner("Generating summary..."):
            summary = st.session_state.client.summarize_chat(session_to_summarize)
            
            if summary:
                st.subheader(f"📋 Summary for {session_to_summarize[:8]}...")
                st.write(summary)

def display_qa_tab():
    """Display Q&A interface"""
    st.header("❓ Ask Questions")
    
    if st.session_state.current_session_id:
        question = st.text_area("Your question:", placeholder="Ask about the conversation...")
        
        if st.button("❓ Ask", type="primary") and question:
            with st.spinner("Getting answer..."):
                answer = st.session_state.client.ask_question(
                    st.session_state.current_session_id, question
                )
                
                if answer:
                    st.subheader("💡 Answer")
                    st.write(answer)
                    
                    # Refresh chat to show Q&A in history
                    data = st.session_state.client.get_chat_session(
                        st.session_state.current_session_id
                    )
                    if data:
                        st.session_state.current_chat = data.get("chat_messages", [])
    else:
        st.warning("No active session for context")

def display_history_tab():
    """Display chat history and search"""
    st.header("📚 Chat History")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Recent Conversations")
        limit = st.selectbox("Number of conversations:", [3, 5, 10])
        
        if st.button("📚 Load Recent"):
            conversations = st.session_state.client.get_chat_history(limit)
            
            for i, conv in enumerate(conversations, 1):
                with st.expander(f"Session {i} - {conv['message_count']} messages"):
                    st.write(f"**ID:** {conv['session_id']}")
                    st.write(f"**Messages:** {conv['message_count']}")
                    st.write(f"**First:** {conv['first_message']}")
                    st.write(f"**Last:** {conv['last_message']}")
                    
                    if st.button("💬 Load", key=f"load_{i}"):
                        st.session_state.current_session_id = conv['session_id']
                        st.session_state.current_chat = conv['full_chat']
                        st.rerun()
    
    with col2:
        st.subheader("🔍 Search")
        search_query = st.text_input("Search term:")
        
        if st.button("🔍 Search") and search_query:
            results = st.session_state.client.search_chats(search_query)
            
            for i, result in enumerate(results, 1):
                with st.expander(f"Result {i}"):
                    st.write(f"**Session:** {result['session_id']}")
                    st.write(f"**Messages:** {result.get('message_count', 'N/A')}")
                    
                    if st.button("💬 Load", key=f"search_{i}"):
                        st.session_state.current_session_id = result['session_id']
                        st.session_state.current_chat = result.get('chat_history', [])
                        st.rerun()

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Chat API Frontend",
        page_icon="🤖",
        layout="wide"
    )
    
    # Initialize
    init_session_state()
    
    # Title
    st.title("🤖 Chat Summarization & AI Assistant")
    st.markdown("---")
    
    # Sidebar
    display_sidebar()
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Chat", 
        "📄 Summary", 
        "❓ Q&A", 
        "📚 History"
    ])
    
    with tab1:
        display_chat_tab()
    
    with tab2:
        display_summary_tab()
    
    with tab3:
        display_qa_tab()
    
    with tab4:
        display_history_tab()
    
    # Footer
    st.markdown("---")
    st.markdown(f"**API Endpoint:** {API_BASE_URL}")
    st.markdown("**Features:** LangChain MongoDB • Memory-Enhanced Chat • AI Summarization")

if __name__ == "__main__":
    main()