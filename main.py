import discord
import json
import os
from datetime import datetime
from dotenv import load_dotenv  # cSpell:ignore dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# File paths for storing user levels and last checked data
LEVELS_FILE = 'lvls.json'
LAST_RUNTIME = 'last_runtime.json'
CHAT_CHANNEL_ID = 1365352681211957413  # Replace with your actual channel ID

# Helper functions to load and save JSON files
def load_json(path, default):
    """
    Load data from a JSON file. If the file doesn't exist, return the default value.
    """
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default

def save_json(path, data):
    """
    Save data to a JSON file.
    """
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

# Set up intents to allow the bot to access message content
intents = discord.Intents.default()
intents.message_content = True

class Client(discord.Client):
    def __init__(self, *args, **kwargs):
        """
        Initialize the bot client.
        """
        super().__init__(*args, **kwargs)
        # Load user levels and the timestamp of the last checked message
        self.user_levels = load_json(LEVELS_FILE, {})
        self.last_rune_data = load_json(LAST_RUNTIME, {})
        self.last_checked_time = self.last_rune_data.get("last_checked_time")  # Last check time

    async def on_ready(self):
        """
        This function runs when the bot is successfully logged in and ready to work.
        """
        print(f'Logged in as {self.user}!')

        # Check the messages and process them
        await self.check_messages()

        # Close the bot after processing messages
        await self.close()

    async def check_messages(self):
        """
        This function checks all messages sent in the channel after the last run time.
        It processes only those that are numbers within the allowed range.
        """
        channel = self.get_channel(CHAT_CHANNEL_ID)  # Replace with the actual channel ID
        if channel is None:
            print("Error: Could not find the channel.")
            return

        # If there's no last checked time, we check all messages
        after_time = datetime.fromisoformat(self.last_checked_time) if self.last_checked_time else None
        all_messages = []
        done = False
        last_message_time = None  # To keep track of the last message's timestamp

        # Loop to get all messages after the last checked time
        while not done:
            batch = []  # Temporary storage for messages in each batch
            # Fetch the next batch of messages (100 at a time)
            async for message in channel.history(limit=100, after=after_time):
                batch.append(message)

            if not batch:
                break  # Break if no messages are found

            # Sort the batch by the message's creation date, oldest first
            batch.sort(key=lambda msg: msg.created_at)  # Sort messages by creation date in ascending order

            for message in batch:
                if after_time and message.created_at <= after_time:
                    continue  # Skip messages already processed

                all_messages.append(message)
                last_message_time = message.created_at  # Update the last message's time

            # If we have less than 100 messages, we've reached the end
            if len(batch) < 100:
                done = True
            else:
                # If there are still more messages, continue after the last processed message
                after_time = last_message_time

        print(f"Found {len(all_messages)} new messages.")

        # Process each message to check if it's a valid number
        for message in all_messages:
            if message.author.bot:
                continue  # Skip bot messages

            try:
                number = int(message.content.strip())  # Try to convert the message to an integer
            except ValueError:
                continue  # Skip if the message is not a number

            user_id = str(message.author.id)  # Get the user ID as a string
            current_date = datetime.now().strftime('%Y-%m-%d')  # Get today's date as a string
            user_history = self.user_levels.get(user_id, {})  # Get the user's level history (default to empty dict)

            last_level = user_history.get(current_date, 0)  # Get the user's last level for today (default to 0)

            # If the number is within 3 levels higher than the user's last level, update the level
            if number > last_level and number <= last_level + 3:
                user_history[current_date] = number  # Update the user's level for the current day
                self.user_levels[user_id] = user_history  # Save the updated history for the user
                print(f"{message.author} now has level {number} for {current_date}")

        # If there are any new messages, update the last checked time and save the data
        if all_messages:
            self.last_checked_time = last_message_time.isoformat()  # Save the last checked time as ISO format
            save_json(LEVELS_FILE, self.user_levels)  # Save updated user levels
            save_json(LAST_RUNTIME, {"last_checked_time": self.last_checked_time})  # Save the last checked time
            print("Data saved.")

client = Client(intents=intents)
client.run(token)