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
import random

import graphs.user_activity as ua
import utils_check_msgs as ucm
import graphs.all_join as ujoin
import graphs.all_levels as ulvl
import graphs.xp as uxp

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# File paths for storing user levels and last checked data
LVLS_FILE = 'lvls.json'
LAST_RUNTIME_FILE = 'last_runtime.json'
READ_CHAT_CHANNEL_ID = 1381883455717114009
TESTING_CHAT_CHANNEL_ID = 1381883601343348747
LOCAL_TIMEZONE = pytz.timezone('Europe/Ljubljana')
#READ_CHAT_CHANNEL_ID = TESTING_CHAT_CHANNEL_ID                  # TESTING CREW SERVER
#TESTING_CHAT_CHANNEL_ID = READ_CHAT_CHANNEL_ID
#READ_CHAT_CHANNEL_ID = MY_SERVER = 1365352681211957413         # MY SERVER

def save_json(path, data):
    """
    Save data to a JSON file.
    """
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

# Helper functions to load and save JSON files
def load_json(path, default):
    """
    Load data from a JSON file. If the file doesn't exist, return the default value.
    """
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default

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

        self.levels_graph_request_message_id = 0
        self.join_graph_request_message_id = 0

    def update_runtime(self, last_message_time, LVLS_FILE, LAST_RUNTIME_FILE):
        """Updates the last checked time and saves state."""
        self.last_checked_time = last_message_time.isoformat()
        save_json(LVLS_FILE, self.users_lvls)
        save_json(LAST_RUNTIME_FILE, {"last_checked_time": self.last_checked_time})
        print("Time updated")

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
        all_messages, last_message_time = await ucm.get_all_msgs(self.last_checked_time, read_channel)

        # Process each message individually
        for message in all_messages:
            if message.author.bot:
                continue  # Skip bot messages

            user_id = str(message.author.id)
            local_time = message.created_at.astimezone(LOCAL_TIMEZONE)
            msg_sentence_day_date = local_time.strftime('%Y-%m-%d')

            message_content = message.content.lower()

            # Handle specific message commands
            if "activitys" in message_content:
                await ua.handle_activity_request(message)
            
            if "levels" in message_content:
                await ulvl.handle_levels_graph_request(client, message)

            if "join" in message_content:
                await ujoin.handle_join_graph_request(client, message)
            
            if "xps" in message_content:
                await uxp.handle_xps_request(client, message)


            # Process level updates from numbers in message
            number_found = ucm.find_number_in_msg(message.content)
            if number_found == 0:
                print("No numbers.")
                continue

            # Update user level if necessary
            await ucm.process_user_level_update(client, message, user_id, number_found, msg_sentence_day_date)

        # Handle graph request responses
        await ucm.handle_graph_responses(self, read_channel)

        # Save the updated state
        self.update_runtime(last_message_time, LVLS_FILE, LAST_RUNTIME_FILE)

    async def send_join_graph(self, guild, request_message_id, read_channel):
        members = guild.members
        join_dates = [member.joined_at for member in members if member.joined_at and not member.bot]
        join_dates.sort()
        members_count_list = list(range(1, len(join_dates) + 1))

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))

        if join_dates and members_count_list:
            member_count = len(members_count_list)
            extra_days = member_count // 10  # 1 day per 10 members
            # Compute padded limits
            min_date = min(join_dates) - timedelta(days=extra_days)
            max_date = max(join_dates) + timedelta(days=extra_days)
            max_count = max(members_count_list)
            ax.set_xlim(min_date, max_date)
            ax.set_ylim(0, max_count + 1)

            # Use padded ranges for background image
            ax.set_xlim(min_date, max_date)
            ax.set_ylim(0, max_count + 1)
            ucm.add_background_image(ax, [min_date, max_date], [0, max_count + 1])


        ax.plot(join_dates, members_count_list, color='blue', label='X axis')
        ax.scatter(join_dates, members_count_list, color='cyan', s=20, label='Y axis')

        for i, date in enumerate(join_dates):
            players = [user for user in members if user.joined_at == date]
            for j, player in enumerate(players):
                nickname = ucm.get_user_nickname_and_crop(player)
                
                # Alternate globally: use (i + j) to alternate label position
                direction = 1 if (i + j) % 2 == 0 else -1  # 1 = right, -1 = left
                x_offset = timedelta(days=3 * direction)  # 6-hour shift
                y_offset = members_count_list[i]  # keep same Y for simplicity
                
                ax.text(date + x_offset, y_offset, nickname,
                        ha='left' if direction > 0 else 'right',
                        va='center', fontsize=9)
                ax.plot([date, date + x_offset], [members_count_list[i]]*2, color='gray', linewidth=0.5)

        show_week_label = len(join_dates) <= 30  # Show full 'Week X' labels only if 30 or fewer members

        ax.set_xlabel('Join Date (Derby start)', color='white', labelpad=20)
        ax.set_ylabel('Players in Server', color='white')
        ax.set_title(f'Number of players = {len(join_dates)}', color='white')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.xticks(rotation=0, color='white')
        ax.tick_params(colors='white')
        #ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        # Set ticks every 7 days starting from the closest Monday
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.TU, interval=1))
        if show_week_label:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))


        # Add week numbers between the x-axis ticks
        first_join_date = min(join_dates)
        current_date = first_join_date
        week_num = 1
        leftmost_date = current_date + timedelta(days=2)  # Approximate middle of first week
        if not show_week_label:
            # Add just the "Week" label once on the far left
            ax.text(leftmost_date - timedelta(days=10), -3, "Week", ha='right', va='top', fontsize=10, color='white')

        while current_date <= max_date:
            # Calculate the midpoint between the ticks
            next_date = current_date + timedelta(days=7)
            if next_date <= max_date:
                if show_week_label:
                    mid_date = current_date + timedelta(days=2)  # Approximate middle of the week
                    ax.text(mid_date, -3, f"Week {week_num}", ha='center', va='top', fontsize=10, color='white')
                else:
                    mid_date = current_date + timedelta(days=1)  # Approximate middle of the week
                    ax.text(mid_date, -3, f"{week_num}", ha='center', va='top', fontsize=10, color='white')
            week_num += 1
            current_date = next_date
        # Grid
        ax.grid(True, which='major', axis='x', linestyle='--', linewidth=0.5, color='gray')

        plt.tight_layout()

        await ucm.reply_to_user_message(read_channel, request_message_id, "Joinings")

    async def send_level_graph(self, request_message_id, read_channel):
        self.data = self.users_lvls

        # First, collect all data to compute min/max ranges
        all_dates = []
        all_levels = []
        processed_data = {}  # To avoid recomputation

        for user_id, user_history in self.data.items():
            dates, levels = ucm.fill_missing_days(user_history)
            if dates and levels:
                all_dates.extend(dates)
                all_levels.extend(levels)
                processed_data[user_id] = (dates, levels)
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))

        if all_dates and all_levels:
            ax.set_xlim(min(all_dates), max(all_dates) + timedelta(days=1))  # Padding on right
            ax.set_ylim(0, max(all_levels) + 1)  # Padding on top
            ucm.add_background_image(ax, [min(all_dates), max(all_dates) + timedelta(days=1)], [0, max(all_levels) + 1])

                
        # Plot each user's data
        for user_id, (dates, levels) in processed_data.items():
            try:
                member = await read_channel.guild.fetch_member(int(user_id))
            except discord.NotFound:
                print(f"User {user_id} not in the server")
                continue

            nickname = ucm.get_user_nickname_and_crop(member)
            ax.plot(dates, levels, marker='o', label=nickname)
    	
            #print(f"User: {nickname}")
            #print(f"Levels: {levels}")
            #print(f"Dates: {dates}")

            for i, (x, y) in enumerate(zip(dates, levels)):
                # Check if level increased from previous or to next day
                prev_level = levels[i - 1] if i > 0 else None
                next_level = levels[i + 1] if i < len(levels) - 1 else None

                level_increased = (
                    (prev_level is not None and y > prev_level) or
                    (next_level is not None and next_level > y)
                )

                if level_increased or i==0:
                    ax.annotate(
                        str(y),
                        (x, y),
                        textcoords="offset points",
                        xytext=(0, 8),
                        ha='center',
                        fontsize=8,
                        color='white'
                    )


        ax.set_title("Levels", color='white')
        ax.set_xlabel("Days (Line = Tuesday / Derby start)", color='white')
        ax.set_ylabel("Level", color='white')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.TU))
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        ax.legend(fontsize="small")
        ax.grid(True, which='major', axis='x', linestyle='--', linewidth=0.5, color='gray')
        plt.tight_layout()

        await ucm.reply_to_user_message(read_channel, request_message_id, "levels")

    #async def activity(self, message):  # Not using @bot.command()
    #        await self.handle_activity_request(message)

    async def send_xps_graph(self, message):  # Not using @bot.command()
        await self.handle_xps_request(message)


client = Client(intents=intents)
client.run(token)