import aiosmtplib
from email.message import EmailMessage
from redbot.core import Config, commands
import secrets
import discord


class Verify(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=95932766180343808, force_registration=True)
        self.config.register_global(username=None, password=None, verified_emails=[])
        self.config.register_user(code=None, verified=False, email=None)

    @commands.command()
    @commands.admin()
    async def unverify(self, ctx, *, user: discord.User):
        """Unverify someone"""
        data = await self.config.user(user).all()
        if not data["verified"]:
            return await ctx.send("This user isn't verified.")
        async with self.config.verified_emails() as emails:
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
        if not email.endswith("@mail.dcu.ie"):
            return await ctx.send("This doesn't seem to be a valid DCU email.")
        emails = await self.config.verified_emails()
        if email in emails:
            await ctx.send("This email has already been verified.")
            return
        code = secrets.token_hex(3)
        await self.config.user(ctx.author).code.set(code)
        await self.config.user(ctx.author).email.set(email)
        await self.send_email(email, code)
        await ctx.send(f"You will recieve an email shortly. Once it arrived you may complete your verification process by typing:\n{ctx.clean_prefix}verify code <code from email>")

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
            await ctx.send("You haven't started the verification process yet. Get started by invoking the .verify email command.")
            return
        if code == usercode:
            verified = await self.config.user(ctx.author).verified.set(True)
            async with self.config.verified_emails() as emails:
                emails.append(await self.config.user(ctx.author).email())
            guild = self.bot.get_guild(713522800081764392)
            role = guild.get_role(713538570824187968)
            user = guild.get_member(ctx.author.id)
            await user.add_roles(role)
            await ctx.send("Your account has been verified!")
        else:
            await ctx.send("That code doesn't match the one sent via the email. Try again or request a new code.")

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
        use_tls=True
        )
