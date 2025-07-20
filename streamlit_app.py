"""
Streamlit Main Application
Self-contained chat summarization app with embedded configuration
All secrets defined internally for easy Streamlit Cloud deployment
"""

import streamlit as st
import os
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# =============================================================================
# CONFIGURATION - Uses Streamlit secrets management
# =============================================================================

def get_secret(key: str, default: str = None) -> str:
    """Get secret from Streamlit secrets or show error"""
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
        else:
            if key in ["GOOGLE_API_KEY", "MONGODB_URL"]:
                st.error(f"🔑 Please add {key} to your Streamlit secrets!")
                st.info("Go to your Streamlit Cloud app settings and add the secret key.")
                st.stop()
            return default
    except Exception as e:
        st.error(f"Error accessing secret {key}: {e}")
        st.stop()

def mask_secret(secret: str) -> str:
    """Mask secret for safe printing - show only first 4-5 characters"""
    if not secret:
        return "None"
    if len(secret) <= 5:
        return "****"
    return secret[:4] + "****"

class StreamlitConfig:
    """Configuration class using Streamlit secrets"""
    
    def __init__(self):
        # MongoDB Configuration (from Streamlit secrets)
        self.MONGODB_URL = get_secret("MONGODB_URL")
        self.DATABASE_NAME = get_secret("DATABASE_NAME", "chat_summarization")
        
        # Google API Configuration (from Streamlit secrets)
        self.GOOGLE_API_KEY = get_secret("GOOGLE_API_KEY")
        
        # App Configuration
        self.DEBUG = True

# Initialize config
config = StreamlitConfig()

# Set environment variables for other modules (with masking for debug)
if config.MONGODB_URL:
    os.environ["MONGODB_URL"] = config.MONGODB_URL
if config.DATABASE_NAME:
    os.environ["DATABASE_NAME"] = config.DATABASE_NAME
if config.GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY

# =============================================================================
# EMBEDDED STORE MODULE
# =============================================================================

from datetime import datetime
from typing import List, Dict, Any, Optional, TypedDict
from bson import ObjectId
import asyncio

# Install required packages if not available
try:
    from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
    from langchain.schema import BaseMessage, HumanMessage, AIMessage
    from pymongo import MongoClient
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    st.error("Required packages not installed. Please install: langchain, langchain-mongodb, pymongo, motor")
    st.stop()

