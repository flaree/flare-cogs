import logging

import discord
from redbot.core import Config, bank, commands
from redbot.core.utils import AsyncIter
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.utils.common_filters import filter_invites

adventure_bank = None


log = logging.getLogger("red.flare.userinfo")

# Thanks Preda, core logic is from https://github.com/PredaaA/predacogs/blob/master/serverinfo/serverinfo.py
class Userinfo(commands.Cog):
    """Replace original Red userinfo command with more details."""

    __version__ = "0.3.2"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 95932766180343808, force_registration=True)
        default_global = {
            "banner": False,
            "status_emojis": {
                "mobile": 749067110931759185,
                "online": 749221433552404581,
                "away": 749221433095356417,
                "dnd": 749221432772395140,
                "offline": 749221433049088082,
                "streaming": 749221434039205909,
            },
            "badge_emojis": {
                "staff": 848556248832016384,
                "early_supporter": 706198530837970998,
                "hypesquad_balance": 706198531538550886,
                "hypesquad_bravery": 706198532998299779,
                "hypesquad_brilliance": 706198535846101092,
                "hypesquad": 706198537049866261,
                "verified_bot_developer": 706198727953612901,
                "bug_hunter": 848556247632052225,
                "bug_hunter_level_2": 706199712402898985,
                "partner": 848556249192202247,
                "verified_bot": 848561838974697532,
                "verified_bot2": 848561839260434482,
            },
        }
        self.config.register_global(**default_global)
        self.emojis = self.bot.loop.create_task(self.init())

    def cog_unload(self):
        if self.emojis:
            self.emojis.cancel()

    async def init(self):
        await self.bot.wait_until_ready()
        await self.gen_emojis()

    async def gen_emojis(self):
        config = await self.config.all()
        self.status_emojis = {
            "mobile": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["mobile"]),
            "online": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["online"]),
            "away": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["away"]),
            "dnd": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["dnd"]),
            "offline": discord.utils.get(self.bot.emojis, id=config["status_emojis"]["offline"]),
            "streaming": discord.utils.get(
                self.bot.emojis, id=config["status_emojis"]["streaming"]
            ),
        }
        self.badge_emojis = {
            "staff": discord.utils.get(self.bot.emojis, id=config["badge_emojis"]["staff"]),
            "early_supporter": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["early_supporter"]
            ),
            "hypesquad_balance": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["hypesquad_balance"]
            ),
            "hypesquad_bravery": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["hypesquad_bravery"]
            ),
            "hypesquad_brilliance": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["hypesquad_brilliance"]
            ),
            "hypesquad": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["hypesquad"]
            ),
            "verified_bot_developer": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["verified_bot_developer"]
            ),
            "bug_hunter": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["bug_hunter"]
            ),
            "bug_hunter_level_2": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["bug_hunter_level_2"]
            ),
            "partner": discord.utils.get(self.bot.emojis, id=config["badge_emojis"]["partner"]),
            "verified_bot": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["verified_bot"]
            ),
            "verified_bot2": discord.utils.get(
                self.bot.emojis, id=config["badge_emojis"]["verified_bot2"]
            ),
        }

    async def red_get_data_for_user(self, *, user_id: int):
        # this cog does not store any data
        return {}

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        # this cog does not store any data
        pass

    def cog_unload(self):
        # Remove command logic are from: https://github.com/mikeshardmind/SinbadCogs/tree/v3/messagebox
        global _old_userinfo
        if _old_userinfo:
            try:
                self.bot.remove_command("userinfo")
            except Exception as error:
                log.info(error)
            self.bot.add_command(_old_userinfo)

    @commands.group()
    @commands.is_owner()
    async def uinfoset(self, ctx):
        """Manage userinfo settings."""

    @uinfoset.command(hidden=True)
    async def setemoji(self, ctx, status_or_badge: str, type: str, emoji_id: int):
        """Set status or badge emoji"""
        if status_or_badge not in ["status", "badge"]:
            return await ctx.send("You must choose either status or badge.")
        if status_or_badge == "status":
            async with self.config.status_emojis() as emojis:
                if type not in emojis:
                    await ctx.send(
                        f"""That emoji doesn't exist. Valid emoji types are: {", ".join(emojis.keys())}"""
                    )

                    return
                emojis[type] = emoji_id
        else:
            async with self.config.badge_emojis() as emojis:
                if type not in emojis:
                    await ctx.send(
                        f"""That emoji doesn't exist. Valid emoji types are: {", ".join(emojis.keys())}"""
                    )

                    return
                emojis[type] = emoji_id
        await self.gen_emojis()
        await ctx.tick()

    @uinfoset.command()
    async def clear(self, ctx):
        """Reset emojis to default."""
        await self.config.clear_all()
        await self.gen_emojis()
        await ctx.tick()

    @uinfoset.command()
    async def banner(self, ctx):
        """Toggle banner on userinfo.

        Note: This causes a fetch request which can be a heavy operation."""
        await self.config.banner.set(not await self.config.banner())
        await ctx.tick()

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx, *, user: discord.Member = None):
        """Show userinfo with some more detail."""
        mod = self.bot.get_cog("Mod")
        async with ctx.typing():
            author = ctx.author
            guild = ctx.guild

            if not user:
                user = author
            sharedguilds = (
                user.mutual_guilds
                if hasattr(user, "mutual_guilds")
                else {
                    guild
                    async for guild in AsyncIter(self.bot.guilds, steps=100)
                    if user in guild.members
                }
            )
            roles = user.roles[-1:0:-1]
            names, nicks = await mod.get_names_and_nicks(user)

            joined_at = user.joined_at
            since_created = int((ctx.message.created_at - user.created_at).days)
            if joined_at is not None:
                since_joined = int((ctx.message.created_at - joined_at).days)
                user_joined = joined_at.strftime("%d %b %Y %H:%M")
            else:
                since_joined = "?"
                user_joined = "Unknown"
            user_created = user.created_at.strftime("%d %b %Y %H:%M")
            voice_state = user.voice
            member_number = (
                sorted(guild.members, key=lambda m: m.joined_at or ctx.message.created_at).index(
                    user
                )
                + 1
            )

            created_on = "{}\n({} day{} ago)".format(
                user_created, since_created, "" if since_created == 1 else "s"
            )
            joined_on = "{}\n({} day{} ago)".format(
                user_joined, since_joined, "" if since_joined == 1 else "s"
            )
            if user.is_on_mobile():
                statusemoji = self.status_emojis["mobile"] or "\N{MOBILE PHONE}"
            elif any(a.type is discord.ActivityType.streaming for a in user.activities):
                statusemoji = self.status_emojis["streaming"] or "\N{LARGE PURPLE CIRCLE}"
            elif user.status.name == "online":
                statusemoji = self.status_emojis["online"] or "\N{LARGE GREEN CIRCLE}"
            elif user.status.name == "offline":
                statusemoji = self.status_emojis["offline"] or "\N{MEDIUM WHITE CIRCLE}"
            elif user.status.name == "dnd":
                statusemoji = self.status_emojis["dnd"] or "\N{LARGE RED CIRCLE}"
            elif user.status.name == "idle":
                statusemoji = self.status_emojis["away"] or "\N{LARGE ORANGE CIRCLE}"
            else:
                statusemoji = "\N{MEDIUM BLACK CIRCLE}\N{VARIATION SELECTOR-16}"
            activity = "Chilling in {} status".format(user.status)
            status_string = mod.get_status_string(user)

            if roles:

                role_str = ", ".join([x.mention for x in roles])
                # 400 BAD REQUEST (error code: 50035): Invalid Form Body
                # In embed.fields.2.value: Must be 1024 or fewer in length.
                if len(role_str) > 1024:
                    # Alternative string building time.
                    # This is not the most optimal, but if you're hitting this, you are losing more time
                    # to every single check running on users than the occasional user info invoke
                    # We don't start by building this way, since the number of times we hit this should be
                    # infintesimally small compared to when we don't across all uses of Red.
                    continuation_string = (
                        "and {numeric_number} more roles not displayed due to embed limits."
                    )

                    available_length = 1024 - len(
                        continuation_string
                    )  # do not attempt to tweak, i18n

                    role_chunks = []
                    remaining_roles = 0

                    for r in roles:
                        chunk = f"{r.mention}, "
                        chunk_size = len(chunk)

                        if chunk_size < available_length:
                            available_length -= chunk_size
                            role_chunks.append(chunk)
                        else:
                            remaining_roles += 1
                    role_chunks.append(continuation_string.format(numeric_number=remaining_roles))

                    role_str = "".join(role_chunks)
            else:
                role_str = None
            data = discord.Embed(
                description=(status_string or activity)
                + f"\n\n{len(sharedguilds)} shared servers."
                if len(sharedguilds) > 1
                else f"\n\n{len(sharedguilds)} shared server.",
                colour=user.colour,
            )

            data.add_field(name="Joined Discord on", value=created_on)
            data.add_field(name="Joined this server on", value=joined_on)
            if role_str is not None:
                data.add_field(name="Roles", value=role_str, inline=False)
            if names:
                # May need sanitizing later, but mentions do not ping in embeds currently
                val = filter_invites(", ".join(names))
                data.add_field(name="Previous Names", value=val, inline=False)
            if nicks:
                # May need sanitizing later, but mentions do not ping in embeds currently
                val = filter_invites(", ".join(nicks))
                data.add_field(name="Previous Nicknames", value=val, inline=False)
            if voice_state and voice_state.channel:
                data.add_field(
                    name="Current voice channel",
                    value="{0.mention} ID: {0.id}".format(voice_state.channel),
                    inline=False,
                )
            data.set_footer(text="Member #{} | User ID: {}".format(member_number, user.id))

            name = str(user)
            name = " ~ ".join((name, user.nick)) if user.nick else name
            name = filter_invites(name)

            avatar = user.avatar_url_as(static_format="png")
            data.title = f"{statusemoji} {name}"
            data.set_thumbnail(url=avatar)

            flags = [f.name for f in user.public_flags.all()]
            badges = ""
            badge_count = 0
            if flags:
                for badge in sorted(flags):
                    if badge == "verified_bot":
                        emoji1 = self.badge_emojis["verified_bot"]
                        emoji2 = self.badge_emojis["verified_bot2"]
                        emoji = f"{emoji1}{emoji2}" if emoji1 else None
                    else:
                        emoji = self.badge_emojis[badge]
                    if emoji:
                        badges += f"{emoji} {badge.replace('_', ' ').title()}\n"
                    else:
                        badges += f"\N{BLACK QUESTION MARK ORNAMENT}\N{VARIATION SELECTOR-16} {badge.replace('_', ' ').title()}\n"
                    badge_count += 1
            if badges:
                data.add_field(name="Badges" if badge_count > 1 else "Badge", value=badges)
            if "Economy" in self.bot.cogs:
                balance_count = 1
                bankstat = f"**Bank**: {humanize_number(await bank.get_balance(user))} {await bank.get_currency_name(ctx.guild)}\n"

                if "Unbelievaboat" in self.bot.cogs:
                    cog = self.bot.get_cog("Unbelievaboat")
                    state = await cog.walletdisabledcheck(ctx)
                    if not state:
                        balance_count += 1
                        balance = await cog.walletbalance(user)
                        bankstat += f"**Wallet**: {humanize_number(balance)} {await bank.get_currency_name(ctx.guild)}\n"

                if "Adventure" in self.bot.cogs:
                    cog = self.bot.get_cog("Adventure")
                    if getattr(cog, "_separate_economy", False):
                        global adventure_bank
                        if adventure_bank is None:
                            try:
                                from adventure import bank as adventure_bank
                            except:
                                pass
                        if adventure_bank:
                            adventure_currency = await adventure_bank.get_balance(user)
                            balance_count += 1
                            bankstat += f"**Adventure**: {humanize_number(adventure_currency)} {await adventure_bank.get_currency_name(ctx.guild)}"

                data.add_field(name="Balances" if balance_count > 1 else "Balance", value=bankstat)
            if await self.config.banner():
                banner = (
                    await self.bot.http.request(discord.http.Route("GET", f"/users/{user.id}"))
                ).get("banner", None)
                if banner is not None:
                    ext = ".gif" if banner.startswith("a_") else ".png"
                    banner_url = (
                        f"https://cdn.discordapp.com/banners/{user.id}/{banner}{ext}?size=4096"
                    )
                    data.set_image(url=banner_url)
            await ctx.send(embed=data)


try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError


async def setup(bot):
    uinfo = Userinfo(bot)
    if "Mod" not in bot.cogs:
        raise CogLoadError("This cog requires the Mod cog to be loaded.")
    global _old_userinfo
    if _old_userinfo := bot.get_command("userinfo"):
        bot.remove_command(_old_userinfo.name)
    bot.add_cog(uinfo)
