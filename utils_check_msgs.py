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
THEME_LIST = ["", "dprk-flag-dark.jpg", "dprk-flag-rocket.jpg"]


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
    return re.sub(r'[^A-Za-z\s].*$', '', nickname)

async def update_nickname_and_lvl(member, level):

    nickname = get_user_nickname_and_crop(member)

    if member.guild.me.guild_permissions.manage_nicknames:
        try:
            # Find the last number in the username and remember its position
            number_in_nickname_found = re.search(r"(\d+)(?!.*\d)", nickname)  # Match the last number in the username

            if number_in_nickname_found:
                start, end = number_in_nickname_found.span()  # Find old level position

                new_nickname = nickname[:start] + f"{level}" + nickname[end:]  # Replace old level with new

                print(f"Nickname of {member.name} changed to {new_nickname}")
            else:  # Number is found, just append the level
                new_nickname = f"{nickname}_lvl{level}"
                print(f"Successfully changed nickname for {member.name} to {new_nickname}")
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

def add_background_image(ax, bg_image_path, data_x, data_y, alpha=0.3):
    """
    Adds a background image to the plot using the given data's x and y bounds.

    ax: The axes object to add the background image to.
    bg_image_path: Path to the background image.
    data_x: List or array of x-axis values.
    data_y: List or array of y-axis values.
    alpha: Transparency level for the background image (default is 0.3).
    """
    print("bg_image_path: ", bg_image_path)
    try:
        img = mpimg.imread(bg_image_path)
        min_x, max_x = min(data_x), max(data_x)
        min_y, max_y = min(data_y), max(data_y)
        ax.imshow(img, extent=[min_x, max_x, min_y, max_y], aspect='auto', zorder=0, alpha=alpha)
    except FileNotFoundError:
        print(f"Background image '{bg_image_path}' not found. Falling back to dark theme.")

def get_random_theme():
    num = THEME_LIST[random.randint(0,2)]
    print(num)
    return num