def serialize_objectid(obj):
    """Convert ObjectId to string for JSON serialization"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: serialize_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_objectid(item) for item in obj]
    return obj

class ChatMessage(TypedDict):
    conversation_id: str
    message: str

class StreamlitChatStore:
    """Streamlit-optimized chat store with SSL configuration"""
    
    def __init__(self):
        self.mongodb_url = config.MONGODB_URL
        self.database_name = config.DATABASE_NAME
        self.sync_client = None
        self.sync_database = None
        self.chat_histories: Dict[str, MongoDBChatMessageHistory] = {}
        
        # Initialize immediately
        self._init_sync_client()
    
    def _get_mongodb_client_options(self):
        """Get MongoDB client options optimized for Streamlit Cloud"""
        return {
            'tls': True,
            'tlsAllowInvalidCertificates': True,
            'tlsAllowInvalidHostnames': True,
            'connectTimeoutMS': 30000,
            'socketTimeoutMS': 30000,
            'serverSelectionTimeoutMS': 30000,
            'maxPoolSize': 1,  # Reduced for Streamlit Cloud
            'retryWrites': True,
            'w': 'majority'
        }
    
    def _init_sync_client(self):
        """Initialize sync client with multiple fallback methods"""
        if not self.mongodb_url:
            st.error("🔑 MongoDB URL not found in configuration!")
            return False
        
        # Method 1: Try with optimized SSL settings
        try:
            st.info("🔄 Attempting MongoDB connection (Method 1: Optimized SSL)...")
            client_options = self._get_mongodb_client_options()
            
            self.sync_client = MongoClient(
                self.mongodb_url,
                **client_options
            )
            self.sync_database = self.sync_client[self.database_name]
            self.sync_client.admin.command('ping')
            st.success("✅ MongoDB connected successfully!")
            print(f"✅ MongoDB sync client connected: {mask_secret(self.mongodb_url)}")
            return True
            
        except Exception as e1:
            st.warning(f"Method 1 failed: {str(e1)[:100]}...")
            
            # Method 2: Try with minimal SSL settings
            try:
                st.info("🔄 Trying Method 2: Minimal SSL settings...")
                self.sync_client = MongoClient(
                    self.mongodb_url,
                    tlsAllowInvalidCertificates=True,
                    serverSelectionTimeoutMS=10000,
                    connectTimeoutMS=10000
                )
                self.sync_database = self.sync_client[self.database_name]
                self.sync_client.admin.command('ping')
                st.success("✅ MongoDB connected with Method 2!")
                return True
                
            except Exception as e2:
                st.warning(f"Method 2 failed: {str(e2)[:100]}...")
                
                # Method 3: Try without SSL (if connection string allows)
                try:
                    st.info("🔄 Trying Method 3: Modified connection string...")
                    # Create a modified connection string for testing
                    modified_url = self.mongodb_url.replace("mongodb+srv://", "mongodb://")
                    if "?" in modified_url:
                        modified_url = modified_url.split("?")[0]
                    
                    # This won't work for Atlas, but let's try original with different params
                    self.sync_client = MongoClient(
                        self.mongodb_url,
                        tls=True,
                        tlsAllowInvalidCertificates=True,
                        directConnection=False,
                        serverSelectionTimeoutMS=5000
                    )
                    self.sync_database = self.sync_client[self.database_name]
                    self.sync_client.admin.command('ping')
                    st.success("✅ MongoDB connected with Method 3!")
                    return True
                    
                except Exception as e3:
                    st.error("❌ All MongoDB connection methods failed!")
                    st.error("This appears to be a Streamlit Cloud + MongoDB Atlas SSL compatibility issue.")
                    
                    # Show detailed error info
                    with st.expander("🔍 Detailed Error Information"):
                        st.code(f"Method 1 Error: {str(e1)}")
                        st.code(f"Method 2 Error: {str(e2)}")
                        st.code(f"Method 3 Error: {str(e3)}")
                    
                    # Provide solutions
                    st.info("💡 **Possible Solutions:**")
                    st.markdown("""
                    1. **Try a different MongoDB provider** (like MongoDB Community on Railway/Heroku)
                    2. **Use local MongoDB** for development
                    3. **Switch to a different database** (PostgreSQL, SQLite)
                    4. **Use MongoDB Realm/Atlas Functions** as a proxy
                    """)
                    
                    return False
    
    def get_chat_history(self, session_id: str) -> MongoDBChatMessageHistory:
        """Get LangChain MongoDB chat history for session with SSL configuration"""
        if session_id not in self.chat_histories:
            try:
                # Create connection string with SSL parameters for LangChain
                langchain_connection_string = self.mongodb_url
                if "?" not in langchain_connection_string:
                    langchain_connection_string += "?"
                else:
                    langchain_connection_string += "&"
                
                langchain_connection_string += "tlsAllowInvalidCertificates=true&ssl=true"
                
                self.chat_histories[session_id] = MongoDBChatMessageHistory(
                    connection_string=langchain_connection_string,
                    session_id=session_id,
                    database_name=self.database_name,
                    collection_name="chat_messages"
                )
            except Exception as e:
                st.error(f"Error creating chat history: {e}")
                # Fallback to basic connection
                self.chat_histories[session_id] = MongoDBChatMessageHistory(
                    connection_string=self.mongodb_url,
                    session_id=session_id,
                    database_name=self.database_name,
                    collection_name="chat_messages"
                )
        
        return self.chat_histories[session_id]
    
    def store_chat_message(self, session_id: str, message: str, message_type: str = "human") -> bool:
        """Store chat message with error handling"""
        try:
            chat_history = self.get_chat_history(session_id)
            
            if message_type.lower() in ["human", "user"]:
                langchain_message = HumanMessage(content=message)
            elif message_type.lower() in ["ai", "assistant"]:
                langchain_message = AIMessage(content=message)
            else:
                langchain_message = HumanMessage(content=message)
            
            chat_history.add_message(langchain_message)
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "SSL" in error_msg or "TLS" in error_msg:
                st.error("🔒 SSL Connection Issue detected")
                st.info("This is a known issue with MongoDB Atlas on Streamlit Cloud. Trying workaround...")
                
                # Try to reinitialize connection
                try:
                    if session_id in self.chat_histories:
                        del self.chat_histories[session_id]
                    
                    # Force reconnection
                    self._init_sync_client()
                    
                    # Retry once
                    chat_history = self.get_chat_history(session_id)
                    chat_history.add_message(langchain_message)
                    st.success("✅ Message stored successfully after retry!")
                    return True
                    
                except Exception as e2:
                    st.error(f"Retry failed: {str(e2)[:100]}...")
                    return False
            else:
                st.error(f"Error storing message: {str(e)[:100]}...")
                return False
    
    def get_chat_session(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get chat session messages"""
        try:
            chat_history = self.get_chat_history(session_id)
            messages = chat_history.messages
            
            if not messages:
                return None
            
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    "conversation_id": session_id,
                    "message": msg.content,
                    "message_type": "human" if isinstance(msg, HumanMessage) else "ai",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return formatted_messages
        except Exception as e:
            st.error(f"Error retrieving session: {e}")
            return None
    
    def delete_chat_session(self, session_id: str) -> bool:
        """Delete chat session"""
        try:
            chat_history = self.get_chat_history(session_id)
            chat_history.clear()
            
            if session_id in self.chat_histories:
                del self.chat_histories[session_id]
            
            return True
        except Exception as e:
            st.error(f"Error deleting session: {e}")
            return False

