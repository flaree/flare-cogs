import aiosmtplib
from email.message import EmailMessage
from redbot.core import Config, commands
import secrets
import discord
import random

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_global(username=None, password=None, verified_emails=[], welcome_messages=[])
        self.config.register_user(code=None, verified=False, email=None, verified_by=None)

    @commands.command()
    @commands.admin()
    async def unverify(self, ctx, *, user: discord.User):
        """Unverify someone"""
        data = await self.config.user(user).all()
        if not data["verified"]:
            return await ctx.send("This user isn't verified.")
        async with self.config.verified_emails() as emails:
            if data["email"] in emails:
                emails.remove(data["email"])
        await self.config.user(user).code.set(None)
        await self.config.user(user).verified.set(False)
        await self.config.user(user).email.set(None)
        await ctx.send("User has been un-verified.")

    @commands.group()
    async def verify(self, ctx):
        """Verification process"""
        pass

    @verify.command(name="email")
    @commands.dm_only()
    async def verify_email(self, ctx, email: str):
        """Verify your DCU email"""
        if not email.lower().endswith("@mail.dcu.ie"):
            return await ctx.send("This doesn't seem to be a valid DCU email.")
        if await self.config.user(ctx.author).verified():
            await ctx.send("You have already been verified.")
            return
        emails = await self.config.verified_emails()
        if email in emails:
            await ctx.send("This email has already been verified.")
            return
        code = secrets.token_hex(3)
        await self.config.user(ctx.author).code.set(code)
        await self.config.user(ctx.author).email.set(email)
        await self.send_email(email, code)
        await ctx.send(
            f"You will recieve an email shortly. Once it arrived you may complete your verification process by typing:\n{ctx.clean_prefix}verify code <code from email>"
        )

    @verify.command(name="code")
    @commands.dm_only()
    async def verify_code(self, ctx, code):
        """Verify the code from your email"""
        usercode = await self.config.user(ctx.author).code()
        verified = await self.config.user(ctx.author).verified()
        if verified:
            await ctx.send("You are already verified.")
            return
        if usercode is None:
            await ctx.send(
                "You haven't started the verification process yet. Get started by invoking the .verify email command."
            )
            return
        if code == usercode:
            verified = await self.config.user(ctx.author).verified.set(True)
            await self.config.user(ctx.author).verified_by.set("System")
            async with self.config.verified_emails() as emails:
                emails.append(await self.config.user(ctx.author).email())
            guild = self.bot.get_guild(713522800081764392)
            role = guild.get_role(713538570824187968)
            user = guild.get_member(ctx.author.id)
            mod, general = self.bot.get_channel(713522800081764395), self.bot.get_channel(713524886840279042)
            greeting_msgs = await self.config.welcome_messages()

            await user.add_roles(
                role,
                reason=f"Automatically verified - Email: {await self.config.user(ctx.author).email()}",
            )
            await ctx.send("Your account has been verified! Head over to <#713791953589764156> to set your course/year!")

            # welcome messages for users

            await mod.send(f"User {user.name} joined the server!", allowed_mentions=discord.AllowedMentions(here=True))
            await general.send(random.choice(greeting_msgs).format(name=user.name))

        else:
            await ctx.send(
                "That code doesn't match the one sent via the email. Try again or request a new code."
            )

    @verify.command(name="external")
    @commands.dm_only()
    async def verify_external(self, ctx, *, message: str):
        """Verification process for external members."""
        verified = await self.config.user(ctx.author).verified()
        if verified:
            await ctx.send("You are already verified.")
            return
        guild = self.bot.get_guild(713522800081764392)
        channel = guild.get_channel(713522800081764395)
        embed = discord.Embed(description=message, colour=discord.Color.red())
        embed.set_author(
            name=f"{ctx.author} | {ctx.author.id}", icon_url=ctx.author.avatar_url)
        await channel.send(embed=embed)
        await ctx.send("Your verification request has been sent.")

    @verify.command()
    @commands.admin()
    async def user(self, ctx, type: str, *, user: discord.Member):
        """Verify a user"""
        if ctx.guild.id != 713522800081764392:
            await ctx.send("This must be used in the CASE++ server.")
        if type.lower() == "external":
            roles = [ctx.guild.get_role(
                713538609017258025), ctx.guild.get_role(713538570824187968)]
        elif type.lower() == "internal":
            roles = [ctx.guild.get_role(713538570824187968)]
        else:
            await ctx.send("Type must be internal or external.")
            return
        await user.add_roles(*roles, reason=f"Manually verified by: {ctx.author}")
        await self.config.user(user).verified_by.set(ctx.author.name)
        await self.config.user(user).verified.set(True)
        await self.config.user(user).email.set(type.title())
        await user.send(f"Your account has been verified on CASE++ by {ctx.author}")
        await ctx.tick()

    @commands.is_owner()
    @commands.command()
    @commands.dm_only()
    async def verifyset(self, ctx, email, password):
        """Credential settings"""
        await self.config.username.set(email)
        await self.config.password.set(password)
        await ctx.tick()

    async def send_email(self, email, code):
        message = EmailMessage()
        message["From"] = "casediscord@gmail.com"
        message["To"] = email
        message["Subject"] = "Discord Verification"
        message.set_content(code)
        await aiosmtplib.send(
            message,
            recipients=[email],
            hostname="smtp.gmail.com",
            port=465,
            username=await self.config.username(),
            password=await self.config.password(),
            use_tls=True,
        )

    @commands.command()
    @commands.admin()
    async def profile(self, ctx, user: discord.Member):
        """Show a users profile information."""
        embed = discord.Embed(color=user.color, title=f"Profile for {user}")
        useri = await self.config.user(user).verified_by()
        verif = await self.config.user(user).verified()
        email = await self.config.user(user).email()
        embed.add_field(name="Verified", value=str(verif))
        if not verif:
            await ctx.send(embed=embed)
            return
        veri_by = useri if useri is not None else "None"
        emaill = email if email is not None else "None"
        embed.add_field(name="Verified By", value=veri_by)
        embed.add_field(name="Email", value=emaill)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.admin()
    async def addwelcomemsg(self, ctx, *, msgtoadd: str):
        """Add welcome message strings to existing list"""

        if "{name}" not in msgtoadd:
            await ctx.send("String must contain the phrase '{name}' to format in place of the users' username.")
            return

        await ctx.send(_("Please confirm that the greeting message is valid with a 'yes' or 'no': \n\n{}".format(msgtoadd))
        try:
            pred = MessagePredicate.yes_or_no(ctx, user=ctx.author)
            await ctx.bot.wait_for("message", check=pred, timeout=20)
        except asyncio.TimeoutError:
            await ctx.send("Exiting operation.")
            return

        if pred.result:
            async with self.config.welcome_messages() as messages:
                messages.append(msgtoadd)

            await ctx.send("Appended greeting message to existing list successfully!")
        else:
            await ctx.send("Operation cancelled.")

