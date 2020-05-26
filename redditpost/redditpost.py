import asyncio
import logging
from datetime import datetime
from typing import Optional

import aiohttp
import discord
import feedparser
import validators
from bs4 import BeautifulSoup
from redbot.core import commands
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify

from .htmlparse import html_to_text

log = logging.getLogger("red.flare.redditpost")


class RedditPost(commands.Cog):
    """A reddit auto posting cog.

    Thanks to mikeshardmind(Sinbad) for the RSS cog as reference
    """

    __version__ = "0.0.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_channel(reddits={})
        self.config.register_global(interval=300)
        self.session = aiohttp.ClientSession()
        self.bg_loop_task: Optional[asyncio.Task] = None

    def init(self):
        self.bg_loop_task = asyncio.create_task(self.bg_loop())

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()
        asyncio.create_task(self.session.close())

    async def bg_loop(self):
        await self.bot.wait_until_ready()
        while True:
            await self.do_feeds()
            delay = await self.config.delay()
            await asyncio.sleep(delay)

    async def do_feeds(self):
        feeds = {}
        channel_data = await self.config.all_channels()
        for channel_id, data in channel_data.items():

            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue
            for sub, feed in data["reddits"].items():
                url = feed.get("url", None)
                if not url:
                    continue
                if url in feeds:
                    response = feeds[url]
                else:
                    response = await self.fetch_feed(url)
                    feeds[url] = response
                time = await self.format_send(response, channel, feed["last_post"], sub)
                if time is not None:
                    data = {"url": url, "last_post": time}
                    async with self.config.channel(channel).reddits() as feeds:
                        feeds[sub] = data

    @commands.admin()
    @commands.group()
    async def redditfeed(self, ctx):
        """Reddit auto-feed posting."""

    @redditfeed.command()
    async def add(self, ctx, subreddit: str, channel: Optional[discord.TextChannel] = None):
        """Add a subreddit to post new content from.

        Feed must not include the /r/
        """
        channel = channel or ctx.channel

        async with self.config.channel(channel).reddits() as feeds:
            if subreddit in feeds:
                return await ctx.send("That subreddit is already set to post.")

            url = f"https://www.reddit.com/r/{subreddit}/new/.rss"

            response = await self.fetch_feed(url)

            if response is None:
                return await ctx.send(f"That didn't seem to be a valid rss feed.")

            feeds[subreddit] = {
                "url": url,
                "last_post": datetime.fromisoformat("1970-01-01T00:00:00+00:00").timestamp(),
            }
            await ctx.tick()

    @redditfeed.command()
    async def list(self, ctx, channel: discord.TextChannel = None):
        """Lists the current subreddits for the current channel, or a provided one."""

        channel = channel or ctx.channel

        data = await self.config.channel(channel).reddits()
        if not data:
            return await ctx.send("No subreddits here.")
        output = "\n".join(
            (
                "{name}: {url}".format(name=k, url=v.get("url", "broken feed"))
                for k, v in data.items()
            )
        )
        for page in pagify(output):
            await ctx.send(embed=discord.Embed(description=page, color=(await ctx.embed_color())))

    @redditfeed.command(name="remove")
    async def remove_feed(
        self, ctx, subreddit: str, channel: Optional[discord.TextChannel] = None
    ):
        """Removes a subreddit from the current channel, or a provided one."""
        channel = channel or ctx.channel
        async with self.config.channel(channel).reddits() as feeds:
            if subreddit not in feeds:
                await ctx.send(f"No subreddit named {subreddit} in {channel.mention}.")
                return

            del feeds[subreddit]

        await ctx.tick()

    async def fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        timeout = aiohttp.client.ClientTimeout(total=15)
        try:
            async with self.session.get(url, timeout=timeout) as response:
                data = await response.read()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None
        except Exception as exc:
            log.info(
                f"Unexpected exception type {type(exc)} encountered for feed url: {url}",
                exc_info=exc,
            )
            return None

        ret = feedparser.parse(data)
        if ret.bozo:
            log.debug(f"Feed url: {url} is invalid.")
            return None
        return ret

    async def format_send(self, feed, channel, lastimg, sub):
        if not feed.entries:
            return
        timestamp = datetime.fromisoformat(feed.entries[0].updated).timestamp()
        if timestamp <= lastimg:
            return None
        soup = BeautifulSoup(feed.entries[0].content[0].value, features="html5lib")
        desc = html_to_text(feed.entries[0].description)
        images = soup.find("span")
        image = images.find("a")["href"]
        title = f"[{feed.entries[0].title}]({feed.entries[0].link})\n\n" + " ".join(
            desc.split()[:-5]
        )
        if len(title) > 2000:
            title = title[:2000] + "..."
        embed = discord.Embed(
            title=f"New post on r/{sub}", description=title, color=await ctx.embed_color()
        )
        embed.set_footer(text=" ".join(desc.split()[-5:-2]))
        if image[-3:] in ["png", "jpg"]:
            embed.set_image(url=image)
        else:
            if image != feed.entries[0].link:
                if validators.url(image):
                    embed.add_field(name="Attachment", value=image)
        await channel.send(embed=embed)
        return timestamp