# =============================================================================
# EMBEDDED CHAT PROCESSOR MODULE
# =============================================================================

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import HumanMessage
    from langchain.memory import ConversationBufferMemory
except ImportError:
    st.error("Required packages not installed. Please install: langchain-google-genai")
    st.stop()

class StreamlitChatProcessor:
    """Streamlit-optimized chat processor"""
    
    def __init__(self, mongo_store: StreamlitChatStore):
        try:
            if not config.GOOGLE_API_KEY:
                st.error("🔑 Google API Key not found in Streamlit secrets!")
                st.info("Please add GOOGLE_API_KEY to your Streamlit app secrets.")
                self.llm = None
                return
                
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                google_api_key=config.GOOGLE_API_KEY,
                temperature=0.3,
                convert_system_message_to_human=True
            )
            self.mongo_store = mongo_store
            print(f"✅ LLM initialized with API key: {mask_secret(config.GOOGLE_API_KEY)}")
        except Exception as e:
            st.error(f"Error initializing LLM: {e}")
            st.info("Please check your GOOGLE_API_KEY in Streamlit secrets.")
            print(f"❌ LLM initialization error: {e}")
            self.llm = None
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4())
    
    def format_chat_for_llm(self, chat_messages: List[Dict[str, Any]]) -> str:
        """Format chat messages for LLM"""
        if not chat_messages:
            return "No messages in conversation."
        
        formatted_chat = "Conversation:\n"
        for i, msg in enumerate(chat_messages, 1):
            formatted_chat += f"{i}. {msg['message']}\n"
        
        return formatted_chat
    
    def generate_summary(self, session_id: str) -> str:
        """Generate summary synchronously for Streamlit"""
        try:
            if not self.llm:
                return "LLM not available"
                
            chat_messages = self.mongo_store.get_chat_session(session_id)
            
            if not chat_messages:
                return "No messages to summarize."
            
            formatted_chat = self.format_chat_for_llm(chat_messages)
            
            prompt = f"""
            Please provide a concise summary of the following conversation:
            
            {formatted_chat}
            
            Summary should include:
            1. Main topics discussed
            2. Key points or decisions
            3. Overall conversation context
            
            Keep the summary clear and under 200 words.
            """
            
            # Use invoke instead of ainvoke for synchronous operation
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def answer_with_context(self, session_id: str, question: str) -> str:
        """Answer questions with context"""
        try:
            if not self.llm:
                return "LLM not available"
                
            chat_messages = self.mongo_store.get_chat_session(session_id)
            context = self.format_chat_for_llm(chat_messages) if chat_messages else "No previous conversation."
            
            prompt = f"""
            Based on the following conversation context, please answer the question:
            
            Previous Conversation:
            {context}
            
            Question: {question}
            
            Please provide a helpful answer using the conversation context when relevant.
            """
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Store the Q&A in the session
            self.mongo_store.store_chat_message(session_id, question, "human")
            self.mongo_store.store_chat_message(session_id, response.content, "ai")
            
            return response.content
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def chat_with_memory(self, session_id: str, message: str) -> str:
        """Chat with memory"""
        try:
            if not self.llm:
                return "LLM not available"
                
            # Get conversation history
            chat_messages = self.mongo_store.get_chat_session(session_id)
            context = self.format_chat_for_llm(chat_messages) if chat_messages else ""
            
            # Create conversation prompt
            if context:
                prompt = f"""
                Previous conversation:
                {context}
                
                Human: {message}
                
                Please respond naturally as an AI assistant, taking into account the conversation history.
                """
            else:
                prompt = f"Human: {message}\n\nPlease respond as a helpful AI assistant."
            
            # Generate response
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Store both message and response
            self.mongo_store.store_chat_message(session_id, message, "human")
            self.mongo_store.store_chat_message(session_id, response.content, "ai")
            
            return response.content
            
        except Exception as e:
            return f"Error: {str(e)}"

