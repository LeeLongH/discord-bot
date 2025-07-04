import discord
import os
import json
import re
import io
import pytz
from datetime import datetime, timedelta, timezone
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


def find_date_words_in_msg(msg_sentence_day_date, message, user_history, user_id, users_lvls, number_found, message_author):
    words = message.content.lower().split()  # lowercase helps with "Yesterday", etc.
    msg_date_obj = datetime.strptime(msg_sentence_day_date, '%Y-%m-%d')
    
    yesterday_date = (msg_date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
    tomorrow_date = (msg_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
    current_date = msg_date_obj.strftime('%Y-%m-%d')

    if "yesterday" and "tomorrow" in words:
        return
    elif "yesterday" in words:
        return write_new_lvl_n_date(yesterday_date, user_history, user_id, users_lvls, number_found, message_author)
    elif "tomorrow" in words:
        return write_new_lvl_n_date(tomorrow_date, user_history, user_id, users_lvls, number_found, message_author)
    else:
        return write_new_lvl_n_date(current_date, user_history, user_id, users_lvls, number_found, message_author)



def find_number_in_msg(message_text):
    """
    Finds a number in a message if exactly one number is present.
    A valid number must be followed by a punctuation mark (!, ., whitespace, or end of string).
    Returns the number as int if valid, else 0.
    """
    # Match full integers with optional punctuation after them
    matches = re.findall(r'\b(\d+)(?=[!\.\s]|$)', message_text)

    if len(matches) == 1:
        number = int(matches[0])
        print(f"Number {number} found")
        return number

    print("No valid number found or multiple numbers.")
    return 0


def write_new_lvl_n_date(msg_sentence_day_date, user_history, user_id, users_lvls, number_found, message_author):
    if msg_sentence_day_date not in user_history:
        user_history[msg_sentence_day_date] = []

    user_history[msg_sentence_day_date].append(number_found)

    users_lvls[user_id] = user_history  # Update shared dict
    print(f"{message_author} levelled up to {number_found} for {msg_sentence_day_date}")


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
    
        if not last_message_time:
            last_message_time = datetime.now(timezone.utc)

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
        return re.sub(r'\s*lvl\S*(\s\S*)*$|[^A-Za-z\s’\'].*$', '', member.nick , flags=re.IGNORECASE)
    else: 
        #nickname = member.name 
        print("No nickname, just username for @ ",member.name)
        return member.name

def get_user_nickname(member):
    """
    Get user's nickname, and crop it
    """
    if member.nick:
        nickname = member.nick
        has_nickname = True
    else: 
        nickname = member.name 
        print("No nickname, just username.")
        #print(nickname)
        has_nickname = False
    return (nickname, has_nickname)

async def update_nickname_and_lvl(member, level):
    nickname, has_nickname = get_user_nickname(member)
    print("old nick:", nickname)

    if not has_nickname:
        print("NICKNAME NOT FOUND; REQUIRED ATTENTION")

    if member.guild.me.guild_permissions.manage_nicknames:
        try:
            number_matches = list(re.finditer(r"\d+", nickname, re.UNICODE))
            print("Number matches found:")
            for m in number_matches:
                print(f"-> {m.group()} at position {m.span()}")

                if m == level: # member changed nickname level himself
                    return

            # Filter only numbers greater than the new level
            valid_matches = [m for m in number_matches if int(m.group()) < level]

            if valid_matches:
                # Pick closest number greater than level
                closest_match = min(valid_matches, key=lambda m: abs(int(m.group()) - level))
                start, end = closest_match.span()
                old_number = closest_match.group()

                new_nickname = nickname[:start] + f"{level}" + nickname[end:]
                print(f"Replaced {old_number} in nickname: {nickname} -> {new_nickname}")
            else:
                #new_nickname = f"{nickname} lvl {level}"
                new_nickname = nickname
                print(f"No suitable number > {level} found. Appending instead: {member.name} -> {new_nickname}")

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
    #print("selected theme: " + selected_theme)
    #print(THEME_LIST)
    
    return selected_theme

def add_background_image(ax, xlim, ylim, alpha=0.3):
    """
    Adds a background image in 50% of cases.
    """
    send_image = random.choice([True, False])
    #send_image = True

    if not send_image:
        #print("No background image selected.")
        return  # No background

    bg_image_name = get_random_theme()
    bg_image_path = os.path.join("slike", bg_image_name)
    #print("Using background image:", bg_image_name)

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
        (
            datetime.strptime(date_str, "%Y-%m-%d").date(), 
            level_list[0] if i == 0 else level_list[-1]
        )
        for i, (date_str, level_list) in enumerate(sorted(user_history.items()))
        if level_list  # Only include dates with non-empty level lists
    ]

    current_date = sorted_history[0][0] # Oldest date
    #end_date = sorted_history[-1][0] # Latest date
    end_date = datetime.today().date()  # Today's date
    current_level = sorted_history[0][1] # Oldest level
    idx = 0

    while current_date <= end_date:
        # Update current_level if we're at a known history date
        if idx < len(sorted_history) and current_date == sorted_history[idx][0]:
            current_level = sorted_history[idx][1]
            idx += 1

        # Only store data from 10.6.2025 onward
        if current_date >= datetime(2025, 6, 1).date():
            dates.append(current_date)
            levels.append(current_level)

        current_date += timedelta(days=1)

    return dates, levels


def fill_last_days(user_history):
    dates = []
    levels = []

    # Pretvori in sortiraj zgodovino po datumu
    sorted_history = sorted(
        (datetime.strptime(date_str, "%Y-%m-%d").date(), level_list[-1])
        for date_str, level_list in user_history.items()
        if level_list
    )

    # Če ni zgodovine, vrni prazno
    if not sorted_history:
        return [], []

    last_date = sorted_history[-1][0]
    today = datetime.today().date()

    level = sorted_history[-1][1]

    # Če je zadnji vnos starejši od 10 dni, ne vračaj ničesar
    if (today - last_date).days > max(8, 5 + level // 10 + level // 20):
        return [], []

    # Dodaj obstoječe datume/levele od 2025.6.1 naprej
    for date, level in sorted_history:
        if date >= datetime(2025, 5, 7).date():
            dates.append(date)
            levels.append(level)

    # Dodaj še današnji datum z zadnjim znanim levelom
    last_level = sorted_history[-1][1]
    dates.append(today)
    levels.append(last_level)

    return dates, levels






async def process_user_level_update(client, message, user_id, number_found, msg_sentence_day_date):
    """Handles the user level update process."""
    user_history = client.users_lvls.get(user_id, {})
    user_current_lvl = get_user_current_level(user_history, number_found)
    print(f"-> Old lvl: {user_current_lvl}\n-> New lvl?: {number_found}")

    # Determine if the level change is valid
    jump = max(1, 6 - min(user_current_lvl, 49) // 10)
    if number_found > user_current_lvl and number_found <= user_current_lvl + jump:
        await update_user_level(client, message, msg_sentence_day_date, user_history, user_id, number_found)
    else:
        print(f"{number_found} insufficient for {message.author}")


def get_user_current_level(user_history, number_found):
    """Gets the current user level from history, or sets it based on the found number."""
    if user_history:
        return get_user_level_from_JSON(user_history)
    else:
        print("No prior lvl entry for this user")
        return number_found - 1
    
async def update_user_level(client, message, msg_sentence_day_date, user_history, user_id, number_found):
    """Updates the user's level and nickname."""
    find_date_words_in_msg(msg_sentence_day_date, message, user_history, user_id, client.users_lvls, number_found, message.author)
    try:
        member = await message.guild.fetch_member(int(user_id))
    except discord.HTTPException as e:
        print(f"Could not fetch member {user_id}: {e}, prolly Discord API problem.")
        return

    await update_nickname_and_lvl(member, number_found)


async def handle_graph_responses(client, read_channel):
    """Handles sending graph responses based on requests."""
    if client.levels_graph_request_message_id:
        print(f"Levels Graph detected by {client.levels_graph_request_message_id}")
        await client.send_level_graph(client.levels_graph_request_message_id, read_channel)

    if client.join_graph_request_message_id:
        print(f"Join detected by {client.join_graph_request_message_id}")
        await client.send_join_graph(read_channel.guild, client.join_graph_request_message_id, read_channel)
    
    """ if client.xps_graph_request_message_id:
        print(f"Xmp detected by {client.xps_graph_request_message_id}")
        await client.send_xps_graph(read_channel.guild, client.xps_graph_request_message_id, read_channel)
 """