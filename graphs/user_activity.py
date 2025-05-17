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
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import utils_check_msgs as ucm

from collections import defaultdict

async def handle_activity_request(message):
    """Handles 'activity' requests in messages."""

    matched_user = await get_activity_arg(message)

    # If a matching nickname was found, use that user
    if matched_user:
        all_user_messages = await get_user_messages_across_guild(message.guild, matched_user)
        await draw_activity_graph(message.guild, matched_user, message.channel, all_user_messages)
    else:
        # Default to author if no nickname matched
        all_user_messages = await get_user_messages_across_guild(message.guild, message.author)
        await draw_activity_graph(message.guild, message.author, message.channel, all_user_messages)


async def draw_activity_graph(guild, user_requested, channel, messages):
    return
    if not messages:
        await channel.send("No message history found.")
        return

    # Extract hours (in local time or UTC depending on your preference)
    message_hours = [msg.created_at.hour for msg in messages]

    # Count how many messages per hour
    hour_counts = Counter(message_hours)

    # Fill in missing hours with 0
    all_hours = list(range(24))
    message_counts = [hour_counts.get(h, 0) for h in all_hours]

    # Plotting
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(all_hours, message_counts, color='skyblue')
    ax.set_xticks(all_hours)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Messages Sent")
    ax.set_title(f"Hourly Message Activity: {user_requested.display_name} utc+0", color='white')
    ax.tick_params(colors='white')
    ax.yaxis.label.set_color('white')
    ax.xaxis.label.set_color('white')
    ax.title.set_color('white')
    plt.tight_layout()

    # Save plot to a BytesIO stream
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)

    # Send the image
    file = discord.File(fp=buf, filename="activity.png")
    await channel.send(file=file)

async def get_user_messages_across_guild(guild, user):
    """
    Retrieves all messages sent by a specific user across all accessible text channels in the guild.
    """
    messages = []
    for channel in guild.text_channels:
        try:
            async for msg in channel.history(limit=None):
                if msg.author == user:
                    messages.append(msg)
        except (discord.Forbidden, discord.HTTPException):
            continue  # Skip channels where access fails
    return messages

async def get_activity_arg(message):
    content = message.content
    match = re.search(r'(?<=\bactivity\s)\w+', content, re.IGNORECASE)

    if not match:
        await message.channel.send("No 'activity' argument found in the message.")
        return

    target_nick = match.group()

    for member in message.guild.members:
        nickname = ucm.get_user_nickname(member)
        if nickname and nickname.split()[0].lower() == target_nick.lower():
            #await message.channel.send(f"Found: {member.mention} has the nickname '{nickname}'")
            print("hmmmm")
            return member
        print(nickname, target_nick, nickname.lower() == target_nick.lower() )
    for member in message.guild.members:
        nickname = member.name
        if nickname and nickname.lower() == target_nick.lower():
            #await message.channel.send(f"Found: {member.mention} has the nickname '{nickname}'")
            print("hmmmm")
            return member
        print(nickname, target_nick, nickname.lower() == target_nick.lower() )

    #await message.channel.send("No matching nickname found.")
