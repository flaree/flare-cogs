import typing
from io import BytesIO

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.utils.predicates import MessagePredicate


async def tokencheck(ctx):
    token = await ctx.bot.get_shared_api_tokens("imgen")
    return bool(token.get("authorization"))


class DankMemer(commands.Cog):

    __version__ = "0.0.3"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_global(url="https://imgen.flaree.xyz/api")
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        self.headers = {}

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def initalize(self):
        self.api = await self.config.url()
        token = await self.bot.get_shared_api_tokens("imgen")
        self.headers = {"Authorization": token.get("authorization")}

    @commands.command()
    async def dankmemersetup(self, ctx):
        """Instructions on how to setup DankMemer"""
        msg = (
            "This DankMemer cog relies on flare#0001s self hosted version of DankMemers imgen site.\n"
            "Gaining an API key will be difficult as they won't be handed out to everyone.\n"
            "If you're lucky enough to get an API key then enter it using the following commands:\n"
            f"{ctx.clean_prefix}set api imgen authorization <key>"
        )
        await ctx.maybe_send_embed(msg)

    @commands.is_owner()
    @commands.command()
    async def dmurl(self, ctx, *, url: str):
        """Set the DankMemer API Url
        
        Only use this if you have an instance already."""
        await ctx.send(
            "This has the ability to make every command error if not setup properly. Only use this if you're experienced enough to understand. Type yes to continue, otherwise type no."
        )
        try:
            pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
            await ctx.bot.wait_for("message", check=pred, timeout=20)
        except asyncio.TimeoutError:
            await ctx.send("Exiting operation.")
            return

        if pred.result:
            await self.config.url.set(url)
            await ctx.tick()
            await self.initalize()
        else:
            await ctx.send("Operation cancelled.")

    @commands.Cog.listener()
    async def on_red_api_tokens_update(self, service_name, api_tokens):
        if service_name == "imgen":
            self.headers = {"Authorization": api_tokens.get("authorization")}

    async def send_error(self, ctx, data):
        await ctx.send(f"Oops, an error occured. `{data['error']}`")

    async def get(self, ctx, url):
        async with ctx.typing():
            async with self.session.get(self.api + url, headers=self.headers) as resp:
                if resp.status == 200:
                    file = await resp.read()
                    file = BytesIO(file)
                    file.seek(0)
                    return file
                try:
                    return await resp.json()
                except aiohttp.ContentTypeError:
                    return {"error": "Server may be down, better errors soon ok i promise."}

    @commands.check(tokencheck)
    @commands.command()
    async def abandon(self, ctx, *, text: str):
        """Abandoning your son?"""
        data = await self.get(ctx, f"/abandon?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "abandon.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command(aliases=["aborted"])
    async def abort(self, ctx, user: discord.Member = None):
        """All the reasons why X was aborted."""
        user = user or ctx.author
        data = await self.get(ctx, f"/aborted?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "abort.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def affect(self, ctx, user: discord.Member = None):
        """It won't affect my baby."""
        user = user or ctx.author
        data = await self.get(ctx, f"/affect?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "affect.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def airpods(self, ctx, user: discord.Member = None):
        """Flex with airpods."""
        user = user or ctx.author
        data = await self.get(ctx, f"/airpods?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "airpods.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def america(self, ctx, user: discord.Member = None):
        """Americafy a picture."""
        user = user or ctx.author
        data = await self.get(ctx, f"/america?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "america.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def armor(self, ctx, *, text: str):
        """Nothing gets through this armour."""
        data = await self.get(ctx, f"/armor?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "armor.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def balloon(self, ctx, *, text: str):
        """Pop a balloon.
        
        
        Texts must be comma seperated."""
        data = await self.get(ctx, f"/balloon?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "balloon.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def bed(self, ctx, user: discord.Member, user2: discord.Member = None):
        """There's a monster under my bed."""
        user2 = user2 or ctx.author
        data = await self.get(
            ctx,
            "/bed?avatar1={}{}".format(
                user.avatar_url_as(static_format="png"),
                f"&avatar2={user2.avatar_url_as(static_format='png')}"
                if user2 is not None
                else "",
            ),
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "bed.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def bongocat(self, ctx, user: discord.Member = None):
        """Bongocat-ify your avatar."""
        user = user or ctx.author
        data = await self.get(ctx, f"/bongocat?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "bongocat.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def boo(self, ctx, *, text: str):
        """Scary.
        
        
        
        Texts must be comma seperated."""
        data = await self.get(ctx, f"/boo?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "boo.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def brain(self, ctx, *, text: str):
        """Big brain meme.
        
        Texts must be 4 comma seperated items."""
        data = await self.get(ctx, f"/brain?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "brain.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def brazzers(self, ctx, user: discord.Member = None):
        """Brazzerfy your avatar."""
        user = user or ctx.author
        data = await self.get(ctx, f"/brazzers?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "brazzers.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def byemom(self, ctx, user: typing.Optional[discord.Member] = None, *, text: str):
        """Bye mom."""
        user = user or ctx.author

        data = await self.get(
            ctx,
            f"/byemom?avatar1={user.avatar_url_as(static_format='png')}&username1={user.name}&text={text}",
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "byemom.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()  # TODO: Maybe remove?
    async def cancer(self, ctx, user: discord.Member = None):
        """Maybe remove."""
        user = user or ctx.author
        data = await self.get(ctx, f"/cancer?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "cancer.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def changemymind(self, ctx, *, text: str):
        """Change my mind?"""
        data = await self.get(ctx, f"/changemymind?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "changemymind.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def cheating(self, ctx, *, text: str):
        """Cheating?.
        
        Text must be comma seperated."""
        data = await self.get(ctx, f"/cheating?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "cheating.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def citation(self, ctx, *, text: str):
        """Papers Please Citation.
        
        Text must be 3 comma seperated values."""
        data = await self.get(ctx, f"/citation?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "citation.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()  # TODO: Maybe remove?
    async def communism(self, ctx, user: discord.Member = None):
        """Communism-ify your picture."""
        user = user or ctx.author
        data = await self.get(ctx, f"/communism?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "communism.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def confusedcat(self, ctx, *, text: str):
        """Confused cat meme.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/confusedcat?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "confusedcat.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def corporate(self, ctx, user: discord.Member = None):
        """Corporate meme."""
        user = user or ctx.author
        data = await self.get(ctx, f"/corporate?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "corporate.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def cry(self, ctx, *, text: str):
        """Drink my tears meme.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/cry?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "cry.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def dab(self, ctx, user: discord.Member = None):
        """Hit a dab."""
        user = user or ctx.author
        data = await self.get(ctx, f"/dab?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "dab.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def dank(self, ctx, user: discord.Member = None):
        """Dank, noscope 420."""
        user = user or ctx.author
        data = await self.get(ctx, f"/dank?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "dank.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def deepfried(self, ctx, user: discord.Member = None):
        """Deepfry an image."""
        user = user or ctx.author
        data = await self.get(ctx, f"/deepfry?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "deepfry.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def delete(self, ctx, user: discord.Member = None):
        """Delete Meme."""
        user = user or ctx.author
        data = await self.get(ctx, f"/delete?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "delete.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def disability(self, ctx, user: discord.Member = None):
        """Disability Meme."""
        user = user or ctx.author
        data = await self.get(
            ctx, f"/disability?avatar1={user.avatar_url_as(static_format='png')}"
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "disability.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def doglemon(self, ctx, *, text: str):
        """Dog and Lemon Meme.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/doglemon?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "doglemon.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def door(self, ctx, user: discord.Member = None):
        """Kick down the door meme."""
        user = user or ctx.author
        data = await self.get(ctx, f"/door?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "door.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def egg(self, ctx, user: discord.Member = None):
        """Turn your picture into an egg."""
        user = user or ctx.author
        data = await self.get(ctx, f"/egg?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "egg.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def excuseme(self, ctx, *, text: str):
        """Excuse me, what the...
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/excuseme?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "excuseme.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def expanddong(self, ctx, *, text: str):
        """Expanding?
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/expanddong?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "expanddong.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def facts(self, ctx, *, text: str):
        """Facts book.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/facts?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "facts.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def failure(self, ctx, user: discord.Member = None):
        """You're a failure meme."""
        user = user or ctx.author
        data = await self.get(ctx, f"/failure?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "failure.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def fakenews(self, ctx, user: discord.Member = None):
        """Fake News."""
        user = user or ctx.author
        data = await self.get(ctx, f"/fakenews?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "fakenews.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def fedora(self, ctx, user: discord.Member = None):
        """*Tips Fedora*."""
        user = user or ctx.author
        data = await self.get(ctx, f"/fedora?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "fedora.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def floor(self, ctx, user: typing.Optional[discord.Member] = None, *, text: str):
        """The floor is ...."""
        user = user or ctx.author
        data = await self.get(
            ctx, f"/floor?avatar1={user.avatar_url_as(static_format='png')}&text={text}"
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "fedora.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def fuck(self, ctx, *, text: str):
        """Feck.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/fuck?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "fuck.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def garfield(self, ctx, user: typing.Optional[discord.Member] = None, *, text: str):
        """I wonder who that's for - Garfield meme."""
        user = user or ctx.author
        data = await self.get(
            ctx, f"/garfield?avatar1={user.avatar_url_as(static_format='png')}&text={text}"
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "garfield.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def gay(self, ctx, user: discord.Member = None):
        """Rainbow-fy your avatar."""
        user = user or ctx.author
        data = await self.get(ctx, f"/gay?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "gay.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def goggles(self, ctx, user: discord.Member = None):
        """Remember, safety goggles on."""
        user = user or ctx.author
        data = await self.get(ctx, f"/goggles?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "goggles.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def hitler(self, ctx, user: discord.Member = None):
        """Worse than hitler?."""
        user = user or ctx.author
        data = await self.get(ctx, f"/hitler?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "hitler.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def humansgood(self, ctx, *, text: str):
        """Humans are wonderful things."""
        data = await self.get(ctx, f"/humansgood?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "humansgood.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def inator(self, ctx, *, text: str):
        """Xinator."""
        data = await self.get(ctx, f"/inator?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "inator.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command(aliases=["invertcolor", "invertcolors", "invercolours"])
    async def invertcolour(self, ctx, user: discord.Member = None):
        """Invert the colour of an image."""
        user = user or ctx.author
        data = await self.get(ctx, f"/invert?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "invert.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def ipad(self, ctx, user: discord.Member = None):
        """Put your picture on an ipad."""
        user = user or ctx.author
        data = await self.get(ctx, f"/ipad?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "ipad.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def jail(self, ctx, user: discord.Member = None):
        """Send yourself to jail."""
        user = user or ctx.author
        data = await self.get(ctx, f"/jail?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "jail.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def justpretending(self, ctx, *, text: str):
        """Playing dead
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/justpretending?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "justpretending.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def kimborder(self, ctx, user: discord.Member = None):
        """Place yourself under mighty kim."""
        user = user or ctx.author
        data = await self.get(ctx, f"/kimborder?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "kimborder.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def knowyourlocation(self, ctx, *, text: str):
        """Google wants to know your location.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/knowyourlocation?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "knowyourlocation.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()  # TODO: MP4s
    async def kowalski(self, ctx, *, text: str):
        """Kowlalski tapping.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/kowalski?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "kowalski.gif"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def laid(self, ctx, user: discord.Member = None):
        """Do you get laid?"""
        user = user or ctx.author
        data = await self.get(ctx, f"/laid?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "laid.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()  # TODO: MP4s
    async def letmein(self, ctx, *, text: str):
        """LET ME IN."""
        data = await self.get(ctx, f"/letmein?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "letmein.mp4"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def lick(self, ctx, *, text: str):
        """Lick lick.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/lick?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "lick.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def madethis(self, ctx, user: discord.Member, user2: discord.Member = None):
        """I made this!"""
        user2 = user2 or ctx.author
        data = await self.get(
            ctx,
            "/madethis?avatar1={}{}".format(
                user.avatar_url_as(static_format="png"),
                f"&avatar2={user2.avatar_url_as(static_format='png')}"
                if user2 is not None
                else "",
            ),
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "madethis.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()  # Support other urls soon
    async def magickify(self, ctx, user: discord.Member = None):
        """Peform magik."""
        user = user or ctx.author
        data = await self.get(ctx, f"/magik?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "magik.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def master(self, ctx, *, text: str):
        """Yes master!
        
        Text must be 3 comma seperated values."""
        data = await self.get(ctx, f"/master?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "master.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def meme(
        self,
        ctx,
        user: typing.Optional[discord.Member],
        top_text: str,
        bottom_text: str,
        color: typing.Optional[str],
        font: typing.Optional[str] = None,
    ):
        """Make your own meme.

        For text longer then one word for each variable, enclose them in ""
        This endpoint works a bit differently from the other endpoints.
        This endpoint takes in top_text and bottom_text parameters instead of text.
        It also supports color and font parameters.
        Fonts supported are: arial, arimobold, impact, robotomedium, robotoregular, sans, segoeuireg, tahoma and verdana.
        Colors can be defined with HEX codes or web colors, e.g. black, white, orange etc. Try your luck ;)
        The default is Impact in white."""
        user = user or ctx.author
        if font:
            fnt = f"&font={font}"
        else:
            fnt = ""
        if color:
            clr = f"&color={color}"
        else:
            clr = ""
        data = await self.get(
            ctx,
            f"/meme?avatar1={user.avatar_url_as(static_format='png')}&top_text={top_text}&bottom_text={bottom_text}{clr}{fnt}",
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "meme.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def note(self, ctx, *, text: str):
        """Pass a note back."""
        data = await self.get(ctx, f"/note?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "note.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def nothing(self, ctx, *, text: str):
        """Woah! nothing."""
        data = await self.get(ctx, f"/nothing?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "nothing.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def ohno(self, ctx, *, text: str):
        """Oh no, it's stupid!"""
        data = await self.get(ctx, f"/ohno?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "ohno.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def piccolo(self, ctx, *, text: str):
        """Piccolo."""
        data = await self.get(ctx, f"/piccolo?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "piccolo.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def plan(self, ctx, *, text: str):
        """Gru makes a plan
        
        Text must be 3 comma seperated values."""
        data = await self.get(ctx, f"/plan?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "plan.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def presentation(self, ctx, *, text: str):
        """Lisa makes a presentation."""
        data = await self.get(ctx, f"/presentation?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "presentation.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def quote(self, ctx, user: typing.Optional[discord.Member] = None, *, text: str):
        """Quote a discord user."""
        user = user or ctx.author

        data = await self.get(
            ctx,
            f"/quote?avatar1={user.avatar_url_as(static_format='png')}&username1={user.name}&text={text}",
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "quote.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def radialblur(self, ctx, user: discord.Member = None):
        """Radiarblur-ify your picture.."""
        user = user or ctx.author
        data = await self.get(
            ctx, f"/radialblur?avatar1={user.avatar_url_as(static_format='png')}"
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "radialblur.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command(aliases=["restinpeace"])
    async def tombstone(self, ctx, user: discord.Member = None):
        """Give a lucky person a tombstone."""
        user = user or ctx.author
        data = await self.get(ctx, f"/rip?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "rip.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def roblox(self, ctx, user: discord.Member = None):
        """Turn yourself into a roblox character."""
        user = user or ctx.author
        data = await self.get(ctx, f"/roblox?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "roblox.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def salty(self, ctx, user: discord.Member = None):
        """Add some salt."""
        user = user or ctx.author
        data = await self.get(ctx, f"/salty?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "salty.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def savehumanity(self, ctx, *, text: str):
        """The secret to saving humanity."""
        data = await self.get(ctx, f"/savehumanity?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "savehumanity.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def screams(self, ctx, user: discord.Member, user2: discord.Member = None):
        """Why can't you just be normal? **Screams**"""
        user2 = user2 or ctx.author
        data = await self.get(
            ctx,
            "/screams?avatar1={}{}".format(
                user.avatar_url_as(static_format="png"),
                f"&avatar2={user2.avatar_url_as(static_format='png')}"
                if user2 is not None
                else "",
            ),
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "screams.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def shit(self, ctx, *, text: str):
        """I stepped in crap."""
        data = await self.get(ctx, f"/shit?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "shit.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def sickban(self, ctx, user: discord.Member = None):
        """Ban this sick filth!"""
        user = user or ctx.author
        data = await self.get(ctx, f"/sickban?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "sickban.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def slap(self, ctx, user: discord.Member, user2: discord.Member = None):
        """*SLAPS*"""
        user2 = user2 or ctx.author
        data = await self.get(
            ctx,
            "/slap?avatar1={}{}".format(
                user.avatar_url_as(static_format="png"),
                f"&avatar2={user2.avatar_url_as(static_format='png')}"
                if user2 is not None
                else "",
            ),
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "slap.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def slapsroof(self, ctx, *, text: str):
        """This bad boy can fit so much in it."""
        data = await self.get(ctx, f"/slapsroof?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "slapsroof.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def sneakyfox(self, ctx, *, text: str):
        """That sneaky fox.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/sneakyfox?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "sneakyfox.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def spank(self, ctx, user: discord.Member, user2: discord.Member = None):
        """*spanks*"""
        user2 = user2 or ctx.author
        data = await self.get(
            ctx,
            "/spank?avatar1={}{}".format(
                user.avatar_url_as(static_format="png"),
                f"&avatar2={user2.avatar_url_as(static_format='png')}"
                if user2 is not None
                else "",
            ),
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "spank.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def stroke(self, ctx, *, text: str):
        """How to recognize a stroke?"""
        data = await self.get(ctx, f"/stroke?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "stroke.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def surprised(self, ctx, *, text: str):
        """Pikasuprised
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/surprised?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "surprised.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def sword(self, ctx, user: typing.Optional[discord.Member] = None, *, text: str):
        """Swordknife."""
        user = user or ctx.author

        data = await self.get(
            ctx,
            f"/sword?avatar1={user.avatar_url_as(static_format='png')}&username1={user.name}&text={text}",
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "sword.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def thesearch(self, ctx, *, text: str):
        """The search for intelligent life continues.."""
        data = await self.get(ctx, f"/thesearch?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "thesearch.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def trash(self, ctx, user: discord.Member = None):
        """Peter Parker trash."""
        user = user or ctx.author
        data = await self.get(ctx, f"/trash?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "trash.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def trigger(self, ctx, user: discord.Member = None):
        """Triggerfied."""
        user = user or ctx.author
        data = await self.get(ctx, f"/trigger?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "trigger.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def tweet(
        self,
        ctx,
        user: typing.Optional[discord.Member],
        username1: str,
        username2: str,
        *,
        text: str,
    ):
        """Create a fake tweet.

        avatar1: Image URL. Usually a Discord Avatar. Supports at least JPG, PNG and BMP!
        username1: String. Username for the first user.
        text: String. Text to show on the generated image.
        username2: String. Username for the second user.
        altstyle: Endpoint specific parameter"""
        user = user or ctx.author
        data = await self.get(
            ctx,
            f"/tweet?avatar1={user.avatar_url_as(static_format='png')}&username1={username1}&username2={username2}&text={text}",
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "tweet.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def ugly(self, ctx, user: discord.Member = None):
        """Make a user ugly."""
        user = user or ctx.author
        data = await self.get(ctx, f"/ugly?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "ugly.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def unpopular(self, ctx, user: typing.Optional[discord.Member] = None, *, text: str):
        """Get rid of that pesky teacher."""
        user = user or ctx.author

        data = await self.get(
            ctx,
            f"/unpopular?avatar1={user.avatar_url_as(static_format='png')}&username1={user.name}&text={text}",
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "unpopular.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def violence(self, ctx, *, text: str):
        """Violence is never the answer."""
        data = await self.get(ctx, f"/violence?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "violence.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def violentsparks(self, ctx, *, text: str):
        """Some violent sparks.
        
        Text must be 2 comma seperated values."""
        data = await self.get(ctx, f"/violentsparks?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "violentsparks.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def vr(self, ctx, *, text: str):
        """Woah, VR is so realistic."""
        data = await self.get(ctx, f"/vr?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "vr.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def walking(self, ctx, *, text: str):
        """Walking Meme"""
        data = await self.get(ctx, f"/walking?text={text}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "walking.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def wanted(self, ctx, user: discord.Member = None):
        """Heard you're a wanted fugitive?"""
        user = user or ctx.author
        data = await self.get(ctx, f"/wanted?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "wanted.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def warp(self, ctx, user: discord.Member = None):
        """Warp?."""
        user = user or ctx.author
        data = await self.get(ctx, f"/warp?avatar1={user.avatar_url_as(static_format='png')}")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "warp.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def whodidthis(self, ctx, user: discord.Member = None):
        """Who did this?"""
        user = user or ctx.author
        data = await self.get(
            ctx, f"/whodidthis?avatar1={user.avatar_url_as(static_format='png')}"
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "whodidthis.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def whothisis(self, ctx, user: typing.Optional[discord.Member], username: str):
        """replace help msg."""
        user = user or ctx.author
        data = await self.get(
            ctx, f"/whothisis?avatar1={user.avatar_url_as(static_format='png')}&text={username}"
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "whothisis.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def yomomma(self, ctx):
        """Yo momma!."""
        user = user or ctx.author
        data = await self.get(ctx, f"/yomomma")
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "yomomma.png"
        await ctx.send(file=discord.File(data))

    @commands.check(tokencheck)
    @commands.command()
    async def youtube(self, ctx, user: typing.Optional[discord.Member] = None, *, text: str):
        """Create a youtube comment."""
        user = user or ctx.author

        data = await self.get(
            ctx,
            f"/youtube?avatar1={user.avatar_url_as(static_format='png')}&username1={user.name}&text={text}",
        )
        if isinstance(data, dict):
            return await self.send_error(ctx, data)
        data.name = "youtube.png"
        await ctx.send(file=discord.File(data))
