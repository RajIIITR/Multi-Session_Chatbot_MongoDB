"""
FastAPI application with LangChain MongoDB integration
Enhanced with LangChain memory systems for better chat management
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Import LangChain MongoDB integrated modules
from src.store import ChatStore, ChatMessage
from src.helpers import ChatProcessor

# Load environment variables
load_dotenv()

# Simple request/response models
class ChatRequest(BaseModel):
    """Simple chat message request"""
    conversation_id: str = Field(..., description="Conversation identifier")
    message: str = Field(..., description="Message content")

class SessionRequest(BaseModel):
    """Request to store complete chat session"""
    session_id: str = Field(..., description="Session identifier")
    chat_messages: List[ChatRequest] = Field(..., description="List of chat messages")

class SummaryRequest(BaseModel):
    """Request for chat summarization"""
    session_id: str = Field(..., description="Session to summarize")

class QuestionRequest(BaseModel):
    """Request for context-aware question answering"""
    session_id: str = Field(..., description="Session for context")
    question: str = Field(..., description="Question to answer")

class ChatWithMemoryRequest(BaseModel):
    """Request for LangChain memory-based chat"""
    session_id: str = Field(..., description="Session identifier")
    message: str = Field(..., description="User message")

# Global instances
chat_store: Optional[ChatStore] = None
chat_processor: Optional[ChatProcessor] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown with LangChain MongoDB"""
    global chat_store, chat_processor
    
    # Startup
    try:
        chat_store = ChatStore()
        await chat_store.connect()
        chat_processor = ChatProcessor(chat_store)
        print("Application started with LangChain MongoDB integration")
        yield
    except Exception as e:
        print(f"Startup error: {e}")
        raise
    
    # Shutdown
    finally:
        if chat_store:
            await chat_store.close_connection()
        print("Application shutdown completed")

# Initialize FastAPI
app = FastAPI(
    title="Chat Summarization API with LangChain MongoDB",
    description="Enhanced API with LangChain MongoDB integration for better memory management",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Chat Summarization API with LangChain MongoDB",
        "status": "healthy",
        "features": ["LangChain Memory", "MongoDB Integration", "AI Summarization"],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/chats")
async def store_chat_session(request: SessionRequest):
    """
    Store complete chat session using LangChain MongoDB integration
    Enhanced with LangChain message formatting and storage
    """
    try:
        # Convert request to ChatMessage objects
        chat_messages = [
            ChatMessage(conversation_id=msg.conversation_id, message=msg.message)
            for msg in request.chat_messages
        ]
        
        # Store using LangChain MongoDB integration
        success = await chat_store.store_chat_session(request.session_id, chat_messages)
        
        if success:
            return {
                "session_id": request.session_id,
                "status": "stored",
                "message_count": len(chat_messages),
                "storage_type": "langchain_mongodb",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store chat session")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing chat: {str(e)}")

@app.post("/chats/message")
async def add_single_message(session_id: str, message: str, message_type: str = "human"):
    """
    Add single message to session using LangChain MongoDB
    Real-time message addition with LangChain formatting
    """
    try:
        success = await chat_store.store_chat_message(session_id, message, message_type)
        
        if success:
            return {
                "session_id": session_id,
                "message": message,
                "message_type": message_type,
                "status": "stored",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store message")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing message: {str(e)}")

@app.get("/chats/{session_id}")
async def get_chat_session(session_id: str):
    """
    Retrieve chat session using LangChain MongoDB
    Enhanced retrieval with LangChain message formatting
    """
    try:
        chat_messages = await chat_store.get_chat_session(session_id)
        
        if chat_messages is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "chat_messages": chat_messages,
            "message_count": len(chat_messages),
            "storage_type": "langchain_mongodb",
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat: {str(e)}")

@app.post("/chats/summarize")
async def summarize_chat(request: SummaryRequest):
    """
    Generate summary using LangChain memory integration
    Enhanced summarization with LangChain context management
    """
    try:
        # Generate summary using LangChain memory system
        summary = await chat_processor.generate_summary(request.session_id)
        
        # Get message count for metadata
        chat_messages = await chat_store.get_chat_session(request.session_id)
        message_count = len(chat_messages) if chat_messages else 0
        
        return {
            "session_id": request.session_id,
            "summary": summary,
            "message_count": message_count,
            "processing_type": "langchain_memory",
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@app.post("/chats/ask")
async def ask_with_context(request: QuestionRequest):
    """
    Ask questions using LangChain memory for context
    Enhanced Q&A with LangChain conversation memory
    """
    try:
        # Generate response using LangChain memory system
        answer = await chat_processor.answer_with_context(request.session_id, request.question)
        
        # Get context information
        chat_messages = await chat_store.get_chat_session(request.session_id)
        context_messages = len(chat_messages) if chat_messages else 0
        
        return {
            "session_id": request.session_id,
            "question": request.question,
            "answer": answer,
            "context_messages": context_messages,
            "processing_type": "langchain_memory",
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")

@app.post("/chats/chat")
async def chat_with_memory(request: ChatWithMemoryRequest):
    """
    Chat using LangChain conversation chain with memory
    Advanced conversational AI with automatic memory management
    """
    try:
        # Use LangChain conversation chain for more natural flow
        response = await chat_processor.chat_with_memory(request.session_id, request.message)
        
        return {
            "session_id": request.session_id,
            "user_message": request.message,
            "ai_response": response,
            "conversation_type": "langchain_chain",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in conversation: {str(e)}")

@app.get("/users/{user_id}/chats")
async def get_chat_history(user_id: str, limit: int = 5):
    """
    Get recent conversations using LangChain MongoDB
    Enhanced history retrieval with LangChain integration
    """
    try:
        conversations = await chat_store.get_last_n_conversations(limit)
        
        return {
            "user_id": user_id,
            "conversations": conversations,
            "count": len(conversations),
            "storage_type": "langchain_mongodb",
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@app.delete("/chats/{session_id}")
async def delete_chat_session(session_id: str):
    """
    Delete chat session using LangChain MongoDB
    Enhanced deletion with LangChain memory cleanup
    """
    try:
        success = await chat_store.delete_chat_session(session_id)
        
        if success:
            return {
                "session_id": session_id,
                "status": "deleted",
                "cleanup_type": "langchain_memory",
                "deleted_at": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")

@app.get("/search")
async def search_chats(query: str, limit: int = 10):
    """
    Search chat sessions using LangChain MongoDB
    Enhanced search with LangChain message indexing
    """
    try:
        results = await chat_store.search_chat_sessions(query, limit)
        
        return {
            "query": query,
            "results": results,
            "count": len(results),
            "search_type": "langchain_mongodb",
            "searched_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching chats: {str(e)}")

@app.get("/memory/{session_id}")
async def get_langchain_memory(session_id: str):
    """
    Get LangChain memory variables for a session
    Useful for debugging and understanding conversation context
    """
    try:
        # Get LangChain memory for the session
        memory = chat_processor.get_langchain_memory(session_id)
        memory_vars = memory.load_memory_variables({})
        
        # Format memory variables for display
        formatted_memory = {
            "session_id": session_id,
            "memory_variables": str(memory_vars),
            "memory_type": "ConversationBufferMemory",
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
        return formatted_memory
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving memory: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    uvicorn.run("app:app", host=host, port=port, reload=True)