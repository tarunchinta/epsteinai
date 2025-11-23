"""
Test script for Twitter bot functionality
Run this to test the bot without manually tweeting
"""

import tweepy
import os
from datetime import datetime
from dotenv import load_dotenv
from tweet_processor import generate_response

# Load environment variables
load_dotenv()

# Twitter credentials
API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET = os.getenv('TWITTER_API_SECRET')
ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')


def test_generate_response():
    """Test the generate_response function with various inputs"""
    print("=" * 60)
    print("Testing generate_response() function")
    print("=" * 60)
    
    test_cases = [
        ("What happened in 2019?", "Query with content", "testuser"),
        ("Tell me about Maxwell", "Another query", "testuser"),
        ("", "Empty query", "testuser"),
        ("@botname @someone tell me about Epstein", "Query with mentions", "testuser"),
        ("This is a very long query " * 20, "Very long query", "testuser"),
    ]
    
    for tweet_text, description, username in test_cases:
        print(f"\n📝 Test: {description}")
        print(f"Input: '{tweet_text[:50]}...' ({len(tweet_text)} chars)" if len(tweet_text) > 50 else f"Input: '{tweet_text}'")
        print(f"Username: @{username}")
        
        response = generate_response(tweet_text, username)
        print(f"Output: '{response}'")
        print(f"Length: {len(response)} characters")
        
        # Check if response fits in a tweet
        max_allowed = 280
        if len(response) > max_allowed:
            print(f"⚠️ WARNING: Response too long! ({len(response)} > {max_allowed})")
        else:
            print(f"✅ Response fits in tweet")
    
    print("\n" + "=" * 60)


def test_fetch_recent_mentions():
    """Fetch and display recent mentions to the bot (read-only test)"""
    print("\n" + "=" * 60)
    print("Fetching Recent Mentions (Read-Only)")
    print("=" * 60)
    
    try:
        # Authenticate
        client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        
        # Get bot's info
        me = client.get_me()
        my_id = me.data.id
        my_username = me.data.username
        
        print(f"\n🤖 Bot Account: @{my_username} (ID: {my_id})")
        
        # Get recent mentions
        mentions = client.get_users_mentions(
            id=my_id,
            tweet_fields=['author_id', 'created_at', 'text'],
            expansions=['author_id'],
            max_results=5  # Get last 5 mentions
        )
        
        if mentions.data:
            print(f"\n📬 Found {len(mentions.data)} recent mention(s):\n")
            
            for i, tweet in enumerate(mentions.data, 1):
                # Get author info
                author = next((user for user in mentions.includes['users'] 
                             if user.id == tweet.author_id), None)
                author_username = author.username if author else "unknown"
                
                # Generate response (function handles cleaning and @mention)
                response = generate_response(tweet.text, author_username)
                
                print(f"Mention #{i}:")
                print(f"  From: @{author_username}")
                print(f"  Time: {tweet.created_at}")
                print(f"  Original: {tweet.text}")
                print(f"  Bot Reply: {response}")
                print()
        else:
            print("\n📭 No mentions found")
            print("You can create a test mention by:")
            print(f"  1. Tweeting: @{my_username} test message")
            print(f"  2. Or use option 3 below to post programmatically")
    
    except tweepy.Unauthorized:
        print("\n❌ Authentication failed. Check your API credentials.")
    except tweepy.TooManyRequests:
        print("\n⚠️ Rate limit exceeded. Wait 15 minutes and try again.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("=" * 60)


def post_test_tweet():
    """Post a test tweet that mentions the bot (requires user confirmation)"""
    print("\n" + "=" * 60)
    print("Post Test Tweet")
    print("=" * 60)
    
    try:
        # Authenticate
        client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        
        # Get bot's username
        me = client.get_me()
        my_username = me.data.username
        
        print(f"\n🤖 Bot Account: @{my_username}")
        print("\n⚠️ This will post a PUBLIC tweet from your account.")
        print(f"Tweet content: '@{my_username} Test query about documents'")
        
        confirm = input("\nDo you want to proceed? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            # Post the test tweet
            test_message = f"@{my_username} Test query about documents"
            response = client.create_tweet(text=test_message)
            
            print(f"\n✅ Test tweet posted successfully!")
            print(f"Tweet ID: {response.data['id']}")
            print(f"\nWait 60 seconds for the bot to process it,")
            print(f"or run the bot manually to see the response.")
        else:
            print("\n❌ Test tweet cancelled.")
    
    except tweepy.Forbidden as e:
        print(f"\n❌ Permission denied. Make sure you have write permissions: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("=" * 60)


def simulate_bot_processing():
    """Simulate the bot's processing of a mention without actually posting"""
    print("\n" + "=" * 60)
    print("Simulate Bot Processing (Dry Run)")
    print("=" * 60)
    
    print("\nThis simulates how the bot would process a mention:")
    
    # Simulate various tweet scenarios
    test_mentions = [
        {
            'username': 'testuser1',
            'tweet': '@epsteinbot What documents mention Maxwell in 2019?',
        },
        {
            'username': 'testuser2',
            'tweet': '@epsteinbot @someoneelse Tell me about flights',
        },
        {
            'username': 'testuser3',
            'tweet': '@epsteinbot',
        },
    ]
    
    for i, mention in enumerate(test_mentions, 1):
        print(f"\n--- Scenario {i} ---")
        print(f"From: @{mention['username']}")
        print(f"Tweet: {mention['tweet']}")
        
        # Generate response (function handles cleaning and @mention)
        response = generate_response(mention['tweet'], mention['username'])
        
        print(f"Bot Reply: '{response}'")
        print(f"Reply Length: {len(response)} chars")
    
    print("\n" + "=" * 60)


def main():
    """Main test menu"""
    print("\n" + "=" * 60)
    print("Twitter Bot Test Suite")
    print("=" * 60)
    
    # Check credentials
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, BEARER_TOKEN]):
        print("\n❌ ERROR: Missing Twitter API credentials!")
        print("Make sure your .env file has all required variables.")
        return
    
    while True:
        print("\nSelect a test option:")
        print("1. Test generate_response() function (unit test)")
        print("2. Fetch recent mentions (read-only)")
        print("3. Post a test tweet that mentions the bot")
        print("4. Simulate bot processing (dry run, no API calls)")
        print("5. Run all non-posting tests (1, 2, 4)")
        print("0. Exit")
        
        choice = input("\nEnter option (0-5): ").strip()
        
        if choice == '1':
            test_generate_response()
        elif choice == '2':
            test_fetch_recent_mentions()
        elif choice == '3':
            post_test_tweet()
        elif choice == '4':
            simulate_bot_processing()
        elif choice == '5':
            test_generate_response()
            test_fetch_recent_mentions()
            simulate_bot_processing()
        elif choice == '0':
            print("\n👋 Exiting test suite")
            break
        else:
            print("\n❌ Invalid option. Please try again.")


if __name__ == "__main__":
    main()

