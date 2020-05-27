import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
import discord
import validators
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.commands.converter import TimedeltaConverter

log = logging.getLogger("red.flare.redditpost")


class RedditPost(commands.Cog):
    """A reddit auto posting cog."""

    __version__ = "0.0.2"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=959327661803438081, force_registration=True)
        self.config.register_channel(reddits={})
        self.config.register_global(delay=300)
        self.session = aiohttp.ClientSession()
        self.bg_loop_task: Optional[asyncio.Task] = None

    def init(self):
        self.bg_loop_task = self.bot.loop.create_task(self.bg_loop())

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()
        self.bot.loop.create_task(self.session.close())

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
                time = await self.format_send(response, channel, feed["last_post"])
                if time is not None:
                    data = {"url": url, "last_post": time}
                    async with self.config.channel(channel).reddits() as feeds:
                        feeds[sub] = data

    @commands.admin()
    @commands.group()
    async def redditfeed(self, ctx):
        """Reddit auto-feed posting."""

    @redditfeed.command()
    @commands.is_owner()
    async def delay(
        self,
        ctx,
        seconds: TimedeltaConverter(
            minimum=timedelta(), maximum=timedelta(seconds=900), default_unit="seconds"
        ),
    ):
        """Set the delay used to check for new content."""
        time = seconds.total_seconds()
        await self.config.delay.set(time)
        await ctx.tick()
        await ctx.send("This delay will come into effect on the next loop.")

    @redditfeed.command()
    async def add(self, ctx, subreddit: str, channel: Optional[discord.TextChannel] = None):
        """Add a subreddit to post new content from.

        Feed must not include the /r/
        """
        channel = channel or ctx.channel
        async with self.session.get(
            f"https://www.reddit.com/r/{subreddit}/about.json?sort=new"
        ) as resp:
            data = await resp.json()
            if data["data"]["over18"] and not channel.is_nsfw():
                return await ctx.send(
                    "You're trying to add an NSFW subreddit to a SFW channel. Please edit the channel or try another."
                )

        async with self.config.channel(channel).reddits() as feeds:
            if subreddit in feeds:
                return await ctx.send("That subreddit is already set to post.")

            url = f"https://www.reddit.com/r/{subreddit}/new.json?sort=new"

            response = await self.fetch_feed(url)

            if response is None:
                return await ctx.send(f"That didn't seem to be a valid rss feed.")

            feeds[subreddit] = {"url": url, "last_post": datetime.now().timestamp()}
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

    async def fetch_feed(self, url: str):
        timeout = aiohttp.client.ClientTimeout(total=15)
        try:
            async with self.session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                else:
                    return None
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None
        except Exception as exc:
            log.info(
                f"Unexpected exception type {type(exc)} encountered for feed url: {url}",
                exc_info=exc,
            )
            return None
        if data["data"]["dist"] > 0:
            return data["data"]["children"]
        return None

    async def format_send(self, data, channel, last_post):
        timestamps = []
        embeds = []
        for feed in data:
            feed = feed["data"]
            timestamp = feed["created_utc"]
            if feed["over_18"] and not channel.is_nsfw():
                timestamps.append(timestamp)
                continue
            if timestamp <= last_post:
                break
            timestamps.append(timestamp)

            desc = feed["selftext"]

            image = feed["url"]

            link = "https://reddit.com" + feed["permalink"]

            title = f"[{feed['title']}]({link})\n\n" + " ".join(desc.split()[:-5])

            if len(title) > 2000:
                title = title[:2000] + "..."
            embed = discord.Embed(
                title=f"New post on r/{feed['subreddit']}",
                description=title,
                color=channel.guild.me.color,
            )
            embed.set_footer(text=f"Submitted by /u/{feed['author']}")
            if image[-3:] in ["png", "jpg"]:
                embed.set_image(url=image)
            else:
                if feed["permalink"] not in image:
                    if validators.url(image):
                        embed.add_field(name="Attachment", value=image)
            embeds.append(embed)
        if timestamps:
            if embeds:
                for emb in embeds[::-1]:
                    await channel.send(embed=emb)

            return timestamps[0]
        return None
