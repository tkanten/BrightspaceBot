import subprocess
import os

os.chdir(os.path.dirname(__file__))
import discord
from discord.ext import commands, tasks
import json
import datetime
import time
import asyncio
from Models import *
from Database import *

db["crawl_script_location", "crawl_configs"] = os.path.join(os.path.dirname(__file__), 'crawler.py')
db["raw_crawl_file", "crawl_configs"] = os.path.join(os.path.dirname(__file__), 'rawcrawldump.json')

## Database crap ##
# TODO: Insert check here to ensure all mandatory values are entered (e.g if not db[important_dates])

if not db["BOT_TOKEN"]:
    db["BOT_TOKEN", "discord_configs"] = input("Enter your Discord bot token")
if not db["SERVER_ID"]:
    db["SERVER_ID", "discord_configs"] = int(input("Enter the ID of your Discord server"))
if not db["LOG_CHANNEL"]:
    db["LOG_CHANNEL", "discord_configs"] = int(input("Enter the ID of your Discord log channel"))
if not db["IMPORTANT_DATES_CHANNEL"]:
    db["IMPORTANT_DATES_CHANNEL", "discord_configs"] = int(input("Enter the channel ID of where dates will be posted"))

if not db["backup_frequency"]:
    db["backup_frequency", "database_configs"] = int(
        input("Enter the time (in seconds) that you want the database to backup"))

if not db["username"]:
    db["username", "crawl_configs"] = input("Enter your Brightspace username")
if not db["password"]:
    db["password", "crawl_configs"] = input("Enter your Brightspace password")
if not db["submit_button"]:
    db["submit_button", "crawl_configs"] = input("Enter the full Xpath for 'Submit' button")

if not db["class_id_dictionary"]:
    class_id_dict = dict({})
    class_id_list = list([])
    print("Enter ClassID|Classname - press enter with no input when complete")
    count = 1
    while True:
        inp = input(f"{count}>")
        if inp == "":
            break
        class_id, class_name = inp.split("|")
        class_id_list.append(int(class_id))
        class_id_dict.update({class_id: class_name})
        count += 1
    # add OTHER field
    class_id_list.append("000000")
    class_id_dict.update({"000000": "OTHER"})
    db["class_id_dictionary", "crawl_configs"] = class_id_dict
    db["class_id_list", "crawl_configs"] = class_id_list

print("Database loaded")
