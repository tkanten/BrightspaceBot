import asyncio
import subprocess
from settings import *
import time
import datetime


def setup(bot):
    bot.add_cog(CrawlControl(bot))


class CrawlControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.BotLog = LogEmbeds(bot, db["LOG_CHANNEL"], discord.Colour.gold())

        self.channel = db["IMPORTANT_DATES_CHANNEL"]

        if not self.message_update_loop.is_running():
            self.message_update_loop.start()

        # fire up the crawl script, runs in the background by itself
        subprocess.Popen(
            f'python3 {db["crawl_script_location"]} {db["raw_crawl_file"]}', shell=True)

    def cog_unload(self):
        if self.message_update_loop.is_running():
            self.message_update_loop.cancel()

    @commands.command()
    @commands.is_owner()
    async def add_date(self, ctx, *content):
        """<CLASS NAME> <MM/DD/YY-mm:hh-AM/PM> <NAME>"""

        # start by converting class name string to upper
        # then iterate through class ID dictionary to try and find the class ID
        class_name = content[0].upper()
        class_id = None
        for key, val in db["class_id_dictionary"].items():
            if val == class_name:
                class_id = key
                break

        if not class_id:
            raise Exception(f"couldn't find a class ID for {class_name}")

        due_date = datetime.datetime.strptime(
            content[1], "%m/%d/%y-%I:%M-%p").timestamp()

        item_name = " ".join(content[2:])
        current_dict = db[f"{class_id}_custom"]
        ## beware messy programming below! ##
        # check current dictionary is an observeddict
        # if it is, update dict and push
        # if it isn't, create dict and push

        if isinstance(current_dict, controller.ObservedDict):
            current_dict.update(
                {item_name: {"Name": item_name, "Ends": due_date}})
        else:
            current_dict = {item_name: {"Name": item_name, "Ends": due_date}}
        db[f"{class_id}_custom", "crawl_data"] = current_dict

        # delete after all operations completed, easy signifier that there was a parsing issue
        await ctx.message.delete()
        # quickly push the newly updated table
        await self.msg_updater()

    @commands.command()
    @commands.is_owner()
    async def rm_date(self, ctx, *content):
        """<CLASS NAME> <TOPIC NAME - MUST MATCH EXACTLY>"""
        class_name = content[0].upper()
        class_id = None
        for key, val in db["class_id_dictionary"].items():
            if val == class_name:
                class_id = key
                break
        if not class_id:
            raise Exception(f"couldn't find a class ID for {class_name}")

        topic_name = " ".join(content[1:])

        if db[f"{class_id}_custom"][topic_name]:
            current_content = db[f"{class_id}_custom"]
            current_content.pop(topic_name)
            db[f"{class_id}_custom"] = current_content
        else:
            raise Exception(f"couldn't find a custom listing for {topic_name}")
        await ctx.message.delete()

        await self.msg_updater()

    @commands.command()
    @commands.is_owner()
    async def force_u(self, ctx):
        """Forces output message to be updated"""
        await ctx.message.delete()

        await self.msg_updater()

    @tasks.loop(seconds=30)
    async def message_update_loop(self):
        while not self.bot.is_ready():
            await asyncio.sleep(1)

        # if the temporary json crawl file exists, update values
        if not os.path.isfile(db["raw_crawl_file"]):
            return
        with open(db["raw_crawl_file"], "r") as entry:
            raw_data = json.load(entry)

        for key, val in raw_data.items():
            db[key, "crawl_data"] = val
        os.remove(db["raw_crawl_file"])

        await self.msg_updater()

    async def msg_updater(self):
        # if the bot is not ready, return and try again next time
        if not self.bot.is_ready():
            return
        # start by ensuring the channel and message objects are discovered
        if isinstance(self.channel, int):
            self.channel = self.bot.get_channel(self.channel)

        for class_id in db["class_id_list"]:
            final_output = []
            # name mapping for class ID
            class_name = f"__{db['class_id_dictionary'][f'{class_id}']}__"
            final_output.append(class_name)

            ## getting test list ##
            raw_test_list = db[f"{class_id}_tests"]

            if raw_test_list:
                formatted_test_list = await self.create_test_list(raw_test_list)
                for test in formatted_test_list:
                    final_output.append(test)

            ## getting assignment list ##
            raw_assignment_list = db[f"{class_id}_assignments"]
            if raw_assignment_list:
                formatted_assignment_list = await self.create_assignment_list(raw_assignment_list)
                for assignment in formatted_assignment_list:
                    final_output.append(assignment)

            ## getting custom list ##
            raw_custom_list = db[f"{class_id}_custom"]
            if raw_custom_list:
                formatted_custom_list = await self.create_custom_list(raw_custom_list)
                for custom in formatted_custom_list:
                    final_output.append(custom)

            final_output.append(" ")
            final_output = "\n".join(final_output)

            # now check database to see if there is a saved message ID
            # if there isn't, send a new message to important dates channel
            if not db[f"{class_id}_MESSAGE"]:
                message = await self.channel.send(final_output)
                db[f"{class_id}_MESSAGE", "discord_configs"] = message.id
            # if there is, edit existing message content
            else:
                message = await self.channel.fetch_message(db[f"{class_id}_MESSAGE"])
                await message.edit(content=final_output)

        # now create or edit the update time stamp
        update_time_stamp = f"\n_Last checked {datetime.datetime.now().strftime('%b %d, %I:%M %p MST')}_"
        if not db[f"LAST_UPDATE_MESSAGE"]:
            message = await self.channel.send(update_time_stamp)
            db["LAST_UPDATE_MESSAGE", "discord_configs"] = message.id
        else:
            message = await self.channel.fetch_message(db["LAST_UPDATE_MESSAGE"])
            await message.edit(content=update_time_stamp)

    @staticmethod
    async def create_test_list(raw_test_input):
        current_time = time.time()

        formatted_test_list = []
        for val in raw_test_input.values():
            # if end time already reached, skip to the next
            if current_time > val["Ends"]:
                continue
            test_name = val["Name"]
            test_end = datetime.datetime.fromtimestamp(val["Ends"])
            test_attempts = val["Attempts"]

            # "%b %d, %I:%M %p MST"
            formatted_line = f"**{test_name} -** _Due {test_end.strftime('%b %d, %I:%M %p MST')}_ ({test_attempts} attempt(s))"
            formatted_test_list.append(formatted_line)
        return formatted_test_list

    @staticmethod
    async def create_assignment_list(raw_assignment_input):
        current_time = time.time()
        formatted_ass_list = []

        for val in raw_assignment_input.values():
            # if assignment is closed, skip to the next
            if val["Closed"]:
                continue
            # potential elif assignment is group mark, we'll see
            ass_name = val["Name"]
            if val["Due"]:
                # if current time is past duedate, skip to next
                if current_time > val["Due"]:
                    continue
                ass_due = datetime.datetime.fromtimestamp(val["Due"])
                ass_due = ass_due.strftime('%b %d, %I:%M %p MST')
            else:
                continue

            # "%b %d, %I:%M %p MST"
            formatted_line = f"**{ass_name} -** _Due {ass_due}_"
            formatted_ass_list.append(formatted_line)
        return formatted_ass_list

    @staticmethod
    async def create_custom_list(raw_custom_input):
        current_time = time.time()

        formatted_cust_list = []
        for val in raw_custom_input.values():
            # if end time already reached, skip to the next
            if current_time > val["Ends"]:
                continue

            cust_name = val["Name"]

            cust_date = datetime.datetime.fromtimestamp(val["Ends"])

            formatted_line = f"**{cust_name} -** _Ends on {cust_date.strftime('%b %d, %I:%M %p MST')}_"
            formatted_cust_list.append(formatted_line)
        return formatted_cust_list
