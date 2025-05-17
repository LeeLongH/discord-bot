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

# In graphs/all_join.py
async def handle_join_graph_request(client, message):
    """Handles 'join' requests in messages."""
    print(f"Message with 'join': {message.content}")
    client.join_graph_request_message_id = message.id