# =============================================================================
# STREAMLIT APPLICATION
# =============================================================================

def init_session_state():
    """Initialize Streamlit session state"""
    if 'chat_store' not in st.session_state:
        st.session_state.chat_store = StreamlitChatStore()
    
    if 'chat_processor' not in st.session_state:
        st.session_state.chat_processor = StreamlitChatProcessor(st.session_state.chat_store)
    
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    
    if 'current_chat' not in st.session_state:
        st.session_state.current_chat = []

def display_sidebar():
    """Display sidebar with session management"""
    st.sidebar.title("🤖 Chat Management")
    
    # Current session info
    if st.session_state.current_session_id:
        st.sidebar.success(f"Session: {st.session_state.current_session_id[:8]}...")
        
        if st.sidebar.button("🗑️ Delete Session"):
            if st.session_state.chat_store.delete_chat_session(st.session_state.current_session_id):
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
        chat_data = st.session_state.chat_store.get_chat_session(load_session_id)
        if chat_data:
            st.session_state.current_session_id = load_session_id
            st.session_state.current_chat = chat_data
            st.sidebar.success("Session loaded!")
            st.rerun()
        else:
            st.sidebar.error("Session not found!")
    
    # Connection status
    st.sidebar.subheader("🌐 Status")
    if st.session_state.chat_store.sync_client:
        st.sidebar.success("✅ MongoDB Connected")
        if st.sidebar.button("🔍 Show Connection Info"):
            st.sidebar.info(f"DB: {config.DATABASE_NAME}")
            st.sidebar.info(f"URL: {mask_secret(config.MONGODB_URL)}")
    else:
        st.sidebar.error("❌ MongoDB Disconnected")
    
    if st.session_state.chat_processor.llm:
        st.sidebar.success("✅ LLM Ready")
        if st.sidebar.button("🔍 Show API Info"):
            st.sidebar.info(f"API: {mask_secret(config.GOOGLE_API_KEY)}")
    else:
        st.sidebar.error("❌ LLM Not Available")

