from redbot.core import commands
import discord
import aiohttp
import asyncio
import random
import json
import datetime


class Weather(commands.Cog):
    """Weather Related Commands"""

    __version__ = "0.1.0"

    def __init__(self, bot):
        self.bot = bot
        self._session = aiohttp.ClientSession(loop=self.bot.loop)

    def cog_unload(self):
        self.bot.loop.create_task(self._session.detach())

    async def get(self, api, location):
        async with self._session.get(
            "https://api.apixu.com/v1/current.json?key={}&q={}".format(api, location)
        ) as response:
            if response.status == 200:
                return await response.json(content_type=None)
            else:
                return None

    async def build(self, data):
        area = "{}, {} {}.".format(
            data["location"]["name"],
            data["location"]["region"] + "," if data["location"]["region"] != "" else "",
            data["location"]["country"],
        )
        time = datetime.datetime.strptime(data["current"]["last_updated"], "%Y-%m-%d %H:%M")
        embed = discord.Embed(
            title="Pikachu Weather",
            description="Weather in {}".format(area),
            timestamp=time,
            colour=discord.Colour.blue(),
        )
        embed.add_field(
            name="Temperature",
            value=f"{data['current']['temp_c']}°C/{data['current']['temp_f']}°F",
        )
        embed.add_field(
            name="Feels like Temperature",
            value=f"{data['current']['feelslike_c']}°C/{data['current']['feelslike_f']}°F",
        )
        embed.add_field(name="Conditions", value=f"{data['current']['condition']['text']}")
        embed.add_field(
            name="Wind Speds",
            value=f"{data['current']['gust_mph']} Mph/{data['current']['gust_kph']} Kph",
        )
        embed.add_field(
            name="Rain Fall",
            value=f"{data['current']['precip_mm']} mm/{data['current']['precip_in']} in",
        )
        embed.add_field(name="Humidity", value=f"{data['current']['humidity']}%")
        currtime = datetime.datetime.strptime(data["location"]["localtime"], "%Y-%m-%d %H:%M")
        embed.add_field(name="Current Time", value=currtime.strftime("%H:%M"))
        return embed

    @commands.command()
    async def weather(self, ctx, *, location: str):
        """Weather Server Lookup"""
        api = await self.bot.db.api_tokens.get_raw("weather", default={"api_key": None})
        if api["api_key"] is None:
            return await ctx.send("API is not set..")
        data = await self.get(api["api_key"], location)
        if data is None:
            return await ctx.send("No data")
        embed = await self.build(data)
        await ctx.send(embed=embed)
