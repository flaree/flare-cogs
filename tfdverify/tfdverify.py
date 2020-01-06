import discord
from redbot.core import commands, checks


async def tfdcheck(ctx):

    return ctx.guild.id == 410031796105773057


class TFDVerify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.check(tfdcheck)
    @commands.has_any_role(
        "Moderator",
        "Administrator",
        "Assistant Manager",
        "Manager",
        "Pikachu",
        "flare?",
        "Helper",
    )
    @checks.bot_has_permissions(manage_nicknames=True, manage_roles=True)
    @commands.command()
    async def arsenal(self, ctx, user: discord.Member):
        """Verify someone as an Arsenal supporter."""
        name = f"{user.name[:22]} | Arsenal"
        try:
            await user.edit(
                reason="Set {} as an Arsenal supporter. Verified by: {}".format(
                    user.name, ctx.author
                ),
                nick=name,
            )
        except discord.Forbidden:

            await ctx.send("I do not have permission to rename that member.")
        role = ctx.guild.get_role(539097159350484992)
        if role in user.roles:
            return await ctx.send("User is already verified.")
        efl = ctx.guild.get_role(539076954469695491)
        roles = [role, efl]
        await user.add_roles(
            *roles, reason="Verified as an Arsenal supporter. Verified by :{}".format(ctx.author)
        )
        await ctx.tick()

    @commands.check(tfdcheck)
    @commands.has_any_role(
        "Moderator",
        "Administrator",
        "Assistant Manager",
        "Manager",
        "Pikachu",
        "flare?",
        "Helper",
    )
    @checks.bot_has_permissions(manage_nicknames=True, manage_roles=True)
    @commands.command()
    async def liverpool(self, ctx, user: discord.Member):
        """Verify someone as an Liverpool supporter."""
        name = f"{user.display_name[:20]} | Liverpool"
        try:
            await user.edit(
                reason="Set {} as an Liverpool supporter. Verified by: {}".format(
                    user.name, ctx.author
                ),
                nick=name,
            )
        except discord.Forbidden:

            await ctx.send("I do not have permission to rename that member.")
        role = ctx.guild.get_role(588752725144109060)
        if role in user.roles:
            return await ctx.send("User is already verified.")
        efl = ctx.guild.get_role(539076954469695491)
        roles = [role, efl]
        await user.add_roles(
            *roles, reason="Verified as an Liverpool supporter. Verified by :{}".format(ctx.author)
        )
        await ctx.tick()

    @commands.check(tfdcheck)
    @commands.has_any_role(
        "Moderator",
        "Administrator",
        "Assistant Manager",
        "Manager",
        "Pikachu",
        "flare?",
        "Helper",
    )
    @checks.bot_has_permissions(manage_nicknames=True, manage_roles=True)
    @commands.command()
    async def united(self, ctx, user: discord.Member):
        """Verify someone as an United supporter."""
        name = f"{user.display_name[:22]} | Man Utd"
        try:
            await user.edit(
                reason="Set {} as an United supporter. Verified by: {}".format(
                    user.name, ctx.author
                ),
                nick=name,
            )
        except discord.Forbidden:

            await ctx.send("I do not have permission to rename that member.")
        role = ctx.guild.get_role(539101117477421081)
        if role in user.roles:
            return await ctx.send("User is already verified.")
        efl = ctx.guild.get_role(539076954469695491)
        roles = [role, efl]
        await user.add_roles(
            *roles, reason="Verified as an United supporter. Verified by :{}".format(ctx.author)
        )
        await ctx.tick()

    @commands.check(tfdcheck)
    @commands.has_any_role(
        "Moderator",
        "Administrator",
        "Assistant Manager",
        "Manager",
        "Pikachu",
        "flare?",
        "Helper",
    )
    @checks.bot_has_permissions(manage_nicknames=True, manage_roles=True)
    @commands.command()
    async def city(self, ctx, user: discord.Member):
        """Verify someone as an City supporter."""
        name = f"{user.display_name[:21]} | Man City"
        try:
            await user.edit(
                reason="Set {} as an City supporter. Verified by: {}".format(
                    user.name, ctx.author
                ),
                nick=name,
            )
        except discord.Forbidden:

            await ctx.send("I do not have permission to rename that member.")
        role = ctx.guild.get_role(588752838746963999)
        if role in user.roles:
            return await ctx.send("User is already verified.")
        efl = ctx.guild.get_role(539076954469695491)
        roles = [role, efl]
        await user.add_roles(
            *roles, reason="Verified as an City supporter. Verified by :{}".format(ctx.author)
        )
        await ctx.tick()

    @commands.check(tfdcheck)
    @commands.has_any_role(
        "Moderator",
        "Administrator",
        "Assistant Manager",
        "Manager",
        "Pikachu",
        "flare?",
        "Helper",
    )
    @checks.bot_has_permissions(manage_nicknames=True, manage_roles=True)
    @commands.command()
    async def spurs(self, ctx, user: discord.Member):
        """Verify someone as a Spurs supporter."""
        name = f"{user.display_name[:24]} | Spurs"
        try:
            await user.edit(
                reason="Set {} as a Spurs supporter. Verified by: {}".format(
                    user.name, ctx.author
                ),
                nick=name,
            )
        except discord.Forbidden:

            await ctx.send("I do not have permission to rename that member.")
        role = ctx.guild.get_role(568202085233852427)
        if role in user.roles:
            return await ctx.send("User is already verified.")
        efl = ctx.guild.get_role(539076954469695491)
        roles = [role, efl]
        await user.add_roles(
            *roles, reason="Verified as a Spurs supporter. Verified by :{}".format(ctx.author)
        )
        await ctx.tick()

    @commands.check(tfdcheck)
    @commands.has_any_role(
        "Moderator",
        "Administrator",
        "Assistant Manager",
        "Manager",
        "Pikachu",
        "flare?",
        "Helper",
    )
    @checks.bot_has_permissions(manage_nicknames=True, manage_roles=True)
    @commands.command()
    async def chelsea(self, ctx, user: discord.Member):
        """Verify someone as a Chelsea supporter."""
        name = f"{user.display_name[:22]} | Chelsea"
        try:
            await user.edit(
                reason="Set {} as a Chelsea supporter. Verified by: {}".format(
                    user.name, ctx.author
                ),
                nick=name,
            )
        except discord.Forbidden:

            await ctx.send("I do not have permission to rename that member.")
        role = ctx.guild.get_role(539112501959196673)
        if role in user.roles:
            return await ctx.send("User is already verified.")
        efl = ctx.guild.get_role(539076954469695491)
        roles = [role, efl]
        await user.add_roles(
            *roles, reason="Verified as a Chelsea supporter. Verified by :{}".format(ctx.author)
        )
        await ctx.tick()

    @commands.check(tfdcheck)
    @commands.has_any_role(
        "Moderator",
        "Administrator",
        "Assistant Manager",
        "Manager",
        "Pikachu",
        "flare?",
        "Helper",
    )
    @checks.bot_has_permissions(manage_nicknames=True, manage_roles=True)
    @commands.command()
    async def efl(self, ctx, user: discord.Member, *, team: str):
        """Verify someone as an EFL supporter."""
        if len(team) > 20:
            return await ctx.send(
                "Ensure the team lenght is less than 20, otherwise manually verify."
            )
        namelenght = 32 - (len(team) + 3)
        name = f"{user.display_name[:namelenght]} | {team}"
        try:
            await user.edit(
                reason="Set {} as an EFL supporter. Verified by: {}".format(user.name, ctx.author),
                nick=name,
            )
        except discord.Forbidden:

            await ctx.send("I do not have permission to rename that member.")
        role = ctx.guild.get_role(539111785819799578)
        if role in user.roles:
            return await ctx.send("User is already verified.")
        efl = ctx.guild.get_role(539076954469695491)
        roles = [role, efl]
        await user.add_roles(
            *roles, reason="Verified as an EFL supporter. Verified by :{}".format(ctx.author)
        )
        await ctx.tick()

    @commands.check(tfdcheck)
    @commands.has_any_role(
        "Moderator",
        "Administrator",
        "Assistant Manager",
        "Manager",
        "Pikachu",
        "flare?",
        "Helper",
    )
    @checks.bot_has_permissions(manage_nicknames=True, manage_roles=True)
    @commands.command()
    async def other(self, ctx, user: discord.Member, *, team: str):
        """Verify someone."""
        if len(team) > 20:
            return await ctx.send(
                "Ensure the team lenght is less than 20, otherwise manually verify."
            )
        namelenght = 32 - (len(team) + 3)
        name = f"{user.display_name[:namelenght]} | {team}"
        try:
            await user.edit(
                reason="Set {} as a {} supporter. Verified by: {}".format(
                    user.name, team, ctx.author
                ),
                nick=name,
            )
        except discord.Forbidden:

            await ctx.send("I do not have permission to rename that member.")
        role = ctx.guild.get_role(539076954469695491)
        if role in user.roles:
            return await ctx.send("User is already verified.")
        await user.add_roles(
            role, reason="Verified as a {} supporter. Verified by :{}".format(team, ctx.author)
        )
        await ctx.tick()
