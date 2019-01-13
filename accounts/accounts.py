from redbot.core import commands, checks, Config
import discord


class Accounts(commands.Cog):
    """All your accounts in one place."""

    def __init__(self):
        self.config = Config.get_conf(
            self, identifier=6234098143, force_registration=True)

        defaults_user = {}
        self.config.register_user(**defaults_user)

    @commands.command()
    async def addaccount(self, ctx, platform: str, name: str):
        """Add an account to your current list."""
        userdata = await self.config.user(ctx.author).all()
        key = platform.capitalize()
        userdata[key] = name
        await self.config.user(ctx.author).set(userdata)
        await ctx.send(
            "Successfully added your {} name: {} to the list of accounts.".format(platform.capitalize(), name))

    @commands.command()
    async def accounts(self, ctx, *, user: discord.Member = None):
        """Show all your accounts."""
        if user is None:
            user = ctx.author
        userdata = await self.config.user(user).all()
        embed = discord.Embed(
            title=f"{user.display_name}'s Accounts", colour=user.color)
        for profile in userdata:
            embed.add_field(name="{}".format(profile), value=userdata["{}".format(profile)], inline=True)
        await ctx.send(embed=embed)
