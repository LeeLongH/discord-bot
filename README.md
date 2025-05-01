Viet
Gab
Kucia
Miri
?
?
Seon
Dota Farm












import discord
import os
import json
import re
import io
import pytz
from datetime import datetime, timedelta
datetime = datetime

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

from collections import Counter
from dotenv import load_dotenv

import main_utils as utils
import utils_check_msgs as ucm

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# File paths for storing user levels and last checked data
LVLS_FILE = 'lvls.json'
LAST_RUNTIME_FILE = 'last_runtime.json'
READ_CHAT_CHANNEL_ID = 1361015769248567470
TESTING_CHAT_CHANNEL_ID = 1365761858447081482
LOCAL_TIMEZONE = pytz.timezone('Europe/Ljubljana')
#READ_CHAT_CHANNEL_ID = TESTING_CHAT_CHANNEL_ID
#TESTING_CHAT_CHANNEL_ID = READ_CHAT_CHANNEL_ID
READ_CHAT_CHANNEL_ID = MY_SERVER = 1365352681211957413

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

# Set up intents allows bot to access message content
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # needed to access member join dates

class Client(discord.Client):
    def __init__(self, *args, **kwargs):
        """
        Initialize the bot client.
        """
        super().__init__(*args, **kwargs)

        # JSONs
        self.users_lvls = load_json(LVLS_FILE, {})
        self.last_ran_data = load_json(LAST_RUNTIME_FILE, {})
        self.last_checked_time = self.last_ran_data.get("last_checked_time")

        self.user_graph_request_message_id = 0
        self.join_graph_request_message_id = 0

    async def on_ready(self):
        """
        This function runs when the bot is successfully logged in and ready to work.
        """
        print(f'Logged in as {self.user}!')

        await self.check_messages()

        await self.close()


    async def check_messages(self):
        """
        This function checks all messages sent in the channel after the last run time.
        It processes only those that are numbers within the allowed range.
        """

        read_channel = ucm.get_read_channel(self.get_channel(READ_CHAT_CHANNEL_ID))
        (all_messages, last_message_time) = ucm.get_all_msgs(self.last_checked_time, read_channel)
        
        # Process each message to check if it's a valid number
        for message in all_messages:
            if message.author.bot:
                continue  # Skip bot messages

            if message.content == "graph":
                print(f"message: {message}")
                self.user_graph_request_message_id = message.id  # Store the message ID for later

            if message.content == "join":
                print(f"message: {message}")
                self.join_graph_request_message_id = message.id  # Store the message ID for later

            number = utils.split_msg(message) 

            if number == 0:  # No number (or too many numbers) found
                print(f"No numbers.")
                continue

            user_id = str(message.author.id)  # Get the user ID as a string

            local_time = message.created_at.astimezone(LOCAL_TIMEZONE)
            day_date = local_time.strftime('%Y-%m-%d')
            
            user_history = self.users_lvls.get(user_id, {})  # Get the user's level history (default to empty dict)

            # Get the user's last level for today (default to 0)
            if user_history:
                last_saved_date = max(user_history.keys())
                levels_array = user_history.get(last_saved_date, [])
                last_level = levels_array[-1] if levels_array else 0
            else:
                last_level = number - 1
                print("No prior lvl entry for this user")

            print(f"-> old user lvl: {last_level}\n-> new user lvl?: {number}")

            # If the number is within 3 levels higher than the user's last level, update the level
            if number > last_level and number <= last_level + 3:
                print("YES YES YES")
                if day_date not in user_history:
                    user_history[day_date] = []
                user_history[day_date].append(number)  # Add number to list
                self.users_lvls[user_id] = user_history  # Save the updated history for the user
                print(f"{message.author} now has level {number} for {day_date}")

                await utils.update_username_lvl(read_channel.guild, user_id, number)

            else:
                print(f"{message.author} NO NO NO {number} for.")


        # If there are any new messages, update the last checked time and save the data
        if all_messages:
            self.last_checked_time = last_message_time.isoformat()  # Save the last checked time as ISO format
            save_json(LVLS_FILE, self.users_lvls)  # Save updated user levels
            save_json(LAST_RUNTIME_FILE, {"last_checked_time": self.last_checked_time})  # Save the last checked time
            print("Data saved.")
        
        if self.user_graph_request_message_id:
            print(f"heyyyy {self.user_graph_request_message_id}")
            await self.send_user_graph(self.user_graph_request_message_id)
        if self.join_graph_request_message_id:
            print(f"heyyyy {self.join_graph_request_message_id}")
            await utils.send_join_graph(self.get_channel(READ_CHAT_CHANNEL_ID).guild, self.join_graph_request_message_id, read_channel)


    async def send_user_graph(self, user_graph_request_message_id):
        """
        Create and send a graph showing all users' level progressions.
        """
        testing_channel = self.get_channel(TESTING_CHAT_CHANNEL_ID)
        read_channel = self.get_channel(READ_CHAT_CHANNEL_ID)

        self.data = self.users_lvls
        if not self.data:
            await testing_channel.send("No user data available.")
            return

        plt.style.use('dark_background')  # DARK THEME 🌑
        plt.figure(figsize=(10, 6))

        # Plot each user's data
        for user_id, user_history in self.data.items():
            dates, levels = utils.fill_missing_days(user_history)

            if dates and levels:
                
                guild = read_channel.guild
                try:
                    member = await guild.fetch_member(int(user_id))  # Always fetch from server
                    username = member.display_name
                except discord.NotFound:
                    # If user not found in guild, fallback to global username
                    user = await self.fetch_user(int(user_id))
                    username = user.name if user else f"User {user_id}"

                username = utils.crop_username(username)
                #print(username)
                
                plt.plot(dates, levels, marker='o', label=username)

                # 🔥 Add level text above each point
                for (x, y) in zip(dates, levels):
                    plt.annotate(
                        str(y),
                        (x, y),
                        textcoords="offset points",
                        xytext=(0, 8),
                        ha='center',
                        fontsize=8,
                        color='white'
                    )

        plt.title("Levels", color='white')
        plt.xlabel("Day", color='white')
        plt.ylabel("Level", color='white')

        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        plt.legend(fontsize="small")
        plt.grid(True, which='both', axis='x', linestyle='--', linewidth=0.5)
        plt.tight_layout()


        await utils.reply_to_whoever_said_graph(read_channel, user_graph_request_message_id)

client = Client(intents=intents)
client.run(token)