def display_chat_tab():
    """Display chat interface"""
    st.header("💬 Chat Interface")
    
    if not st.session_state.current_session_id:
        st.warning("Please create or load a session first.")
        return
    
    # Message input
    message = st.text_area("Your message:", height=100, placeholder="Type your message...")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📤 Send", type="primary") and message:
            if st.session_state.chat_store.store_chat_message(
                st.session_state.current_session_id, message, "human"
            ):
                # Refresh chat
                st.session_state.current_chat = st.session_state.chat_store.get_chat_session(
                    st.session_state.current_session_id
                ) or []
                st.success("Message sent!")
                st.rerun()
    
    with col2:
        if st.button("🧠 Chat with AI") and message:
            with st.spinner("AI thinking..."):
                ai_response = st.session_state.chat_processor.chat_with_memory(
                    st.session_state.current_session_id, message
                )
                
                if ai_response:
                    st.success("AI Response:")
                    st.write(ai_response)
                    
                    # Refresh chat
                    st.session_state.current_chat = st.session_state.chat_store.get_chat_session(
                        st.session_state.current_session_id
                    ) or []
                    st.rerun()
    
    with col3:
        if st.button("❓ Ask Question") and message:
            with st.spinner("Getting answer..."):
                answer = st.session_state.chat_processor.answer_with_context(
                    st.session_state.current_session_id, message
                )
                
                if answer:
                    st.success("Answer:")
                    st.write(answer)
                    
                    # Refresh chat
                    st.session_state.current_chat = st.session_state.chat_store.get_chat_session(
                        st.session_state.current_session_id
                    ) or []
                    st.rerun()
    
    # Display conversation
    if st.session_state.current_chat:
        st.subheader("💬 Conversation History")
        
        for msg in st.session_state.current_chat:
            if msg.get("message_type") == "human":
                st.markdown(f"👤 **You:** {msg['message']}")
            else:
                st.markdown(f"🤖 **AI:** {msg['message']}")
            st.markdown("---")
    else:
        st.info("No messages yet. Start a conversation!")

def display_summary_tab():
    """Display summarization interface"""
    st.header("📄 Chat Summarization")
    
    if not st.session_state.current_session_id:
        st.warning("Please create or load a session first.")
        return
    
    if st.button("📊 Generate Summary", type="primary"):
        with st.spinner("Generating summary..."):
            summary = st.session_state.chat_processor.generate_summary(
                st.session_state.current_session_id
            )
            
            if summary:
                st.subheader("📋 Summary")
                st.write(summary)
    
    # Summarize any session
    st.subheader("📊 Summarize Any Session")
    session_to_summarize = st.text_input("Enter Session ID:")
    
    if st.button("📊 Summarize Session") and session_to_summarize:
        with st.spinner("Generating summary..."):
            summary = st.session_state.chat_processor.generate_summary(session_to_summarize)
            
            if summary:
                st.subheader(f"📋 Summary for {session_to_summarize[:8]}...")
                st.write(summary)

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Chat Summarization & AI Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize
    init_session_state()
    
    # Header
    st.title("🤖 Chat Summarization & AI Assistant")
    st.markdown("**Self-contained Streamlit app with LangChain MongoDB integration**")
    st.markdown("---")
    
    # Sidebar
    display_sidebar()
    
    # Main tabs
    tab1, tab2 = st.tabs(["💬 Chat", "📄 Summary"])
    
    with tab1:
        display_chat_tab()
    
    with tab2:
        display_summary_tab()
    
    # Footer
    st.markdown("---")
    st.markdown("**Features:** LangChain MongoDB • Memory-Enhanced Chat • AI Summarization")

if __name__ == "__main__":
    main()