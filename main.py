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

import utils_activity as ua
import utils_check_msgs as ucm

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# File paths for storing user levels and last checked data
LVLS_FILE = 'lvls.json'
LAST_RUNTIME_FILE = 'last_runtime.json'
READ_CHAT_CHANNEL_ID = 1361015769248567470
TESTING_CHAT_CHANNEL_ID = 1365761858447081482
LOCAL_TIMEZONE = pytz.timezone('Europe/Ljubljana')
READ_CHAT_CHANNEL_ID = TESTING_CHAT_CHANNEL_ID                  # TESTING KUCIA SERVER
#TESTING_CHAT_CHANNEL_ID = READ_CHAT_CHANNEL_ID
#READ_CHAT_CHANNEL_ID = MY_SERVER = 1365352681211957413         # MY SERVER

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

            if "activity" in message_content:
                all_user_messages = await ua.get_user_messages_across_guild(message.guild, message.author)
                await ua.draw_user_hourly_history(message.guild, message.author, message.channel, all_user_messages)
                return
                
            if "graph" in message_content:
                print(f"Message with 'graph': {message_content}")
                self.lvl_graph_request_message_id = message.id

            if "join" in message_content:
                print(f"Message with 'join': {message_content}")
                self.join_graph_request_message_id = message.id

            number_found = ucm.find_number_in_msg(message.content)

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
                ucm.find_date_words_in_msg(msg_sentence_day_date, message, user_history, user_id, self.users_lvls, number_found, message.author)
                try:
                    member = await read_channel.guild.fetch_member(int(user_id))
                except discord.HTTPException as e:
                    print(f"Could not fetch member {user_id}: {e}, prolly Discord API problem.")
                    continue
                await ucm.update_nickname_and_lvl(member, number_found)
            else:
                print(f"{number_found} insufficient for {message.author}")

        if self.lvl_graph_request_message_id:
            print(f"Graph detected by {self.lvl_graph_request_message_id}")
            await self.send_lvl_graph(
                self.lvl_graph_request_message_id, 
                read_channel,
            )

        if self.join_graph_request_message_id:
            print(f"Join detected by {self.join_graph_request_message_id}")
            await self.send_join_graph( 
                read_channel.guild,
                self.join_graph_request_message_id,
                read_channel,
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
            # Get all members who joined on the current date
            players = [user for user in members if user.joined_at == date]
            for j, player in enumerate(players):
                # Pass the individual member (player) to get_user_nickname_and_crop
                nickname = ucm.get_user_nickname_and_crop(player)
                ax.text(date, members_count_list[i] + j * 5, nickname,
                        ha='center', va='bottom', fontsize=9)

        ax.set_xlabel('Join Date (Mondays)', color='white', labelpad=20)
        ax.set_ylabel('Players in Server', color='white')
        ax.set_title(f'Number of players = {len(join_dates)}', color='white')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        plt.xticks(rotation=0, color='white')
        ax.tick_params(colors='white')
        #ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        # Set ticks every 7 days starting from the closest Monday
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

        # Add week numbers between the x-axis ticks
        first_join_date = min(join_dates)
        current_date = first_join_date
        week_num = 1
        
        while current_date <= max_date:
            # Calculate the midpoint between the ticks
            next_date = current_date + timedelta(days=7)
            if next_date <= max_date:
                mid_date = current_date + timedelta(days=2)  # Approximate middle of the week
                ax.text(mid_date, -1, f"Week {week_num}", ha='center', va='top', fontsize=10, color='white')
                week_num += 1
            current_date = next_date
        # Grid
        ax.grid(True, which='major', axis='x', linestyle='--', linewidth=0.5, color='gray')

        plt.tight_layout()

        await ucm.reply_to_user_message(read_channel, request_message_id, "Joinings")

    async def send_lvl_graph(self, request_message_id, read_channel):
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
            #ucm.add_background_image(ax, all_dates, all_levels)
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
        ax.set_xlabel("Days (Mondays)", color='white')
        ax.set_ylabel("Level", color='white')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        ax.legend(fontsize="small")
        ax.grid(True, which='major', axis='x', linestyle='--', linewidth=0.5, color='gray')
        plt.tight_layout()

        await ucm.reply_to_user_message(read_channel, request_message_id, "levels")

    async def activity(self, message):  # Not using @bot.command()
            await self.draw_user_hourly_history(message.guild, message.author, message.channel)


client = Client(intents=intents)
client.run(token)