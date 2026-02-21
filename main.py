import os
from discord_bot  import run_bot
from logics import tokens

def load_env(file_path):
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

load_env(".env")

token = os.getenv("DiscordToken")
rgbToken = os.getenv("RGBPass")
oldToken = os.getenv("OldPass")


#startup
tokens(rgbToken, oldToken) #send the tokens to the logics.py file
run_bot(token) #send the tokens to the bot
