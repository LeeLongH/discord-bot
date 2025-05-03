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

from collections import defaultdict


async def draw_user_hourly_history(guild, user, channel, messages):
    print("entered")
    
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
    ax.set_title(f"Hourly Message Activity: {user.display_name}", color='white')
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
