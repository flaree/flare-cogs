import asyncio
import logging
import re
from datetime import datetime, timedelta
from html import unescape
from typing import Optional

import aiohttp
import asyncpraw
import asyncprawcore
import discord
import tabulate
import validators
from discord.http import Route
from redbot.core import Config, commands
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import box, humanize_timedelta, pagify, spoiler

log = logging.getLogger("red.flare.redditpost")

REDDIT_LOGO = "https://www.redditinc.com/assets/images/site/reddit-logo.png"
REDDIT_REGEX = re.compile(
    r"(?i)\A(((https?://)?(www\.)?reddit\.com/)?r/)?([A-Za-z0-9][A-Za-z0-9_]{2,20})/?\Z"
)


class RedditPost(commands.Cog):
    """A reddit auto posting cog."""

    __version__ = "0.4.1"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=959327661803438081, force_registration=True)
        self.config.register_channel(reddits={})
        self.config.register_global(delay=300, SCHEMA_VERSION=1)
        self.session = aiohttp.ClientSession()
        self.bg_loop_task: Optional[asyncio.Task] = None
        self.notified = False
        self.client = None
        self.bot.loop.create_task(self.init())

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not story any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not story any data
        pass

    async def init(self):
        await self.bot.wait_until_red_ready()
        if await self.config.SCHEMA_VERSION() == 1:
            data = await self.config.all_channels()
            for channel, _ in data.items():
                async with self.config.channel_from_id(channel).reddits() as sub_data:
                    for feed in sub_data:
                        try:
                            sub_data[feed]["subreddit"] = sub_data[feed]["url"].split("/")[4]
                        except IndexError:
                            sub_data[feed]["subreddit"] = None
            await self.bot.send_to_owners(
                "Hi there.\nRedditPost has now been given an update to accomodate the new reddit ratelimits. This cog now requires authenthication.\nTo setup the cog create an application via https://www.reddit.com/prefs/apps/. Once this is done, copy the client ID found under the name and the secret found inside.\nYou can then setup this cog by using `[p]set api redditpost clientid CLIENT_ID_HERE clientsecret CLIENT_SECRET_HERE`\n"
            )
            await self.config.SCHEMA_VERSION.set(2)

        token = await self.bot.get_shared_api_tokens("redditpost")
        try:
            self.client = asyncpraw.Reddit(
                client_id=token.get("clientid", None),
                client_secret=token.get("clientsecret", None),
                user_agent=f"{self.bot.user.name} Discord Bot",
            )

            self.bg_loop_task = self.bot.loop.create_task(self.bg_loop())
        except Exception as exc:
            log.error("Exception in init: ", exc_info=exc)
            await self.bot.send_to_owners(
                "An exception occured in the authenthication. Please ensure the client id and secret are set correctly.\nTo setup the cog create an application via https://www.reddit.com/prefs/apps/. Once this is done, copy the client ID found under the name and the secret found inside.\nYou can then setup this cog by using `[p]set api redditpost clientid CLIENT_ID_HERE clientsecret CLIENT_SECRET_HERE`"
            )

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()
        self.bot.loop.create_task(self.session.close())
        self.bot.loop.create_task(self.client.close())

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "redditpost":
            try:
                self.client = asyncpraw.Reddit(
                    client_id=api_tokens.get("clientid", None),
                    client_secret=api_tokens.get("clientsecret", None),
                    user_agent=f"{self.bot.user.name} Discord Bot",
                )
            except Exception as exc:
                log.error("Exception in init: ", exc_info=exc)
                await self.bot.send_to_owners(
                    "An exception occured in the authenthication. Please ensure the client id and secret are set correctly.\nTo setup the cog create an application via https://www.reddit.com/prefs/apps/. Once this is done, copy the client ID found under the name and the secret found inside.\nYou can then setup this cog by using `[p]set api redditpost clientid CLIENT_ID_HERE clientsecret CLIENT_SECRET_HERE`"
                )

    async def bg_loop(self):
        await self.bot.wait_until_ready()
        while True:
            try:
                await self.do_feeds()
                delay = await self.config.delay()
                await asyncio.sleep(delay)
            except Exception as exc:
                log.error("Exception in bg_loop: ", exc_info=exc)
                if not self.notified:
                    msg = "An exception occured in the background loop for `redditpost`. Check your logs for more details and if possible, report them to the cog creator.\nYou will no longer receive this message until you reload the cog to reduce spam."
                    await self.bot.send_to_owners(msg)
                    self.notified = True

    async def do_feeds(self):
        if self.client is None:
            return
        feeds = {}
        channel_data = await self.config.all_channels()
        for channel_id, data in channel_data.items():

            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue
            for sub, feed in data["reddits"].items():
                url = feed.get("subreddit", None)
                if not url:
                    continue
                if url in feeds:
                    response = feeds[url]
                else:
                    response = await self.fetch_feed(url)
                    feeds[url] = response
                if response is None:
                    continue
                time = await self.format_send(
                    response,
                    channel,
                    feed["last_post"],
                    url,
                    {
                        "latest": feed.get("latest", True),
                        "webhooks": feed.get("webhooks", False),
                        "logo": feed.get("logo", REDDIT_LOGO),
                        "button": feed.get("button", True),
                        "image_only": feed.get("image_only", False),
                    },
                )
                if time is not None:
                    async with self.config.channel(channel).reddits() as feeds_data:
                        feeds_data[sub]["last_post"] = time

    @staticmethod
    def _clean_subreddit(subreddit: str):
        subreddit = subreddit.lstrip("/")
        if match := REDDIT_REGEX.fullmatch(subreddit):
            return match.groups()[-1].lower()
        return None

    @commands.admin_or_permissions(manage_channels=True)
    @commands.guild_only()
    @commands.group(aliases=["redditfeed"])
    async def redditpost(self, ctx):
        """Reddit auto-feed posting."""

    @redditpost.command()
    @commands.is_owner()
    async def setup(self, ctx):
        """Details on setting up RedditPost"""
        msg = "To setup the cog create an application via https://www.reddit.com/prefs/apps/. Once this is done, copy the client ID found under the name and the secret found inside.\nYou can then setup this cog by using `[p]set api redditpost clientid CLIENT_ID_HERE clientsecret CLIENT_SECRET_HERE`"
        await ctx.send(msg)

    @redditpost.command()
    @commands.is_owner()
    async def delay(
        self,
        ctx,
        time: TimedeltaConverter(
            minimum=timedelta(seconds=15), maximum=timedelta(hours=3), default_unit="seconds"
        ),
    ):
        """Set the delay used to check for new content."""
        seconds = time.total_seconds()
        await self.config.delay.set(seconds)
        await ctx.tick()
        await ctx.send(
            f"The {humanize_timedelta(seconds=seconds)} delay will come into effect on the next loop."
        )

    @redditpost.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def add(self, ctx, subreddit: str, channel: Optional[discord.TextChannel] = None):
        """Add a subreddit to post new content from."""
        channel = channel or ctx.channel
        subreddit = self._clean_subreddit(subreddit)
        if not subreddit:
            return await ctx.send("That doesn't look like a subreddit name to me.")
        if self.client is None:
            await ctx.send(
                f"Please setup the client correctly, `{ctx.clean_prefix}redditpost setup` for more information"
            )
            return
        async with ctx.typing():
            try:
                subreddit_info = await self.client.subreddit(subreddit, fetch=True)
            except asyncprawcore.Forbidden:
                return await ctx.send("I can't view private subreddits.")
            except asyncprawcore.NotFound:
                return await ctx.send("This subreddit doesn't exist.")
            except Exception:
                return await ctx.send("Something went wrong while searching for this subreddit.")

        if subreddit_info.over18 and not channel.is_nsfw():
            return await ctx.send(
                "You're trying to add an NSFW subreddit to a SFW channel. Please edit the channel or try another."
            )
        logo = REDDIT_LOGO if not subreddit_info.icon_img else subreddit_info.icon_img

        async with self.config.channel(channel).reddits() as feeds:
            if subreddit in feeds:
                return await ctx.send("That subreddit is already set to post.")

            response = await self.fetch_feed(subreddit)

            if response is None:
                return await ctx.send("That didn't seem to be a valid reddit feed.")

            feeds[subreddit] = {
                "subreddit": subreddit,
                "last_post": datetime.now().timestamp(),
                "latest": True,
                "logo": logo,
                "webhooks": False,
            }
        await ctx.tick()

    @redditpost.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def list(self, ctx, channel: discord.TextChannel = None):
        """Lists the current subreddits for the current channel, or a provided one."""

        channel = channel or ctx.channel

        data = await self.config.channel(channel).reddits()
        if not data:
            return await ctx.send("No subreddits here.")
        output = [[k, v.get("webhooks", "False"), v.get("latest", True)] for k, v in data.items()]

        out = tabulate.tabulate(output, headers=["Subreddit", "Webhooks", "Latest Posts"])
        for page in pagify(str(out)):
            await ctx.send(
                embed=discord.Embed(
                    title=f"Subreddits for {channel}.",
                    description=box(page, lang="prolog"),
                    color=(await ctx.embed_color()),
                )
            )

    @redditpost.command(name="remove")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def remove_feed(
        self, ctx, subreddit: str, channel: Optional[discord.TextChannel] = None
    ):
        """Removes a subreddit from the current channel, or a provided one."""
        channel = channel or ctx.channel
        subreddit = self._clean_subreddit(subreddit)
        if not subreddit:
            return await ctx.send("That doesn't look like a subreddit name to me.")
        async with self.config.channel(channel).reddits() as feeds:
            if subreddit not in feeds:
                await ctx.send(f"No subreddit named {subreddit} in {channel.mention}.")
                return

            del feeds[subreddit]

        await ctx.tick()

    @redditpost.command(name="force")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def force(self, ctx, subreddit: str, channel: Optional[discord.TextChannel] = None):
        """Force the latest post."""
        channel = channel or ctx.channel
        subreddit = self._clean_subreddit(subreddit)
        if not subreddit:
            return await ctx.send("That doesn't look like a subreddit name to me.")
        feeds = await self.config.channel(channel).reddits()
        if subreddit not in feeds:
            await ctx.send(f"No subreddit named {subreddit} in {channel.mention}.")
            return
        if self.client is None:
            await ctx.send(
                f"Please setup the client correctly, `{ctx.clean_prefix}redditpost setup` for more information"
            )
            return
        data = await self.fetch_feed(feeds[subreddit]["subreddit"])
        if data is None:
            return await ctx.send("No post could be found.")
        await self.format_send(
            data,
            channel,
            0,
            subreddit,
            {
                "latest": True,
                "webhooks": feeds[subreddit].get("webhooks", False),
                "logo": feeds[subreddit].get("logo", REDDIT_LOGO),
                "button": feeds[subreddit].get("button", True),
                "image_only": False,
            },
        )
        await ctx.tick()

    @redditpost.command(name="latest")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def latest(self, ctx, subreddit: str, latest: bool, channel: discord.TextChannel = None):
        """Whether to fetch all posts or just the latest post."""
        channel = channel or ctx.channel
        subreddit = self._clean_subreddit(subreddit)
        if not subreddit:
            return await ctx.send("That doesn't look like a subreddit name to me.")
        async with self.config.channel(channel).reddits() as feeds:
            if subreddit not in feeds:
                await ctx.send(f"No subreddit named {subreddit} in {channel.mention}.")
                return

            feeds[subreddit]["latest"] = latest

        await ctx.tick()

    @redditpost.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def button(
        self, ctx, subreddit: str, use_button: bool, channel: discord.TextChannel = None
    ):
        """Whether to use buttons for the post URL."""
        channel = channel or ctx.channel
        subreddit = self._clean_subreddit(subreddit)
        if not subreddit:
            return await ctx.send("That doesn't look like a subreddit name to me.")
        async with self.config.channel(channel).reddits() as feeds:
            if subreddit not in feeds:
                await ctx.send(f"No subreddit named {subreddit} in {channel.mention}.")
                return

            feeds[subreddit]["button"] = use_button

        await ctx.tick()

    @redditpost.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def imageonly(
        self, ctx, subreddit: str, on_or_off: bool, channel: discord.TextChannel = None
    ):
        """Whether to only post posts that contain an image."""
        channel = channel or ctx.channel
        subreddit = self._clean_subreddit(subreddit)
        if not subreddit:
            return await ctx.send("That doesn't look like a subreddit name to me.")
        async with self.config.channel(channel).reddits() as feeds:
            if subreddit not in feeds:
                await ctx.send(f"No subreddit named {subreddit} in {channel.mention}.")
                return

            feeds[subreddit]["image_only"] = on_or_off

        await ctx.tick()

    @redditpost.command(
        name="webhook", aliases=["webhooks"], usage="<subreddit> <true_or_false> [channel]"
    )
    @commands.bot_has_permissions(send_messages=True, embed_links=True, manage_webhooks=True)
    async def webhook(
        self, ctx, subreddit: str, webhook: bool, channel: discord.TextChannel = None
    ):
        """Whether to send the post as a webhook or message from the bot."""
        channel = channel or ctx.channel
        subreddit = self._clean_subreddit(subreddit)
        if not subreddit:
            return await ctx.send("That doesn't look like a subreddit name to me.")
        async with self.config.channel(channel).reddits() as feeds:
            if subreddit not in feeds:
                await ctx.send(f"No subreddit named {subreddit} in {channel.mention}.")
                return

            feeds[subreddit]["webhooks"] = webhook

        if webhook:
            await ctx.send(f"New posts from r/{subreddit} will be sent as webhooks.")
        else:
            await ctx.send(f"New posts from r/{subreddit} will be sent as bot messages.")

        await ctx.tick()

    async def fetch_feed(self, subreddit: str):
        try:
            subreddit = await self.client.subreddit(subreddit)
            resp = [submission async for submission in subreddit.new(limit=20)]
            return resp or None
        except Exception:
            return None

    async def format_send(self, data, channel, last_post, subreddit, settings):
        timestamps = []
        embeds = []
        data = data[:1] if settings.get("latest", True) else data
        webhook = None
        try:
            if (
                settings.get("webhooks", False)
                and channel.permissions_for(channel.guild.me).manage_webhooks
            ):
                for hook in await channel.webhooks():
                    if hook.name == channel.guild.me.name:
                        webhook = hook
                if webhook is None:
                    webhook = await channel.create_webhook(name=channel.guild.me.name)
        except Exception as e:
            log.error("Error in webhooks during reddit feed posting", exc_info=e)
        for feed in data:
            timestamp = feed.created_utc
            if feed.over_18 and not channel.is_nsfw():
                timestamps.append(timestamp)
                continue
            if timestamp <= last_post:
                break
            timestamps.append(timestamp)
            desc = unescape(feed.selftext)
            image = feed.url
            link = f"https://reddit.com{feed.permalink}"
            title = feed.title
            if len(desc) > 2000:
                desc = f"{desc[:2000]}..."
            if len(title) > 252:
                title = f"{title[:252]}..."
            if feed.spoiler:
                desc = "(spoiler)\n" + spoiler(desc)
            embed = discord.Embed(
                title=unescape(title),
                url=unescape(link),
                description=desc,
                color=channel.guild.me.color,
                timestamp=datetime.utcfromtimestamp(feed.created_utc),
            )
            embed.set_author(name=f"New post on r/{unescape(subreddit)}")
            if feed.author:
                embed.set_footer(text=f"Submitted by /u/{unescape(feed.author.name)}")
            images = False
            if image.endswith(("png", "jpg", "jpeg", "gif")) and not feed.spoiler:
                embed.set_image(url=unescape(image))
                images = True
            elif feed.permalink not in image and validators.url(image):
                embed.add_field(name="Attachment", value=unescape(image))
            if settings.get("image_only") and not images:
                continue
            embeds.append(embed)
        if timestamps:
            if embeds:
                try:
                    for emb in embeds[::-1]:
                        if webhook is None:
                            try:
                                if settings.get("button", True):
                                    payload = {"content": "", "embed": emb.to_dict()}
                                    payload["components"] = [
                                        {
                                            "type": 1,
                                            "components": [
                                                {
                                                    "label": "Source",
                                                    "url": emb.url,
                                                    "style": 5,
                                                    "type": 2,
                                                }
                                            ],
                                        }
                                    ]
                                    r = Route(
                                        "POST",
                                        "/channels/{channel_id}/messages",
                                        channel_id=channel.id,
                                    )
                                    await self.bot._connection.http.request(r, json=payload)
                                else:
                                    await channel.send(embed=emb)
                            except (discord.Forbidden, discord.HTTPException):
                                log.info(f"Error sending message feed in {channel}. Bypassing")
                        else:
                            await webhook.send(
                                username=f"r/{feed.subreddit}",
                                avatar_url=settings.get("icon", REDDIT_LOGO),
                                embed=emb,
                            )
                except discord.HTTPException as exc:
                    log.error("Exception in bg_loop while sending message: ", exc_info=exc)
            return timestamps[0]
        return None
