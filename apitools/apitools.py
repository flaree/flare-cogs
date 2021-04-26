import json

import aiohttp
import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import box


class ApiTools(commands.Cog):
    """API tool to get/post data."""

    __version__ = "0.0.2"
    __author__ = "flare"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def req(self, get_or_post, url, headers={}):
        reqmethod = self.session.get if get_or_post == "get" else self.session.post
        async with reqmethod(url, headers=headers) as req:
            data = await req.text()
            status = req.status
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            parsed = data
        return parsed, status

    @commands.group()
    @commands.is_owner()
    async def apitools(self, ctx):
        """Group for API tools."""

    @apitools.command(name="get")
    async def _get(self, ctx, url, *, headers=None):
        """Send a HTTP Get request."""
        if headers is not None:
            try:
                headers = json.loads(headers)
            except json.JSONDecodeError:
                return await ctx.send(
                    "The headers you provided are invalid. Please provide them in JSON/Dictionary format."
                )
        else:
            headers = {}
        try:
            data, status = await self.req("get", url, headers=headers)
        except Exception:
            return await ctx.send(
                "An error occured while trying to post your request. Ensure the URL is correct etcetra."
            )
        color = discord.Color.green() if status == 200 else discord.Color.red()
        msg = json.dumps(data, indent=4, sort_keys=True)[:2030]
        if len(msg) > 2029:
            msg += "\n..."
        embed = discord.Embed(
            title=f"Results for **GET** {url}",
            color=color,
            description=box(msg, lang="json"),
        )
        embed.add_field(name="Status Code", value=status)
        await ctx.send(embed=embed)

    @apitools.command()
    async def post(self, ctx, url, *, headers=None):
        """Send a HTTP POST request."""
        if headers is not None:
            try:
                headers = json.loads(headers)
            except json.JSONDecodeError:
                return await ctx.send(
                    "The headers you provided are invalid. Please provide them in JSON/Dictionary format."
                )
        else:
            headers = {}
        try:
            data, status = await self.req("post", url, headers=headers)
        except Exception:
            return await ctx.send(
                "An error occured while trying to post your request. Ensure the URL is correct etcetra."
            )
        color = discord.Color.green() if status == 200 else discord.Color.red()
        msg = json.dumps(data, indent=4)[:2030]
        if len(msg) > 2029:
            msg += "\n..."
        embed = discord.Embed(
            title=f"Results for **POST** {url}",
            color=color,
            description=box(msg, lang="json"),
        )
        embed.add_field(name="Status Code", value=status)
        await ctx.send(embed=embed)
