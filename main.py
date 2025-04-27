import imports as imp
import main_utils as utils

imp.load_dotenv()
token = imp.os.getenv("DISCORD_TOKEN")

# File paths for storing user levels and last checked data
LVLS_FILE = 'lvls.json'
LAST_RUNTIME_FILE = 'last_runtime.json'
READ_CHAT_CHANNEL_ID = 1361015769248567470
TESTING_CHAT_CHANNEL_ID = 1365761858447081482
LOCAL_TIMEZONE = imp.pytz.timezone('Europe/Ljubljana')
READ_CHAT_CHANNEL_ID = TESTING_CHAT_CHANNEL_ID

# Helper functions to load and save JSON files
def load_json(path, default):
    """
    Load data from a JSON file. If the file doesn't exist, return the default value.
    """
    if imp.os.path.exists(path):
        with open(path, 'r') as f:
            return imp.json.load(f)
    return default

def save_json(path, data):
    """
    Save data to a JSON file.
    """
    with open(path, 'w') as f:
        imp.json.dump(data, f, indent=4)

# Set up intents to allow the bot to access message content
intents = imp.discord.Intents.default()
intents.message_content = True

class Client(imp.discord.Client):
    def __init__(self, *args, **kwargs):
        """
        Initialize the bot client.
        """
        super().__init__(*args, **kwargs)

        # JSONs
        self.users_lvls = load_json(LVLS_FILE, {})
        self.last_ran_data = load_json(LAST_RUNTIME_FILE, {})
        self.last_checked_time = self.last_ran_data.get("last_checked_time")  # Last check time

        self.user_requested_graph = "" # graph not requested

    async def on_ready(self):
        """
        This function runs when the bot is successfully logged in and ready to work.
        """
        print(f'Logged in as {self.user}!')

        # Check the messages and process them
        await self.check_messages()

        # Close the bot after processing messages
        await self.close()

    async def check_messages(self):
        """
        This function checks all messages sent in the channel after the last run time.
        It processes only those that are numbers within the allowed range.
        """

        read_channel = self.get_channel(READ_CHAT_CHANNEL_ID)
        if read_channel is None:
            print("Error: Could not find the channel.")
            return

        # If there's no last checked time, we check all messages
        after_time = imp.datetime.fromisoformat(self.last_checked_time) if self.last_checked_time else None
        all_messages = []
        all_msgs_checked = False
        last_message_time = None  # To keep track of the last message's timestamp

        # Loop to get all messages after the last checked time
        while not all_msgs_checked:
            batch = []  # Temporary storage for messages in each batch
            # Fetch the next batch of messages (100 at a time)
            async for message in read_channel.history(limit=100, after=after_time):
                batch.append(message)

            if not batch:
                break  # Break if no messages are found

            # Sort the batch by the message's creation date, oldest first
            batch.sort(key=lambda msg: msg.created_at)  # Sort messages by creation date in ascending order

            for message in batch:
                if after_time and message.created_at <= after_time:
                    continue  # Skip messages already processed

                all_messages.append(message)
                last_message_time = message.created_at  # Update the last message's time

            # If we have less than 100 messages, we've reached the end
            if len(batch) < 100:
                all_msgs_checked = True
            else:
                # If there are still more messages, continue after the last processed message
                after_time = last_message_time

        print(f"\nNew msgs: {len(all_messages)}\n")

        # Process each message to check if it's a valid number
        for message in all_messages:
            if message.author.bot:
                continue  # Skip bot messages

            if message.content == "graph":
                print(f"message: {message}")
                self.user_requested_graph = message.author.id
                self.graph_request_message_id = message.id  # Store the message ID for later

            number = utils.split_msg(message) 

            if number == 0:  # No number (or too many numbers) found
                print(f"No numbers.")
                continue

            user_id = str(message.author.id)  # Get the user ID as a string

            local_time = message.created_at.astimezone(LOCAL_TIMEZONE)
            day_date = local_time.strftime('%Y-%m-%d')
            
            user_history = self.users_lvls.get(user_id, {})  # Get the user's level history (default to empty dict)

            # Get the user's last level for today (default to 0)
            if user_history:
                last_saved_date = max(user_history.keys())
                levels_array = user_history.get(last_saved_date, [])
                last_level = levels_array[-1] if levels_array else 0
            else:
                last_level = number - 1

            print(f"-> old user lvl: {last_level}\n-> new user lvl: {number}")

            # If the number is within 3 levels higher than the user's last level, update the level
            if number > last_level and number <= last_level + 3:
                if day_date not in user_history:
                    user_history[day_date] = []  # Create list if not exists
                user_history[day_date].append(number)  # Add number to list
                self.users_lvls[user_id] = user_history  # Save the updated history for the user
                print(f"{message.author} now has level {number} for {day_date}")

        # If there are any new messages, update the last checked time and save the data
        if all_messages:
            self.last_checked_time = last_message_time.isoformat()  # Save the last checked time as ISO format
            save_json(LVLS_FILE, self.users_lvls)  # Save updated user levels
            #save_json(LAST_RUNTIME_FILE, {"last_checked_time": self.last_checked_time})  # Save the last checked time
            print("Data saved.")
        
        if self.graph_request_message_id:
            await self.send_user_graph(self.graph_request_message_id)

    async def send_user_graph(self, graph_request_message_id):
        """
        Create and send a graph showing all users' level progressions.
        """
        testing_channel = self.get_channel(TESTING_CHAT_CHANNEL_ID)
        read_channel = self.get_channel(READ_CHAT_CHANNEL_ID)

        self.data = self.users_lvls
        if not self.data:
            await testing_channel.send("No user data available.")
            return

        imp.plt.style.use('dark_background')  # DARK THEME 🌑
        imp.plt.figure(figsize=(10, 6))

        # Plot each user's data
        for user_id, user_history in self.data.items():
            dates = []
            levels = []
            for date, level_list in sorted(user_history.items()):
                if not level_list:
                    continue
                dates.append(imp.datetime.strptime(date, "%Y-%m-%d"))  # Parse date to datetime object
                levels.append(level_list[-1])

            if dates and levels:
                
                guild = read_channel.guild
                try:
                    member = await guild.fetch_member(int(user_id))  # Always fetch from server
                    username = member.display_name
                except imp.discord.NotFound:
                    # If user not found in guild, fallback to global username
                    user = await self.fetch_user(int(user_id))
                    username = user.name if user else f"User {user_id}"

                username = utils.crop_username(username)
                print(username)
                imp.plt.plot(dates, levels, marker='o', label=username)


                # 🔥 Add level text above each point
                for (x, y) in zip(dates, levels):
                    imp.plt.annotate(
                        str(y),
                        (x, y),
                        textcoords="offset points",
                        xytext=(0, 8),
                        ha='center',
                        fontsize=8,
                        color='white'
                    )

        imp.plt.title("Levels", color='white')
        imp.plt.xlabel("Day", color='white')
        imp.plt.ylabel("Level", color='white')

        ax = imp.plt.gca()
        ax.xaxis.set_major_formatter(imp.mdates.DateFormatter('%d'))
        ax.xaxis.set_major_locator(imp.mdates.DayLocator())
        ax.yaxis.set_major_locator(imp.ticker.MaxNLocator(integer=True))

        imp.plt.legend(fontsize="small")
        imp.plt.grid(True, which='both', axis='x', linestyle='--', linewidth=0.5)
        imp.plt.tight_layout()


        await utils.reply_to_whoever_said_graph(read_channel, graph_request_message_id)

client = Client(intents=intents)
client.run(token)