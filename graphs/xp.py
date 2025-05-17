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




async def handle_xps_request(client, message):
    """Handles 'xps' requests in messages."""
    print(f"Message with 'xps': {message.content}")
    client.xps_graph_request_message_id = message.id


    xp_dict = {
        1: 27,
        2: 7,
        3: 14,
        4: 30,
        5: 45,
        6: 220,
        7: 370,
        8: 490,
        9: 790,
        10: 960,
        11: 1180,
        12: 1550,
        13: 1790,
        14: 2270,
        15: 2880,
        16: 3270,
        17: 4120,
        18: 4740,
        19: 5610,
        20: 6320,
        21: 7750,
        22: 9140,
        23: 10830,
        24: 12200,
        25: 14000,
        26: 15700,
        27: 18300,
        28: 22500,
        29: 23400,
        30: 26100,
        31: 29400,
        32: 32400,
        33: 35800,
        34: 38700,
        35: 42200,
        36: 45200,
        37: 48900,
        38: 54900,
        39: 61800,
        40: 67900,
        41: 75000,
        42: 81500,
        43: 94400,
        44: 100800,
        45: 110900,
        46: 119500,
        47: 129500,
        48: 138000,
        49: 148400,
        50: 157000,
    }
    
    data = client.users_lvls

    for user_id, date_level_map in data.items():
        if len(date_level_map) < 2:
            continue

        try:
            member = await message.guild.fetch_member(int(user_id))
            username = ucm.get_user_nickname_and_crop(member)
        except Exception as e:
            print(f"Could not fetch member for ID {user_id}: {e}")
            username = f'User {user_id[-4:]}'  # fallback label

        xp_over_time = []
        for date_str in date_level_map:
            level = date_level_map[date_str][-1]
            xp = xp_dict.get(level, 157000 + 11000 * (level - 50))
            xp_over_time.append((datetime.strptime(date_str, "%Y-%m-%d"), xp))

        xp_over_time.sort(key=lambda x: x[0])  # ensure time order
        times = [point[0] for point in xp_over_time]
        xps = [point[1] for point in xp_over_time]

        plt.plot(times, xps, label=username)

    # Hide x-axis time labels
    plt.gca().xaxis.set_visible(False)

    plt.xlabel("Date")
    plt.ylabel("XP")
    plt.title("XP Progression Over Time")
    plt.legend()
    plt.tight_layout()
    plt.grid(True)

    plt.savefig("xp_progression.png")
    plt.close()

    await message.channel.send(file=discord.File("xp_progression.png"))