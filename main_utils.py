import imports as imp

def split_msg(message):
    """
    Check if a number is inside a sentence.
    If exactly one number is found, return it.
    Otherwise, return False.
    """
    words = message.content.split()
    numbers = []

    for word in words:
        number = is_whole_number_int(word)
        
        if number is not None:
            print(f"Number inside msg {number}")

        if number is not None:
            numbers.append(number)
            if len(numbers) > 1:
                return False  # More than one number found → return False immediately

    return numbers[0] if len(numbers) == 1 else 0


def is_whole_number_int(content: str):
    """
    Check if a string is an integer.
    Try whole string, or string without last character.
    """
    for attempt in (content.strip(), content.strip()[:-1]):
        try:
            return int(attempt)
        except ValueError:
            continue
    return None

def crop_username(username):
    """
    Crop usernames so only name and surname is left
    """
    return imp.re.sub(r'[^A-Za-z\s].*$', '', username)

async def reply_to_whoever_said_graph(read_channel, graph_request_message_id):
    """
    Search for the message 'graph' in the specific channel and reply to it, 
    only last person who said graph, if its less than 100 msg ago.
    """
    async for message in read_channel.history(limit=100):
        if message.id == graph_request_message_id:
            buffer = imp.io.BytesIO()
            imp.plt.savefig(buffer, format='png')
            buffer.seek(0)
            imp.plt.close()

            file = imp.discord.File(fp=buffer, filename='levels.png')
            await message.reply(file=file)
            return  # Stop searching once the message is found and replied to
        
def fill_missing_days(user_history):
    dates = []
    levels = []

    # (date, levels) -> (date, last_level) 
    sorted_history = [
        (imp.datetime.strptime(date_str, "%Y-%m-%d").date(), level_list[-1])
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
        current_date += imp.timedelta(days=1)

    return dates, levels
