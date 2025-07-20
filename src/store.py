"""
LangChain MongoDB integration for chat data storage
Uses langchain-mongodb for better integration with LangChain ecosystem
Fixed ObjectId serialization issues
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional, TypedDict
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    """
    Simple chat message structure - only conversation_id and message needed
    LangChain MongoDB will handle the rest of the message structure
    """
    conversation_id: str
    message: str

class ChatStore:
    """
    LangChain MongoDB integration for chat storage
    Uses langchain-mongodb for seamless integration with LangChain ecosystem
    Provides both sync and async operations for different use cases
    """
    
    def __init__(self):
        # MongoDB connection setup
        self.mongodb_url = os.getenv("MONGODB_URL")
        self.database_name = os.getenv("DATABASE_NAME", "chat_summarization")
        
        # Sync client for LangChain operations
        self.sync_client = MongoClient(self.mongodb_url)
        self.sync_database = self.sync_client[self.database_name]
        
        # Async client for FastAPI operations
        self.async_client: Optional[AsyncIOMotorClient] = None
        self.async_database = None
        
        # LangChain MongoDB chat message history
        self.chat_histories: Dict[str, MongoDBChatMessageHistory] = {}
    
    async def connect(self):
        """
        Initialize both sync and async connections
        LangChain MongoDB requires sync client, FastAPI needs async
        """
        try:
            # Setup async client for general operations
            self.async_client = AsyncIOMotorClient(self.mongodb_url)
            self.async_database = self.async_client[self.database_name]
            
            # Test connections
            await self.async_client.admin.command('ping')
            self.sync_client.admin.command('ping')
            
            print("Successfully connected to MongoDB with LangChain integration")
            
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            raise
    
    def get_chat_history(self, session_id: str) -> MongoDBChatMessageHistory:
        """
        Get LangChain MongoDB chat message history for a session
        This provides seamless integration with LangChain memory systems
        
        Args:
            session_id: Session identifier
            
        Returns:
            MongoDBChatMessageHistory instance for the session
        """
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = MongoDBChatMessageHistory(
                connection_string=self.mongodb_url,
                session_id=session_id,
                database_name=self.database_name,
                collection_name="chat_messages"
            )
        
        return self.chat_histories[session_id]
    
    async def store_chat_message(self, session_id: str, message: str, message_type: str = "human") -> bool:
        """
        Store chat message using LangChain MongoDB integration
        Automatically handles message formatting and storage
        
        Args:
            session_id: Session identifier
            message: Message content
            message_type: Type of message (human, ai, system)
            
        Returns:
            bool: Success status
        """
        try:
            # Get LangChain chat history for session
            chat_history = self.get_chat_history(session_id)
            
            # Create appropriate LangChain message type
            if message_type.lower() in ["human", "user"]:
                langchain_message = HumanMessage(content=message)
            elif message_type.lower() in ["ai", "assistant"]:
                langchain_message = AIMessage(content=message)
            else:
                # Default to HumanMessage for system or other types
                langchain_message = HumanMessage(content=message)
            
            # Add message to LangChain history (automatically stores in MongoDB)
            chat_history.add_message(langchain_message)
            
            return True
            
        except Exception as e:
            print(f"Error storing message with LangChain: {e}")
            return False
    
    async def get_chat_session(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve chat session using LangChain MongoDB
        Returns messages in a format compatible with our API
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages or None if not found
        """
        try:
            # Get LangChain chat history
            chat_history = self.get_chat_history(session_id)
            
            # Get all messages from LangChain history
            messages = chat_history.messages
            
            if not messages:
                return None
            
            # Convert LangChain messages to our format
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    "conversation_id": session_id,  # Use session_id as conversation_id
                    "message": msg.content,
                    "message_type": "human" if isinstance(msg, HumanMessage) else "ai",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return formatted_messages
            
        except Exception as e:
            print(f"Error retrieving session with LangChain: {e}")
            return None
    
    async def store_chat_session(self, session_id: str, chat_messages: List[ChatMessage]) -> bool:
        """
        Store multiple chat messages using LangChain MongoDB
        Processes each message through LangChain for consistent storage
        
        Args:
            session_id: Session identifier
            chat_messages: List of chat messages
            
        Returns:
            bool: Success status
        """
        try:
            # Clear existing session to avoid duplicates
            chat_history = self.get_chat_history(session_id)
            chat_history.clear()
            
            # Add each message through LangChain
            for msg in chat_messages:
                success = await self.store_chat_message(
                    session_id=session_id,
                    message=msg["message"],
                    message_type="human"  # Default to human for simplicity
                )
                if not success:
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error storing chat session with LangChain: {e}")
            return False
    
    async def get_last_n_conversations(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent conversations using async MongoDB operations
        Fixed ObjectId serialization issues
        """
        try:
            # Use async client for this operation
            collection = self.async_database["chat_messages"]
            
            # Aggregate to get unique sessions and their message counts
            pipeline = [
                {"$group": {
                    "_id": "$SessionId",
                    "message_count": {"$sum": 1},
                    "last_message": {"$last": "$History"},
                    "timestamp": {"$max": "$_id"}
                }},
                {"$sort": {"timestamp": -1}},
                {"$limit": n}
            ]
            
            cursor = collection.aggregate(pipeline)
            conversations = await cursor.to_list(length=n)
            
            # Format for consistent API response with ObjectId serialization
            formatted_conversations = []
            for conv in conversations:
                # Serialize ObjectId fields
                conv_serialized = serialize_objectid(conv)
                session_id = conv_serialized["_id"]
                
                # Get sample messages for preview
                session_messages = await self.get_chat_session(session_id)
                first_msg = session_messages[0]["message"][:50] + "..." if session_messages else "Empty"
                last_msg = session_messages[-1]["message"][:50] + "..." if session_messages else "Empty"
                
                formatted_conversations.append({
                    "session_id": session_id,
                    "timestamp": conv_serialized["timestamp"],
                    "message_count": conv_serialized["message_count"],
                    "first_message": first_msg,
                    "last_message": last_msg,
                    "full_chat": session_messages or []
                })
            
            return formatted_conversations
            
        except Exception as e:
            print(f"Error retrieving conversations: {e}")
            return []
    
    async def search_chat_sessions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search across chat sessions using MongoDB text search
        Fixed ObjectId serialization issues
        """
        try:
            # Use async client for search
            collection = self.async_database["chat_messages"]
            
            # Create text index if it doesn't exist
            try:
                await collection.create_index([("History.content", "text")])
            except:
                pass  # Index might already exist
            
            # Search using text index
            cursor = collection.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            results = await cursor.to_list(length=limit)
            
            # Format results with ObjectId serialization
            formatted_results = []
            for result in results:
                # Serialize ObjectId fields
                result_serialized = serialize_objectid(result)
                session_id = result_serialized.get("SessionId", "unknown")
                session_messages = await self.get_chat_session(session_id)
                
                formatted_results.append({
                    "session_id": session_id,
                    "chat_history": session_messages or [],
                    "message_count": len(session_messages) if session_messages else 0,
                    "search_score": result_serialized.get("score", 0)
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching with LangChain MongoDB: {e}")
            return []
    
    async def delete_chat_session(self, session_id: str) -> bool:
        """
        Delete chat session using LangChain MongoDB
        Clears the session through LangChain for proper cleanup
        
        Args:
            session_id: Session to delete
            
        Returns:
            bool: Success status
        """
        try:
            # Use LangChain to clear the session
            chat_history = self.get_chat_history(session_id)
            chat_history.clear()
            
            # Remove from our cache
            if session_id in self.chat_histories:
                del self.chat_histories[session_id]
            
            return True
            
        except Exception as e:
            print(f"Error deleting session with LangChain: {e}")
            return False
    
    def get_langchain_memory(self, session_id: str):
        """
        Get LangChain conversation buffer memory for a session
        This enables direct integration with LangChain chains and agents
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationBufferMemory with MongoDB backend
        """
        from langchain.memory import ConversationBufferMemory
        
        chat_history = self.get_chat_history(session_id)
        
        return ConversationBufferMemory(
            chat_memory=chat_history,
            return_messages=True,
            memory_key="chat_history"
        )
    
    async def close_connection(self):
        """Close all MongoDB connections"""
        if self.async_client:
            self.async_client.close()
        
        if self.sync_client:
            self.sync_client.close()
        
        print("LangChain MongoDB connections closed")