import datetime

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number, humanize_timedelta
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .abc import MixinMeta
from .checks import check_global_setting_admin
from .functions import chunks


class SettingsMixin(MixinMeta):
    """Settings."""

    @commands.group(name="unbset", aliases=["unb-set"])
    @check_global_setting_admin()
    @commands.guild_only()
    async def unb_set(self, ctx):
        """Manage various settings for Unbelievaboat."""

    @commands.guild_only()
    @unb_set.command(name="cooldown")
    async def cooldown_set(
        self,
        ctx,
        job,
        *,
        time: commands.TimedeltaConverter(
            minimum=datetime.timedelta(seconds=0),
            maximum=datetime.timedelta(days=2),
            default_unit="minutes",
        ),
    ):
        """Set the cooldown for the work, crime or rob commands. Minimum cooldown is 30 seconds.

        The time can be formatted as so `1h30m` etc. Valid times are hours, minutes and seconds.
        """
        job = job.lower()
        if job not in ["work", "crime", "rob", "deposit", "withdraw"]:
            return await ctx.send("Invalid job.")
        seconds = time.total_seconds()
        if seconds < 30:
            return await ctx.send("The miniumum interval is 30 seconds.")
        conf = await self.configglobalcheck(ctx)
        async with conf.cooldowns() as cooldowns:
            jobcd = {
                "work": "workcd",
                "crime": "crimecd",
                "rob": "robcd",
                "deposit": "depositcd",
                "withdraw": "withdrawcd",
            }
            cooldowns[jobcd[job]] = int(seconds)
        await ctx.tick()

    @check_global_setting_admin()
    @commands.guild_only()
    @unb_set.command(name="payout", usage="<work | crime> <min | max> <amount>")
    async def payout_set(self, ctx, job: str, min_or_max: str, amount: int):
        """Set the min or max payout for working or crimes."""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        if min_or_max not in ["max", "min"]:
            return await ctx.send("You must choose between min or max.")
        conf = await self.configglobalcheck(ctx)
        async with conf.payouts() as payouts:
            payouts[job][min_or_max] = amount
        await ctx.tick()

    @check_global_setting_admin()
    @commands.guild_only()
    @unb_set.command(name="betting", usage="<min | max> <amount>")
    async def betting_set(self, ctx, min_or_max: str, amount: int):
        """Set the min or max betting amounts."""
        if min_or_max not in ["max", "min"]:
            return await ctx.send("You must choose between min or max.")
        conf = await self.configglobalcheck(ctx)
        async with conf.betting() as betting:
            betting[min_or_max] = amount
        await ctx.tick()

    @check_global_setting_admin()
    @commands.guild_only()
    @unb_set.group(name="wallet")
    async def wallet_set(self, ctx):
        """Wallet Settings."""

    @check_global_setting_admin()
    @commands.guild_only()
    @wallet_set.command(name="toggle", usage="<on_or_off>")
    async def wallet_toggle(self, ctx, on_or_off: bool):
        """Toggle the wallet system."""
        conf = await self.configglobalcheck(ctx)
        if on_or_off:
            await ctx.send("The wallet and rob system has been enabled.")
        else:
            await ctx.send("The wallet and rob system has been disabled.")
        await conf.disable_wallet.set(on_or_off)
        await ctx.tick()

    @check_global_setting_admin()
    @commands.guild_only()
    @wallet_set.command(name="max")
    async def wallet_max(self, ctx, amount: int):
        """Set the max a wallet can have."""
        conf = await self.configglobalcheck(ctx)
        await conf.wallet_max.set(amount)
        await ctx.tick()

    @check_global_setting_admin()
    @commands.guild_only()
    @unb_set.command(name="failure-rate", usage="<rob | crime> <amount>", aliases=["failurerate"])
    async def failure_set(self, ctx, job: str, amount: int):
        """Set the failure rate for crimes and robbing."""
        if job not in ["rob", "crime"]:
            return await ctx.send("Invalid job.")
        if amount < 50 or amount > 100:
            return await ctx.send("Amount must be higher than 50 or less than 100")
        conf = await self.configglobalcheck(ctx)
        async with conf.failrates() as failrates:
            failrates[job] = amount
        await ctx.tick()

    @check_global_setting_admin()
    @commands.guild_only()
    @unb_set.command(name="fine-rate", usage="<min | max> <amount>", aliases=["finerate"])
    async def fine_set(self, ctx, min_or_max: str, amount: int):
        """Set the min or max fine rate for crimes."""
        if min_or_max not in ["max", "min"]:
            return await ctx.send("You must choose between min or max.")
        conf = await self.configglobalcheck(ctx)
        async with conf.fines() as fines:
            fines[min_or_max] = amount
        await ctx.tick()

    @check_global_setting_admin()
    @commands.guild_only()
    @unb_set.command(name="interest-rate", usage="<amount>", aliases=["interestrate"])
    async def interest_set(self, ctx, amount: int):
        """Set the interest rate if unable to pay a fine from wallet."""
        if amount < 1 or amount > 99:
            return await ctx.send("Amount must be higher than 1 or less than 99")
        await self.config.guild(ctx.guild).interest.set(amount)
        await ctx.tick()

    @commands.guild_only()
    @check_global_setting_admin()
    @unb_set.command(name="add-reply")
    async def add_reply(self, ctx, job, *, reply: str):
        """Add a custom reply for working or crime.

        Put {amount} in place of where you want the amount earned to be.
        """
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        if "{amount}" not in reply:
            return await ctx.send("{amount} must be present in the reply.")
        conf = await self.configglobalcheck(ctx)
        async with conf.replies() as replies:
            jobreplies = {"work": "workreplies", "crime": "crimereplies"}
            if reply in replies[jobreplies[job]]:
                return await ctx.send("That is already a response.")
            replies[jobreplies[job]].append(reply)
            ind = replies[jobreplies[job]].index(reply)
        await ctx.send("Your reply has been added and is reply ID #{}".format(ind))

    @commands.guild_only()
    @check_global_setting_admin()
    @unb_set.command(name="del-reply")
    async def del_reply(self, ctx, job, *, id: int):
        """Delete a custom reply."""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        conf = await self.configglobalcheck(ctx)
        async with conf.replies() as replies:
            jobreplies = {"work": "workreplies", "crime": "crimereplies"}
            if not replies[jobreplies[job]]:
                return await ctx.send("This job has no custom replies.")
            if id > len(replies[jobreplies[job]]):
                return await ctx.send("Invalid ID.")
            replies[jobreplies[job]].pop(id)
        await ctx.send("Your reply has been removed")

    @check_global_setting_admin()
    @commands.guild_only()
    @unb_set.command(name="list-replies")
    async def list_reply(self, ctx, job):
        """List custom replies."""
        if job not in ["work", "crime"]:
            return await ctx.send("Invalid job.")
        conf = await self.configglobalcheck(ctx)
        async with conf.replies() as replies:
            jobreplies = {"work": "workreplies", "crime": "crimereplies"}
            if not replies[jobreplies[job]]:
                return await ctx.send("This job has no custom replies.")
            a = chunks(replies[jobreplies[job]], 10)
            embeds = []
            i = 0
            for item in a:
                items = []
                for strings in item:
                    items.append(f"Reply {i}: {strings}")
                    i += 1
                embed = discord.Embed(colour=discord.Color.red(), description="\n".join(items))
                embeds.append(embed)
            if len(embeds) == 1:
                await ctx.send(embed=embeds[0])
            else:
                await menu(ctx, embeds, DEFAULT_CONTROLS)

    @check_global_setting_admin()
    @commands.guild_only()
    @unb_set.command(name="default-replies", usage="<enable | disable>")
    async def default_replies(self, ctx, enable: bool):
        """Whether to use the default replies to work and crime."""
        conf = await self.configglobalcheck(ctx)
        if enable:
            await ctx.send("Default replies are enabled.")
        else:
            await ctx.send("Default replies are now disabled.")

        await conf.defaultreplies.set(enable)

    @commands.command()
    @commands.guild_only()
    async def cooldowns(self, ctx):
        """List your remaining cooldowns.."""
        conf = await self.configglobalcheck(ctx)
        userconf = await self.configglobalcheckuser(ctx.author)
        cd = await userconf.cooldowns()
        jobcd = await conf.cooldowns()
        if cd["workcd"] is None:
            workcd = "None"
        else:
            time = int(datetime.datetime.utcnow().timestamp()) - cd["workcd"]
            if time < jobcd["workcd"]:
                workcd = humanize_timedelta(seconds=jobcd["workcd"] - time)
            else:
                workcd = "Ready to use."
        if cd["crimecd"] is None:
            crimecd = "Ready to use."
        else:
            time = int(datetime.datetime.utcnow().timestamp()) - cd["crimecd"]
            if time < jobcd["crimecd"]:
                crimecd = humanize_timedelta(seconds=jobcd["crimecd"] - time)
            else:
                crimecd = "Ready to use."
        if await self.walletdisabledcheck(ctx):
            robcd = "Disabled."
        elif cd["robcd"] is None:
            robcd = "Ready to use."
        else:
            time = int(datetime.datetime.utcnow().timestamp()) - cd["robcd"]
            if time < jobcd["robcd"]:
                robcd = humanize_timedelta(seconds=jobcd["robcd"] - time)
            else:
                robcd = "Ready to use."
        msg = "Work Cooldown: `{}`\nCrime Cooldown: `{}`\nRob Cooldown: `{}`".format(
            workcd, crimecd, robcd
        )
        await ctx.maybe_send_embed(msg)

    @unb_set.command()
    @check_global_setting_admin()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def settings(self, ctx):
        """Current unbelievaboat settings."""
        conf = await self.configglobalcheck(ctx)
        data = await conf.all()
        cooldowns = data["cooldowns"]
        workcd = humanize_timedelta(seconds=cooldowns["workcd"])
        robcd = humanize_timedelta(seconds=cooldowns["robcd"])
        crimecd = humanize_timedelta(seconds=cooldowns["crimecd"])
        cooldownmsg = "Work Cooldown: `{}`\nCrime Cooldown: `{}`\nRob Cooldown: `{}`".format(
            workcd, crimecd, robcd
        )
        embed = discord.Embed(colour=ctx.author.colour, title="Unbelievaboat Settings")
        embed.add_field(
            name="Using Default Replies?",
            value="Yes" if data["defaultreplies"] else "No",
            inline=True,
        )
        payouts = data["payouts"]
        crimepayout = f"**Max**: {humanize_number(payouts['crime']['max'])}\n**Min**: {humanize_number(payouts['crime']['min'])}"
        workpayout = f"**Max**: {humanize_number(payouts['work']['max'])}\n**Min**: {humanize_number(payouts['work']['min'])}"
        embed.add_field(name="Work Payouts", value=workpayout, inline=True)
        embed.add_field(name="Crime Payouts", value=crimepayout, inline=True)
        failrates = data["failrates"]
        embed.add_field(
            name="Fail Rates",
            value=f"**Crime**: {failrates['crime']}%\n**Rob**: {failrates['rob']}%\n**Interest Fee**: {data['interest']}%",
            inline=True,
        )
        fines = data["fines"]
        embed.add_field(
            name="Fines",
            value=f"**Max**: {humanize_number(fines['max'])}\n**Min**: {humanize_number(fines['min'])}",
            inline=True,
        )
        embed.add_field(name="Cooldown Settings", value=cooldownmsg, inline=True)
        walletsettings = data["disable_wallet"]
        embed.add_field(
            name="Wallet Settings",
            value="Disabled."
            if not walletsettings
            else f"**Max Balance**: {humanize_number(data['wallet_max'])}\n**Withdraw Cooldown**: {humanize_timedelta(seconds=cooldowns['withdrawcd'])}\n**Deposit Cooldown**: {humanize_timedelta(seconds=cooldowns['depositcd'])}",
            inline=True,
        )
        minbet = humanize_number(data["betting"]["min"])
        maxbet = humanize_number(data["betting"]["max"])
        betstats = f"**Max**: {maxbet}\n**Min**: {minbet}"
        embed.add_field(name="Betting Information", value=betstats)
        roulette = data["roulette_toggle"]
        game_stats = f"**Roulette**: {'Enabled' if roulette else 'Disabled'}"
        embed.add_field(name="Games", value=game_stats)
        await ctx.send(embed=embed)
