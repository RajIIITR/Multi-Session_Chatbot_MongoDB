"""
Simple prompt templates for LLM operations
Focused templates for core functionality
"""

# Basic summarization prompt
SUMMARIZATION_PROMPT = """
Please provide a concise summary of the following conversation:

{chat_content}

Summary should include:
1. Main topics discussed
2. Key points or decisions
3. Overall conversation context

Keep the summary clear and under 200 words.
"""

# Context-aware response prompt
CONTEXT_RESPONSE_PROMPT = """
Based on the following conversation context, please answer the question:

Previous Conversation:
{context}

Question: {question}

Please provide a helpful answer using the conversation context when relevant.
"""

# Simple analysis prompt
ANALYSIS_PROMPT = """
Analyze the following conversation and provide insights:

{chat_content}

Please provide:
1. Brief summary
2. Main themes
3. Any notable patterns or insights

Keep the analysis concise and informative.
"""