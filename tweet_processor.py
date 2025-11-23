"""
Tweet processing module for generating responses to user tweets.
This module processes tweet text and generates appropriate responses.
"""

from typing import Optional


def generate_response(tweet_text: str) -> str:
    """
    Takes in tweet text and outputs the message that is supposed to be returned to the user.
    
    Args:
        tweet_text (str): The text content of the tweet (with @mentions removed)
    
    Returns:
        str: The response message to be sent back to the user
    
    Example:
        >>> response = generate_response("What happened in 2019?")
        >>> print(response)
        "Based on the documents..."
    """
    # Clean and normalize the input text
    query = tweet_text.strip()
    
    # Handle empty queries
    if not query:
        return "I didn't receive any question. Please ask me something about the documents!"
    
    # Extract text and remove bot mention
    words = query.split()
    filtered_words = [word for word in words if not word.startswith('@')]
    echo_text = ' '.join(filtered_words).strip()
    
    # Create reply
    if echo_text:
        return echo_text
    else:
        return f"You didn't say anything for me to echo!"

    # TODO: Integrate with RAG system when implemented
    # For now, return a placeholder response
    # This will be replaced with actual RAG query processing
    
    # Placeholder implementation
    # In the future, this will:
    # 1. Process the query through the RAG pipeline
    # 2. Search documents using BM25 + semantic search
    # 3. Generate a response based on retrieved context
    # 4. Format the response for Twitter (280 char limit)
    
    response = f"Processing your query: '{query}'. RAG system integration coming soon!"
    
    # Ensure response fits Twitter's character limit (280 characters)
    # Leave room for @username mention (typically ~15 chars)
    max_length = 265
    if len(response) > max_length:
        response = response[:max_length-3] + "..."
    
    return response

