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
import matplotlib.image as mpimg

import random

THEME_FOLDER = "slike"
THEME_LIST = [f for f in os.listdir(THEME_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

def find_number_in_msg(message):
    """
    Check if a number is inside a sentence.
    If exactly one number is found and it's followed by !, ., or whitespace, return it.
    Otherwise, return 0.
    """
    words = message.content.split()
    
    for word in words:
        num_part = ""
        
        for i, char in enumerate(word):
            if char.isdigit():
                num_part += char
            else:
                # Check if the number ends with valid punctuation
                if num_part and char in ('!', '.', ' ', '\n'):
                    print(f"Number {num_part} found")
                    return int(num_part)
                break
        
        if num_part and i == len(word) - 1:  # If number reaches the end of the word
            print(f"Number {num_part} found")
            return int(num_part)
    return 0

def utils_check_msgs(channel):
    if channel is None:
        print("Error: Could not find the channel.")
        return
    
async def get_all_msgs(last_checked_time, read_channel):
        """
        Check msgs by batches
        """
        after_time = datetime.fromisoformat(last_checked_time) if last_checked_time else None
        all_messages = []
        all_msgs_checked = False
        last_message_time = None

        while not all_msgs_checked:
            batch = []  # Temporary storage for 100 messages in each batch
            async for message in read_channel.history(limit=100, after=after_time):
                batch.append(message)
            if not batch:
                break  # No msgs found
            batch.sort(key=lambda msg: msg.created_at)  # Sort messages by creation date, oldest first
            for message in batch:
                if after_time and message.created_at <= after_time:
                    continue  # Skip  already processed msgs
                all_messages.append(message)
                last_message_time = message.created_at
            if len(batch) < 100:  # No more msgs
                all_msgs_checked = True
            else:
                after_time = last_message_time
        print(f"\nNew msgs: {len(all_messages)}\n")
        return (all_messages, last_message_time)

def get_user_level_from_JSON(user_history):
    last_saved_date = next(reversed(user_history))
    levels_array = user_history.get(last_saved_date)
    last_level = levels_array[-1] if levels_array else 0
    return last_level

def get_user_nickname_and_crop(member):
    """
    Get user's nickname, and crop it
    """
    if member.nick:
        nickname = member.nick 
    else: 
        nickname = member.name 
        print("No nickname, just username.")
    return re.sub(r"[^A-Za-z\s\.’].*$", '', nickname)

def get_user_nickname(member):
    """
    Get user's nickname, and crop it
    """
    if member.nick:
        nickname = member.nick 
    else: 
        nickname = member.name 
        print("No nickname, just username.")
    return nickname

async def update_nickname_and_lvl(member, level):

    nickname = get_user_nickname(member)
    print("nicknme: ", nickname)

    if member.guild.me.guild_permissions.manage_nicknames:
        try:
            # Find the last number in the username and remember its position
            number_in_nickname_found = re.search(r"(\d+)(?!.*\d)", nickname)  # Match the last number in the username
            print("number_in_nickname_found", number_in_nickname_found)
            if number_in_nickname_found:
                start, end = number_in_nickname_found.span()  # Find old level position
                print("start n end", start, end)

                new_nickname = nickname[:start] + f"{level}" + nickname[end:]  # Replace old level with new

                print(f"Nickname of {nickname} changed to {new_nickname}")
            else:
                new_nickname = f"{nickname} lvl {level}"
                print(f"Number in nickname not found, just append lvl to {member.name} -> {new_nickname}")
            await member.edit(nick=new_nickname)

        except Exception as e:
            print(f"Failed to change nickname: {e}")
    else:
        print("No permission to change nickname.")

async def reply_to_user_message(read_channel, request_message_id, file_name):

    file_path = f"{file_name}.png"

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    file = discord.File(fp=buffer, filename=file_path)

    try:
        message = await read_channel.fetch_message(request_message_id)
        await message.reply(file=file)
    except discord.NotFound:
        print(f"Message with ID {request_message_id} not found.")
    except discord.HTTPException as e:
        print(f"Failed to fetch or reply to message: {e}")

def get_random_theme():
    if not THEME_LIST:
        raise ValueError("Ni slik v mapi.")
    selected_theme = random.choice(THEME_LIST)
    print("selected theme: " + selected_theme)
    print(THEME_LIST)
    
    return selected_theme

def add_background_image(ax, xlim, ylim, alpha=0.3):
    """
    Adds a background image in 50% of cases.
    """
    send_image = random.choice([True, False])
    #send_image = True

    if not send_image:
        print("No background image selected.")
        return  # No background

    bg_image_name = get_random_theme()
    bg_image_path = os.path.join("slike", bg_image_name)
    print("Using background image:", bg_image_name)

    try:
        img = mpimg.imread(bg_image_path)
        min_x, max_x = xlim
        min_y, max_y = ylim
        ax.imshow(img, extent=[min_x, max_x, min_y, max_y], aspect='auto', zorder=0, alpha=alpha)
    except FileNotFoundError:
        print(f"Background image '{bg_image_name}' not found. Skipping background.")

def fill_missing_days(user_history):
    dates = []
    levels = []

    # (date, levels) -> (date, last_level) 
    sorted_history = [
        (datetime.strptime(date_str, "%Y-%m-%d").date(), level_list[-1])
        for date_str, level_list in user_history.items()
        if level_list  # Only include dates with non-empty level lists
    ]

    current_date = sorted_history[0][0] # Oldest date
    #end_date = sorted_history[-1][0] # Latest date
    end_date = datetime.today().date()  # Today's date
    current_level = sorted_history[0][1] # Oldest level
    idx = 0

    # Loop through each day from oldest date to newest
    while current_date <= end_date:
        dates.append(current_date)
        
        # Check if the current_date matches a date in sorted_history
        if idx < len(sorted_history) and current_date == sorted_history[idx][0]:
            # If there's a match, update the current_level with the corresponding level
            current_level = sorted_history[idx][1]
            # Move to the next item in sorted_history
            idx += 1
        
        # Append the current_level to the levels list
        levels.append(current_level)
        
        # Move to the next day by incrementing current_date
        current_date += timedelta(days=1)

    return dates, levels