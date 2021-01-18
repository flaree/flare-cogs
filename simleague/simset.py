import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box

from .abc import MixinMeta


class SimsetMixin(MixinMeta):
    """Simulation Settings"""

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(autohelp=True)
    async def simset(self, ctx):
        """Simulation Settings."""
        if ctx.invoked_subcommand is None:
            guild = ctx.guild
            # Display current settings
            gametime = await self.config.guild(guild).gametime()
            htbreak = await self.config.guild(guild).htbreak()
            results = await self.config.guild(guild).resultchannel()
            bettoggle = await self.config.guild(guild).bettoggle()
            maxplayers = await self.config.guild(guild).maxplayers()
            redcardmodif = await self.config.guild(guild).redcardmodifier()
            transfers = await self.config.guild(guild).transferwindow()
            mentions = await self.config.guild(guild).mentions()
            msg = ""
            msg += "Game Time: 1m for every {}s.\n".format(gametime)
            msg += "Team Limit: {} players.\n".format(maxplayers)
            msg += "HT Break: {}s.\n".format(htbreak)
            msg += "Red Card Modifier: {}% loss per red card.\n".format(redcardmodif)
            msg += "Posting Results: {}.\n".format("Yes" if results else "No")
            msg += "Transfer Window: {}.\n".format("Open" if transfers else "Closed")
            msg += "Accepting Bets: {}.\n".format("Yes" if bettoggle else "No")
            msg += "Mentions on game start: {}.\n".format("Yes" if mentions else "No")

            if bettoggle:
                bettime = await self.config.guild(guild).bettime()
                betmax = await self.config.guild(guild).betmax()
                betmin = await self.config.guild(guild).betmin()
                msg += "Bet Time: {}s.\n".format(bettime)
                msg += "Max Bet: {}.\n".format(betmax)
                msg += "Min Bet: {}.\n".format(betmin)
            await ctx.send(box(msg))

    @checks.admin_or_permissions(manage_guild=True)
    @simset.group(autohelp=True)
    async def bet(self, ctx):
        """Simulation Betting Settings."""

    @checks.guildowner()
    @simset.command(autohelp=True, hidden=True)
    async def cupmode(self, ctx, bool: bool):
        """Set if the simulation is in cup mode.
        It disables the standings command."""
        if bool:
            await ctx.send("Cup mode is now active.")
            await self.config.guild(ctx.guild).cupmode.set(bool)
        else:
            await ctx.send("Cup mode is now disabled.")
            await self.config.guild(ctx.guild).cupmode.set(bool)

    @checks.guildowner()
    @simset.group(autohelp=True, hidden=True)
    async def probability(self, ctx):
        """Simulation Probability Settings. May break the cog if changed."""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                box("This has the chance to break the game completely, no support is offered.")
            )

    @probability.command()
    async def goals(self, ctx, amount: int = 96):
        """Goal probability. Default = 96"""
        if amount > 100 or amount < 1:
            return await ctx.send("Amount must be greater than 0 and less than 100.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["goalchance"] = amount
        await ctx.tick()

    @probability.command()
    async def yellow(self, ctx, amount: int = 98):
        """Yellow Card probability. Default = 98"""
        if amount > 100 or amount < 1:
            return await ctx.send("Amount must be greater than 0 and less than 100.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["yellowchance"] = amount
        await ctx.tick()

    @checks.guildowner()
    @simset.command()
    async def maxplayers(self, ctx, amount: int):
        """Set the max team players."""
        if amount < 3 or amount > 7:
            return await ctx.send("Amount must be between 3 and 7.")
        await self.config.guild(ctx.guild).maxplayers.set(amount)
        await ctx.tick()

    @simset.command()
    async def redcardmodifier(self, ctx, amount: int):
        """Set the max team players."""
        if amount < 1 or amount > 30:
            return await ctx.send("Amount must be between 1 and 30.")
        await self.config.guild(ctx.guild).redcardmodifier.set(amount)
        await ctx.tick()

    @probability.command()
    async def red(self, ctx, amount: int = 398):
        """Red Card probability. Default = 398"""
        if amount > 400 or amount < 1:
            return await ctx.send("Amount must be greater than 0 and less than 400.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["redchance"] = amount
        await ctx.tick()

    @probability.command()
    async def penalty(self, ctx, amount: int = 249):
        """Penalty Chance probability. Default = 249"""
        if amount > 250 or amount < 1:
            return await ctx.send("Amount must be greater than 0 and less than 250.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["penaltychance"] = amount
        await ctx.tick()

    @probability.command()
    async def penaltyblock(self, ctx, amount: float = 0.6):
        """Penalty Block probability. Default = 0.6"""
        if amount > 1 or amount < 0:
            return await ctx.send("Amount must be greater than 0 and less than 1.")
        async with self.config.guild(ctx.guild).probability() as probability:
            probability["penaltyblock"] = amount
        await ctx.tick()

    @bet.command()
    async def time(self, ctx, time: int = 180):
        """Set the time allowed for betting - 600 seconds is the max, 180 is default."""
        if time < 0 or time > 600:
            time = 180
        await self.config.guild(ctx.guild).bettime.set(time)
        await ctx.tick()

    @bet.command()
    async def max(self, ctx, amount: int):
        """Set the max amount for betting."""
        if amount < 1:
            return await ctx.send("Amount must be greater than 0.")
        await self.config.guild(ctx.guild).betmax.set(amount)
        await ctx.tick()

    @bet.command()
    async def min(self, ctx, amount: int):
        """Set the min amount for betting."""
        if amount < 1:
            return await ctx.send("Amount must be greater than 0.")
        await self.config.guild(ctx.guild).betmin.set(amount)
        await ctx.tick()

    @bet.command()
    async def toggle(self, ctx, toggle: bool):
        """Set if betting is enabled or not.
        Toggle must be a valid bool."""
        await self.config.guild(ctx.guild).bettoggle.set(toggle)
        await ctx.tick()

    @simset.command()
    async def gametime(self, ctx, time: float = 1):
        """Set the time each minute takes - 5 seconds is the max. 1 is default."""
        if time < 0 or time > 5:
            time = 90
        await self.config.guild(ctx.guild).gametime.set(time)
        await ctx.tick()

    @simset.command()
    async def halftimebreak(self, ctx, time: int = 1):
        """Set the half time break - 20 seconds is the max. 5 is default."""
        if time < 0 or time > 20:
            time = 5
        await self.config.guild(ctx.guild).htbreak.set(time)
        await ctx.tick()

    @simset.command()
    async def resultchannel(self, ctx, channel: discord.TextChannel):
        """Add a channel for automatic result posting."""
        async with self.config.guild(ctx.guild).resultchannel() as channels:
            if channel.id in channels:
                await ctx.send("Results are already posted in this channel")
                return

            channels.append(channel.id)
        await ctx.tick()

    @simset.command()
    async def resultchannels(self, ctx, option: str):
        """Show or clear all result channels."""
        if option == "clear":
            await self.config.guild(ctx.guild).resultchannel.set([])
            await ctx.tick()
        elif option == "show":
            async with self.config.guild(ctx.guild).resultchannel() as result:
                a = []
                for res in result:
                    channel = ctx.guild.get_channel(res)
                    if channel is not None:
                        a.append(channel.name)
                embed = discord.Embed(
                    title="Result channels", description="\n".join(a), colour=0xFF0000
                )
                await ctx.send(embed=embed)
        else:
            await ctx.send("No parameter for resultchannels, you must choose 'show' or 'clear'")

    @simset.command()
    async def window(self, ctx, status: str):
        """Open or close the transfer window."""
        if status.lower() not in ["open", "close"]:
            return await ctx.send("You must specify either 'open' or 'close'.")
        if status == "open":
            await self.config.guild(ctx.guild).transferwindow.set(True)
            await ctx.send("Window is now open.")
        else:
            await self.config.guild(ctx.guild).transferwindow.set(False)
            await ctx.send("Window is now closed.")

    @simset.command()
    async def mentions(self, ctx, bool: bool):
        """Toggle mentions on game start."""
        if bool:
            await self.config.guild(ctx.guild).mentions.set(True)
        else:
            await self.config.guild(ctx.guild).mentions.set(False)

    @simset.command(name="updatecache")
    async def levels_updatecache(self, ctx):
        """Update the level cache."""
        async with ctx.typing():
            await self.updatecacheall(ctx.guild)
        await ctx.tick()

    @simset.command()
    @commands.bot_has_permissions(manage_roles=True)
    async def createroles(self, ctx):
        """Create roles for teams"""
        async with self.config.guild(ctx.guild).teams() as teams:
            for team in teams:
                if teams[team]["role"] is not None:
                    continue
                role = await ctx.guild.create_role(name=team)
                teams[team]["role"] = role.id
            await ctx.tick()

    @simset.command()
    @commands.bot_has_permissions(manage_roles=True)
    async def updateroles(self, ctx):
        """Update roles for teammembers."""
        teams = await self.config.guild(ctx.guild).teams()
        for team in teams:
            if teams[team]["role"] is None:
                self.log.debug(f"Skipping {team}, no role found.")
                continue
            role = ctx.guild.get_role(teams[team]["role"])
            for user in teams[team]["members"]:
                member = ctx.guild.get_member(int(user))
                await member.add_roles(role)
        await ctx.tick()

    @simset.command()
    async def createfixtures(self, ctx):
        """Create the fixtures for the current teams."""
        teams = await self.config.guild(ctx.guild).teams()
        teams = list(teams.keys())
        if len(teams) % 2:
            teams.append("DAY OFF")
        n = len(teams)
        matchs = []
        fixtures = []
        return_matchs = []
        for fixture in range(1, n):
            for i in range(n // 2):
                matchs.append((teams[i], teams[n - 1 - i]))
                return_matchs.append((teams[n - 1 - i], teams[i]))
            teams.insert(1, teams.pop())
            fixtures.insert(len(fixtures) // 2, matchs)
            fixtures.append(return_matchs)
            matchs = []
            return_matchs = []

        a = []
        for k, fixture in enumerate(fixtures, 1):
            a.append(f"Week {k}\n----------")
            for i, game in enumerate(fixture, 1):
                a.append(f"Game {i}: {game[0]} vs {game[1]}")
            a.append("----------")
        await self.config.guild(ctx.guild).fixtures.set(fixtures)
        await ctx.tick()

    @checks.guildowner()
    @simset.group()
    async def clear(self, ctx):
        """SimLeague Clear Settings"""

    @clear.command(name="all")
    async def clear_all(self, ctx):
        """Clear all teams, stats etc."""
        await self.config.guild(ctx.guild).clear()
        await self.config.guild(ctx.guild).standings.set({})
        await self.config.guild(ctx.guild).stats.set({})
        await ctx.tick()

    @clear.command(name="stats")
    async def clear_stats(self, ctx):
        """Clear standings and player stats."""
        await self.config.guild(ctx.guild).standings.set({})
        teams = await self.config.guild(ctx.guild).teams()
        async with self.config.guild(ctx.guild).standings() as standings:
            for team in teams:
                standings[team] = {
                    "played": 0,
                    "wins": 0,
                    "losses": 0,
                    "points": 0,
                    "gd": 0,
                    "gf": 0,
                    "ga": 0,
                    "draws": 0,
                }
        await self.config.guild(ctx.guild).stats.set({})
        await ctx.tick()
