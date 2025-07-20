"""
Enhanced chat processing with LangChain MongoDB integration
Uses LangChain memory systems for better chat management
"""

import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
from .store import ChatMessage, ChatStore

# Load environment variables
load_dotenv()

class ChatProcessor:
    """
    Enhanced chat processor with LangChain MongoDB integration
    Leverages LangChain memory systems for context-aware processing
    """
    
    def __init__(self, mongo_store: ChatStore):
        # Initialize Google Generative AI model
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.3,
            convert_system_message_to_human=True
        )
        
        # Reference to LangChain MongoDB store
        self.mongo_store = mongo_store
    
    def generate_session_id(self) -> str:
        """
        Generate unique session ID
        Simple UUID generation for session management
        """
        return str(uuid.uuid4())
    
    def create_chat_message(self, conversation_id: str, message: str) -> ChatMessage:
        """
        Create simple chat message with only required fields
        Follows the simplified ChatMessage structure
        
        Args:
            conversation_id: Conversation identifier
            message: Message content
            
        Returns:
            ChatMessage with conversation_id and message
        """
        return ChatMessage(
            conversation_id=conversation_id,
            message=message
        )
    
    def get_langchain_memory(self, session_id: str) -> ConversationBufferMemory:
        """
        Get LangChain memory for session with MongoDB backend
        This enables seamless integration with LangChain chains and agents
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationBufferMemory with MongoDB persistence
        """
        return self.mongo_store.get_langchain_memory(session_id)
    
    def format_chat_for_llm(self, chat_messages: List[Dict[str, Any]]) -> str:
        """
        Format chat messages for LLM processing
        Simple formatting that preserves conversation flow
        
        Args:
            chat_messages: List of chat messages
            
        Returns:
            Formatted string for LLM input
        """
        if not chat_messages:
            return "No messages in conversation."
        
        formatted_chat = "Conversation:\n"
        for i, msg in enumerate(chat_messages, 1):
            formatted_chat += f"{i}. {msg['message']}\n"
        
        return formatted_chat
    
    async def generate_summary(self, session_id: str) -> str:
        """
        Generate summary using LangChain memory system
        Leverages LangChain's memory management for context retrieval
        
        Args:
            session_id: Session to summarize
            
        Returns:
            Generated summary text
        """
        try:
            # Get chat messages using LangChain MongoDB integration
            chat_messages = await self.mongo_store.get_chat_session(session_id)
            
            if not chat_messages:
                return "No messages to summarize."
            
            # Format chat for LLM
            formatted_chat = self.format_chat_for_llm(chat_messages)
            
            # Create summarization prompt
            prompt = f"""
            Please provide a concise summary of the following conversation:
            
            {formatted_chat}
            
            Summary should include:
            1. Main topics discussed
            2. Key points or decisions
            3. Overall conversation context
            
            Keep the summary clear and under 200 words.
            """
            
            # Generate summary using LLM
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            
            return response.content
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"
    
    async def answer_with_context(self, session_id: str, question: str) -> str:
        """
        Answer questions using LangChain memory for context
        Utilizes LangChain's conversation memory for context-aware responses
        
        Args:
            session_id: Session for context
            question: User's question
            
        Returns:
            LLM response with context awareness
        """
        try:
            # Get LangChain memory for the session
            memory = self.get_langchain_memory(session_id)
            
            # Load conversation history from memory
            history = memory.load_memory_variables({})
            chat_history = history.get("chat_history", [])
            
            # Format conversation history
            context_messages = []
            for msg in chat_history:
                context_messages.append({
                    "message": msg.content,
                    "type": type(msg).__name__
                })
            
            context = self.format_chat_for_llm(context_messages)
            
            # Create prompt with context
            prompt = f"""
            Based on the following conversation context, please answer the question:
            
            Previous Conversation:
            {context}
            
            Question: {question}
            
            Please provide a helpful answer using the conversation context when relevant.
            """
            
            # Generate response with context
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            
            # Store the question and answer in LangChain memory
            await self.mongo_store.store_chat_message(session_id, question, "human")
            await self.mongo_store.store_chat_message(session_id, response.content, "ai")
            
            return response.content
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return f"Error: {str(e)}"
    
    async def create_langchain_conversation_chain(self, session_id: str):
        """
        Create a LangChain conversation chain with MongoDB memory
        This enables more advanced conversational AI patterns
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationChain with MongoDB-backed memory
        """
        try:
            from langchain.chains import ConversationChain
            
            # Get memory with MongoDB backend
            memory = self.get_langchain_memory(session_id)
            
            # Create conversation chain
            conversation = ConversationChain(
                llm=self.llm,
                memory=memory,
                verbose=True
            )
            
            return conversation
            
        except Exception as e:
            print(f"Error creating conversation chain: {e}")
            return None
    
    async def chat_with_memory(self, session_id: str, message: str) -> str:
        """
        Chat using LangChain conversation chain with memory
        Provides more natural conversation flow with automatic memory management
        
        Args:
            session_id: Session identifier
            message: User message
            
        Returns:
            AI response with full conversation context
        """
        try:
            # Create or get conversation chain
            conversation = await self.create_langchain_conversation_chain(session_id)
            
            if not conversation:
                return "Error: Could not create conversation chain"
            
            # Generate response using LangChain chain
            response = await conversation.apredict(input=message)
            
            return response
            
        except Exception as e:
            print(f"Error in chat with memory: {e}")
            return f"Error: {str(e)}"
    
    def extract_keywords(self, chat_messages: List[Dict[str, Any]]) -> List[str]:
        """
        Simple keyword extraction from chat messages
        Basic filtering for conversation topics (non-LLM approach for speed)
        
        Args:
            chat_messages: List of chat messages
            
        Returns:
            List of potential keywords
        """
        try:
            # Combine all messages
            all_text = " ".join([msg['message'] for msg in chat_messages])
            
            # Simple keyword extraction (can be enhanced with NLP libraries)
            words = all_text.lower().split()
            
            # Filter out common words and short words
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
            
            keywords = []
            for word in words:
                if len(word) > 3 and word not in common_words and word.isalpha():
                    keywords.append(word)
            
            # Return unique keywords (top 10)
            unique_keywords = list(set(keywords))
            return unique_keywords[:10]
            
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []