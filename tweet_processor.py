"""
Tweet processing module for generating responses to user tweets.
This module processes tweet text and generates appropriate responses.
"""

from typing import Optional


def generate_response(tweet_text: str, author_username: str) -> str:
    """
    Takes in tweet text and outputs the complete reply message for the user.
    
    Args:
        tweet_text (str): The text content of the tweet (raw text)
        author_username (str): The username of the person who mentioned the bot
    
    Returns:
        str: The complete reply message to be sent back (includes @mention)
    
    Example:
        >>> response = generate_response("@bot What happened in 2019?", "john_doe")
        >>> print(response)
        "@john_doe What happened in 2019?"
    """
    # Clean and normalize the input text
    query = tweet_text.strip()
    
    # Extract text and remove all @mentions
    words = query.split()
    filtered_words = [word for word in words if not word.startswith('@')]
    clean_text = ' '.join(filtered_words).strip()
    
    # Handle empty queries (only @mentions, no actual content)
    if not clean_text:
        return f"@{author_username} You didn't say anything for me to echo!"
    
    # Create reply with @mention
    reply_text = f"@{author_username} {clean_text}"
    
    return reply_text

    # TODO: Integrate with RAG system when implemented
    # This will be replaced with actual RAG query processing
    # Future implementation will:
    # 1. Process the query through the RAG pipeline
    # 2. Search documents using BM25 + semantic search
    # 3. Generate a response based on retrieved context
    # 4. Format the response for Twitter (280 char limit)

