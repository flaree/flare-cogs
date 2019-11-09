import discord
import asyncio
from discord.ext import tasks
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import humanize_list
import datetime
from typing import Union

# thanks to DevilXD for ASL which provided the inspiration/parts of code for this cog.

class Spammute(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        defaults = {"bannedwords": [], "toggle": False, "muterole": None, "ignored": [], "count": 3}
        default = {"muted": {}}
        self.config.register_guild(**defaults)
        self.config.register_global(**default)
        self.spam = {}
        self.expiredcheck.start()
    
    def cog_unload(self):
        self.expiredcheck.cancel()
    
    @checks.mod()
    @commands.group()
    async def spamset(self, ctx):
        pass

    @checks.admin()
    @spamset.command()
    async def add(self, ctx, *, word: str):
        """Add a word to the ban list."""
        async with self.config.guild(ctx.guild).bannedwords() as words:
            words.append(word)
        await ctx.tick()
    
    @checks.admin()
    @spamset.command()
    async def status(self, ctx):
        """Spam Settings."""
        bannedwords = await self.config.guild(ctx.guild).bannedwords()
        toggle = await self.config.guild(ctx.guild).toggle()
        muterole = await self.config.guild(ctx.guild).muterole()
        count = await self.config.guild(ctx.guild).count()
        if muterole is None:
            return await ctx.send("Ensure a valid mute role is set via {}spamset muterole".format(ctx.prefix))
        mute_role = ctx.guild.get_role(muterole)
        if mute_role is None:
            return await ctx.send("Ensure a valid mute role is set via {}spamset muterole".format(ctx.prefix))
        embed = discord.Embed(title="Spam Settings for {}".format(ctx.guild.name), colour=ctx.author.color)
        embed.add_field(name="Toggled:", value="{}".format("Yes" if toggle else "No"))
        embed.add_field(name="Mute Role:", value=mute_role.mention)
        embed.add_field(name="Amount Before Mute:", value=count)
        embed.add_field(name="Banned Words:", value=humanize_list(bannedwords) if bannedwords else "None")
        await ctx.send(embed=embed)
    
    @checks.admin()
    @spamset.command()
    async def muterole(self, ctx, role: discord.Role):
        """Set the mute role for the server."""
        await self.config.guild(ctx.guild).muterole.set(role.id)
        await ctx.tick()
    
    @checks.admin()
    @spamset.command()
    async def amount(self, ctx, amount: int):
        """Set the amount of messages required for mute."""
        if amount > 0 and amount < 10:
            await self.config.guild(ctx.guild).count.set(amount)
            await ctx.tick()
        else:
            await ctx.send("Provide an amount between 1 and 10.")

    @checks.admin()
    @spamset.command()
    async def toggle(self, ctx, yes_or_no: bool):
        """Toggle the spam settings."""
        if yes_or_no:
            await self.config.guild(ctx.guild).toggle.set(yes_or_no)
            await ctx.send("Spam mode has been enabled for this server.")
        else:
            await self.config.guild(ctx.guild).toggle.set(yes_or_no)
            await ctx.send("Spam mode has been disabled for this server.")

    @checks.admin()
    @spamset.command()
    async def remove(self, ctx, *, word: str):
        """Remove a word from the ban list."""
        async with self.config.guild(ctx.guild).bannedwords() as words:
            try:
                words.remove(word)
                await ctx.tick()
            except ValueError:
                await ctx.send("Oops, that word isn't in the list of banned words.")

    @checks.admin()
    @spamset.command()
    async def ignore(self, ctx, *, to_ignore: Union[discord.Member, discord.TextChannel, discord.Role]):
        """Ignore a member, channel or role."""
        if isinstance(to_ignore, discord.Member):
            name = "`{}`".format(to_ignore)
        elif isinstance(to_ignore, discord.TextChannel):
            name = "{}".format(to_ignore.mention)
        elif isinstance(to_ignore, discord.Role):
            name = "`{}`".format(to_ignore.name)
        
        async with self.config.guild(ctx.guild).ignored() as ignored:
            if to_ignore.id in ignored:
                ignored.remove(to_ignore.id)
                await ctx.send("Tracking {} again".format(name))
            else:
                ignored.append(to_ignore.id)
                await ctx.send("Not tracking {} anymore".format(name))

    @checks.mod()
    @spamset.command()
    async def isignored(self, ctx, *, to_check: Union[discord.Member, discord.TextChannel, discord.Role]):
        """Check if a member, channel or role is ignored."""
        guild = ctx.guild
        if isinstance(to_check, discord.Member):
            is_it = await self.is_ignored(guild, member=to_check)
        elif isinstance(to_check, discord.TextChannel):
            is_it = await self.is_ignored(guild, channel=to_check)
        elif isinstance(to_check, discord.Role):
            ignored = set(await self.config.guild(guild).ignored())
            is_it = to_check.id in ignored
        if is_it:
            await ctx.send("This member / channel / role is ignored! ✓")
        else:
            await ctx.send("This member / channel / role is not ignored! :x:")

    async def is_ignored(self, guild, member=None, channel=None):
        ignored = set(await self.config.guild(guild).ignored())
        to_check = []
        if channel:
            to_check.append(channel.id)
        if member:
            to_check.append(member.id)
            to_check.extend(r.id for r in member.roles)
        return bool(ignored.intersection(to_check))


    @tasks.loop(seconds=10)
    async def expiredcheck(self):
        muted = await self.config.muted()
        for guild in muted:
            for user in muted[guild]:
                if datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(int(muted[guild][user]["time"].split(".")[0])) > datetime.timedelta(minutes=30): # TODO: Make this configurable.
                    await self.unmute(muted[guild][user]["id"], muted[guild][user]["guild"])

    async def unmute(self, user_id, guild_id):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        user = guild.get_member(user_id)
        if user is None:
            return
        muted_role = await self.config.guild(guild).muterole()
        muted_role = guild.get_role(muted_role)
        if muted_role is None:
            return
        await user.remove_roles(muted_role, reason="Automatially Unmuted")
        async with self.config.muted() as muted:
            del muted[str(guild.id)][str(user.id)]
    
    @commands.Cog.listener()
    async def on_message(self, message):
        guild = message.guild
        author = message.author
        content = message.content.split()
        toggle = await self.config.guild(guild).toggle()
        if not toggle:
            return
        if await self.is_ignored(guild, message.author, None):
            return
        words = await self.config.guild(guild).bannedwords()
        if not any(word in words for word in content):
            return
        if guild.id not in self.spam:
            self.spam[guild.id] = {}
        if author.id not in self.spam[guild.id]:
            self.spam[guild.id][author.id] = {"guild": guild.id, "id": author.id, "time": datetime.datetime.utcnow(), "count": 1}
        else:
            if datetime.datetime.utcnow() - self.spam[guild.id][author.id]["time"] > datetime.timedelta(seconds=120): #TODO: Make this configurable
                self.spam[guild.id][author.id] = {"guild": guild.id, "id": author.id, "time": datetime.datetime.utcnow(), "count": 1}
                return
            self.spam[guild.id][author.id]["count"] += 1
            if self.spam[guild.id][author.id]["count"] >= await self.config.guild(guild).count():
                muted_role = await self.config.guild(guild).muterole()
                muted_role = guild.get_role(muted_role)
                if muted_role is None:
                    return
                await author.add_roles(muted_role, reason="Muted due to spamming banned words.")
                async with self.config.muted() as muted:
                    if guild.id not in muted:
                        muted[guild.id] = {}
                    muted[guild.id][author.id] = {"guild": guild.id, "id": author.id, "time": str(datetime.datetime.utcnow().timestamp())}

            

        



    