import random
import discord
from redbot.core import commands, Config, checks, bank


class Rob(commands.Cog):

    @commands.command()
    @commands.cooldown(rate=1, per=300, type=commands.BucketType.guild)
    async def rob(self, ctx, user: discord.Member):
        """Rob a member for some sweet moola"""
        author = ctx.author
        bal = await bank.get_balance(user)
        bal2 = await bank.get_balance(author)
        currency = await bank.get_currency_name(ctx.guild)
        roll = random.randint(1, 21)
        try:
            if roll > 1 and roll <= 9:
                cred = round(bal2 * 0.25)
                await bank.withdraw_credits(author, cred)
                await ctx.send(
                    f"You try to rob {user} however you dropped your own wallet allowing {user} to pick it up. You lost {cred} {currency} in the process.")
                await bank.deposit_credits(user, cred)
            elif roll > 9 and roll <= 12:
                cred = round(bal2 * 0.02)
                await bank.withdraw_credits(user, cred)
                await ctx.send(
                    f"You sneak up behind {user} and grab the cash out of his hand. Your earned {cred} {currency}.")
                await bank.deposit_credits(author, cred)
            elif roll > 12 and roll <= 17:
                cred = round(bal2 * 0.05)
                await bank.withdraw_credits(user, cred)
                await ctx.send(
                    f"You sneak up behind {user} and pluck the wallet put of his back pocket. Your earned {cred} {currency}.")
                bank.deposit_credits(author, cred)
            elif roll > 17 and roll <= 20:
                cred = round(bal2 * 0.07)
                await bank.withdraw_credits(user, cred)
                await ctx.send(
                    f"You break into {user}'s house and take the car keys lying on the table, you proceed to scrap the car for money. Your earned {cred} {currency}.")
                await bank.deposit_credits(author, cred)
            elif roll == 21:
                cred = round(bal2 * 0.25)
                await bank.withdraw_credits(user, cred)
                await ctx.send(
                    f"You break into {user}'s house and break into the safe, stealing the contents. Your earned {cred} {currency}.")
                await bank.deposit_credits(author, cred)
        except ValueError:
            await ctx.send("You or the target does not have any money to rob, try again on a new target.")
