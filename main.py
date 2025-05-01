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
from matplotlib.ticker import MaxNLocator

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

        self.lvl_graph_request_message_id = 0
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
        read_channel = self.get_channel(READ_CHAT_CHANNEL_ID)
        (all_messages, last_message_time) = await ucm.get_all_msgs(self.last_checked_time, read_channel)

        for message in all_messages:

            if message.author.bot:
                continue  # Skip bot messages

            user_id = str(message.author.id)
            local_time = message.created_at.astimezone(LOCAL_TIMEZONE)
            msg_sentence_day_date = local_time.strftime('%Y-%m-%d')

            message_content = message.content.lower()
            if "graph" in message_content:
                print(f"Message with 'graph': {message_content}")
                self.lvl_graph_request_message_id = message.id

            if "join" in message_content:
                print(f"Message with 'join': {message_content}")
                self.join_graph_request_message_id = message.id

            number_found = ucm.find_number_in_msg(message)

            if number_found == 0:
                print("No numbers.")
                continue

            user_history = self.users_lvls.get(user_id, {})

            if user_history:
                user_current_lvl = ucm.get_user_level_from_JSON(user_history)
            else:
                user_current_lvl = number_found - 1
                print("No prior lvl entry for this user")

            print(f"-> Old lvl: {user_current_lvl}\n-> New lvl?: {number_found}")

            jump = max(1, 6 - min(user_current_lvl, 49) // 10)
            if number_found > user_current_lvl and number_found <= user_current_lvl + jump:
                if msg_sentence_day_date not in user_history:
                    user_history[msg_sentence_day_date] = []
                user_history[msg_sentence_day_date].append(number_found)
                self.users_lvls[user_id] = user_history
                print(f"{message.author} levelled up to {number_found} for {msg_sentence_day_date}")
                member = await read_channel.guild.fetch_member(user_id)
                await utils.update_nickname_and_lvl(member, number_found)
            else:
                print(f"{number_found} insufficient for {message.author}")

        if self.lvl_graph_request_message_id:
            print(f"Graph detected by {self.lvl_graph_request_message_id}")
            await self.send_user_graph(
                self.lvl_graph_request_message_id, 
                read_channel
            )

        if self.join_graph_request_message_id:
            print(f"Join detected by {self.join_graph_request_message_id}")
            await self.send_join_graph( 
                read_channel.guild,
                self.join_graph_request_message_id,
                read_channel
            )

        if all_messages:
            self.last_checked_time = last_message_time.isoformat()
            save_json(LVLS_FILE, self.users_lvls)
            save_json(LAST_RUNTIME_FILE, {"last_checked_time": self.last_checked_time})
            print("Time updated")

    async def send_join_graph(self, guild, request_message_id, read_channel):
        members = guild.members

        join_dates = [member.joined_at for member in members if member.joined_at]
        join_dates.sort()

        members_count_list = []
        total_members = 0
        for date in join_dates:
            total_members += 1
            members_count_list.append(total_members)

        plt.style.use('dark_background')
        plt.figure(figsize=(10, 6))
        plt.plot(join_dates, members_count_list, color='blue', label='X axis')
        plt.scatter(join_dates, members_count_list, color='cyan', s=20, label='Y axis')

        for i, date in enumerate(join_dates):
            players = [user.display_name if user.nick is None else user.nick for user in members if user.joined_at == date]
            for j, player in enumerate(players):
                plt.text(date, members_count_list[i] + j * 5, player, ha='center', va='bottom', fontsize=9)

            """
            for i, date in enumerate(join_dates):
            players = [get_nickname_by_id(user.id) if get_nickname_by_id(user.id) else user.display_name for user in members if user.joined_at == date]
            for j, player in enumerate(players):
            plt.text(date, members_count_list[i] + j * 5, player, ha='center', va='bottom', fontsize=9)
            """

        plt.xticks(rotation=45)
        plt.xlabel('Join Date')
        plt.ylabel('Players in Server')
        plt.title('Players Joining Over Time')
        plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.tight_layout()

        await ucm.reply_to_user_message(read_channel, request_message_id, "Joinings.png")

    async def send_user_graph(self, request_message_id, read_channel):
        """
        Create and send a graph showing all users' level progressions.
        """
        self.data = self.users_lvls

        plt.style.use('dark_background')
        plt.figure(figsize=(10, 6))

        # Plot each user's data
        for user_id, user_history in self.data.items():
            dates, levels = utils.fill_missing_days(user_history)

            if dates and levels:
  
                try:
                    member = await read_channel.guild.fetch_member(int(user_id))
                except discord.NotFound:
                    print(f"User {user_id} not in the server")
                    continue

                nickname = ucm.get_user_nickname_and_crop(member)
                #print(username)
                
                plt.plot(dates, levels, marker='o', label=nickname)

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

        await ucm.reply_to_user_message(read_channel, request_message_id, "levels.png")

client = Client(intents=intents)
client.run(token)