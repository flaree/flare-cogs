import logging
import secrets
from email.message import EmailMessage

import aiosmtplib
import discord
from redbot.core import Config, commands

log = logging.getLogger("red.flare.verifyemail")


class EmailVerify(commands.Cog):

    __version__ = "0.1.1"
    __author__ = "flare"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nCog Author: {self.__author__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_guild(
            email=None, password=None, verified_emails=[], log_channel=None, role=None, domain=None
        )
        self.config.register_member(code=None, verified=False, email=None)

    @commands.command()
    @commands.admin()
    @commands.guild_only()
    async def unverify(self, ctx, *, user: discord.Member):
        """Unverify a user."""
        data = await self.config.member(user).all()
        if not data["verified"]:
            return await ctx.send("This user isn't verified.")
        async with self.config.guild(ctx.guild).verified_emails() as emails:
            if data["email"] in emails:
                emails.remove(data["email"])
        await self.config.member(user).code.set(None)
        await self.config.member(user).verified.set(False)
        await self.config.member(user).email.set(None)
        await ctx.send("User has been un-verified.")

    @commands.group()
    @commands.guild_only()
    async def verify(self, ctx):
        """Verification process"""

    @verify.command(name="email")
    async def verify_email(self, ctx, email: str):
        """Verify your discord account with your email."""
        if await self.config.guild(ctx.guild).role() is None:
            await ctx.send(
                "The server owner must setup a role for this verification method to work."
            )
            return
        if not await self.config.guild(ctx.guild).email():
            await ctx.send(
                "The server owner must setup an email for this verification method to work."
            )
            return

        domain = await self.config.guild(ctx.guild).domain()
        if domain is not None and not email.endswith(domain):
            await ctx.send("Your email does not match the domain this server is setup to use.")
            return

        if await self.config.member(ctx.author).verified():
            await ctx.send("You have already been verified.")
            log_channel = await self.config.guild(ctx.guild).log_channel()
            if log_channel is not None:
                log_channel_obj = ctx.guild.get_channel(log_channel)
                if log_channel_obj is not None:
                    await log_channel_obj.send(
                        f"{ctx.author} with the email {email} has tried to verify with an email that has already been verified."
                    )
            return
        emails = await self.config.guild(ctx.guild).verified_emails()
        if email in emails:
            await ctx.send("This email has already been verified.")
            return
        code = secrets.token_hex(4)
        try:
            await self.send_email(ctx, email, code)
        except Exception as e:
            await ctx.send("There was an error sending the email.")
            log.error("Error in email sending.", exc_info=e)
            return
        await self.config.member(ctx.author).code.set(code)
        await self.config.member(ctx.author).email.set(email)
        await ctx.send(
            f"You will recieve an email shortly. Once it arrives you may complete your verification process by typing:\n`{ctx.clean_prefix}verify code <code from email>`"
        )

    @verify.command(name="code")
    async def verify_code(self, ctx, code):
        """Verify the code from your email"""
        usercode = await self.config.member(ctx.author).code()
        verified = await self.config.member(ctx.author).verified()
        if verified:
            await ctx.send("You are already verified.")
            return
        if usercode is None:
            await ctx.send(
                "You haven't started the verification process yet. Get started by invoking the .verify email command."
            )
            return
        if code == usercode:
            verified = await self.config.member(ctx.author).verified.set(True)
            email = await self.config.member(ctx.author).email()
            async with self.config.guild(ctx.guild).verified_emails() as emails:
                emails.append(email)

            role = await self.config.guild(ctx.guild).role()
            if role is not None:
                role_obj = ctx.guild.get_role(role)
                if role_obj is not None:
                    roles = [role_obj]
                    await ctx.author.add_roles(
                        *roles,
                        reason=f"Automatically verified - Email: {email}",
                    )
                await ctx.send("Your account has been verified!")
                log_channel = await self.config.guild(ctx.guild).log_channel()
                if log_channel is not None:
                    log_channel_obj = ctx.guild.get_channel(log_channel)
                    if log_channel_obj is not None:
                        await log_channel_obj.send(
                            f"{ctx.author} with the email {email} has verified their account."
                        )
                return
            await ctx.send("This server has not set up a role for verification.")
        else:
            await ctx.send(
                "That code doesn't match the one sent via the email. Try again or request a new code."
            )

    @commands.is_owner()
    @commands.group()
    @commands.guild_only()
    async def verifyset(self, ctx):
        """Verification settings."""

    @verifyset.command(name="instructions")
    async def verifyset_instructions(self, ctx):
        """Instructions for verification."""
        await ctx.send(
            "To get started, visit https://myaccount.google.com on the email you wish to use.\n"
            "Click on the 'Security' tab and then click on App Passwords and generate one.\n"
            "Copy the generated code and paste it into the command below.\n"
            f"`{ctx.clean_prefix}verifyset email <email> <app password>`\n\n"
            "NOTE: This leaves your account secure as it bypasses 2FA. Use at your own risk"
        )

    @verifyset.command(name="logchannel")
    async def verifyset_logchannel(self, ctx, channel: discord.TextChannel):
        """Set the channel for verification logs"""
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.tick()

    @verifyset.command(name="role")
    async def verifyset_role(self, ctx, role: discord.Role):
        """Set the role for verification"""
        await self.config.guild(ctx.guild).role.set(role.id)
        await ctx.tick()

    @verifyset.command(name="email")
    async def verifyset_email(self, ctx, email: str, password: str):
        """Set the email for verification."""
        await self.config.guild(ctx.guild).email.set(email)
        await self.config.guild(ctx.guild).password.set(password)
        await ctx.tick()

    @verifyset.command(name="domain")
    async def verifyset_domain(self, ctx, *, domain: str = None):
        """Restrict verification to a specific email domain.

        Example:
        [p]verifyset restrict @mail.dcu.ie

        This will restrict to all @mail.dcu.ie emails"""
        await self.config.guild(ctx.guild).domain.set(domain)
        await ctx.tick()

    async def send_email(self, ctx, email, code):
        message = EmailMessage()
        message["From"] = await self.config.guild(ctx.guild).email()
        message["To"] = email
        message["Subject"] = f"Discord Verification for {ctx.guild}"
        contents = f"Verification Code for {ctx.guild}: {code}"
        message.set_content(contents)
        await aiosmtplib.send(
            message,
            recipients=[email],
            hostname="smtp.gmail.com",
            port=465,
            username=await self.config.guild(ctx.guild).email(),
            password=await self.config.guild(ctx.guild).password(),
            use_tls=True,
        )

    @commands.command()
    @commands.admin()
    async def profile(self, ctx, user: discord.Member):
        """Show a users profile information."""
        embed = discord.Embed(color=user.color, title=f"Profile for {user}")
        verif = await self.config.member(user).verified()
        email = await self.config.member(user).email()
        embed.add_field(name="Verified", value=str(verif))
        if not verif:
            await ctx.send(embed=embed)
            return
        emaill = email if email is not None else "None"
        embed.add_field(name="Email", value=emaill)
        await ctx.send(embed=embed)
