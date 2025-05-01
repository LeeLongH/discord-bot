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
    end_date = sorted_history[-1][0] # Latest date
    current_level = sorted_history[0][1] # Oldest level
    idx = 0

    # Loop through each day from current_date to end_date (inclusive)
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



""" async def joined_dates(guild):
    members = guild.members

    members_join_date = sorted(
        [f"{m.name} joined at {(m.joined_at.strftime('%Y-%m-%d') if m.joined_at else 'Unknown')}" for m in members],
        key=lambda x: datetime.strptime(x.split(' joined at ')[1], '%Y-%m-%d') if x.split(' joined at ')[1] != 'Unknown' else datetime.min
    )

    print("\n".join(members_join_date)) """



