# twitter_bot.py
# Install required packages first: pip install tweepy python-dotenv

import tweepy
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load credentials from environment variables (safer than hardcoding)
API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET = os.getenv('TWITTER_API_SECRET')
ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# Authenticate with Twitter API v2
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

# Store last processed mention ID
last_mention_id = None

def check_mentions():
    """Check for new mentions and reply with echoed text"""
    global last_mention_id
    
    try:
        # Get authenticated user's ID
        me = client.get_me()
        my_id = me.data.id
        my_username = me.data.username
        
        print(f"Bot running as @{my_username} (ID: {my_id})")
        
        # Get mentions
        mentions = client.get_users_mentions(
            id=my_id,
            since_id=last_mention_id,
            tweet_fields=['author_id', 'created_at'],
            expansions=['author_id'],
            max_results=10
        )
        
        if mentions.data:
            for tweet in mentions.data:
                # Update last mention ID
                last_mention_id = tweet.id
                
                # Get the author's username
                author = next((user for user in mentions.includes['users'] 
                             if user.id == tweet.author_id), None)
                author_username = author.username if author else "unknown"
                
                # Extract text and remove bot mention
                tweet_text = tweet.text
                # Remove @mentions from the text
                words = tweet_text.split()
                filtered_words = [word for word in words if not word.startswith('@')]
                echo_text = ' '.join(filtered_words).strip()
                
                # Create reply
                if echo_text:
                    reply_text = f"@{author_username} {echo_text}"
                else:
                    reply_text = f"@{author_username} You didn't say anything for me to echo!"
                
                # Post reply
                client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=tweet.id
                )
                
                print(f"[{datetime.now()}] Replied to @{author_username}: {echo_text}")
                
        else:
            print(f"[{datetime.now()}] No new mentions")
            
    except tweepy.TooManyRequests as e:
        print(f"Rate limit reached. Waiting 15 minutes...")
        time.sleep(15 * 60)
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Main loop to continuously check for mentions"""
    print("Twitter Echo Bot starting...")
    print("Press Ctrl+C to stop")
    
    # Print credentials to verify they're loaded (for debugging)
    print("\nChecking environment variables:")
    print(f"TWITTER_API_KEY: {API_KEY}")
    print(f"TWITTER_API_SECRET: {API_SECRET}")
    print(f"TWITTER_ACCESS_TOKEN: {ACCESS_TOKEN}")
    print(f"TWITTER_ACCESS_TOKEN_SECRET: {ACCESS_TOKEN_SECRET}")
    print(f"TWITTER_BEARER_TOKEN: {BEARER_TOKEN}")
    print()
    
    # Check credentials are loaded
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, BEARER_TOKEN]):
        print("ERROR: Missing credentials. Make sure environment variables are set.")
        return
    
    while True:
        try:
            check_mentions()
            # Wait 60 seconds between checks (respects rate limits)
            time.sleep(60)
        except KeyboardInterrupt:
            print("\nBot stopped by user")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()