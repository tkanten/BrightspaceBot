from discord.ext import commands, tasks
import discord
"""Supplies coroutine models for sending embeded messages to the log channels"""

class LogEmbeds:
    def __init__(self, bot, channel, log_colour=discord.Colour.dark_theme()):
        # channel pass in should be a channel object (obtained through bot.fetch_channel)
        self.bot = bot
        self.channel = channel
        self.log_colour = log_colour


    async def log_event(self,event_title,event_description,author=False,field_args=False):
        # field_args layout: [0] name, [1] value, [2] inline
        
        ### NOTE: this method for fetching channels may prove to be inefficient in the long run ###
        channel = await self.bot.fetch_channel(self.channel)
        
        embed = discord.Embed(colour=self.log_colour,title=event_title,description=event_description)
        if author:
            embed.set_author(name=author.name,icon_url=author.avatar_url)
            embed.set_thumbnail(url=author.avatar_url)

        if field_args:
            # if there are multiple fields to enter
            if type(field_args[0]) == list:
                for item in field_args:
                    embed.add_field(name=item[0],value=item[1],inline=item[2])
            else:
                embed.add_field(name=field_args[0],value=field_args[1],inline=field_args[2])

        await channel.send(embed=embed)

    async def preset_log_event(self, embed):
        channel = await self.bot.fetch_channel(self.channel)
        await channel.send(embed=embed)