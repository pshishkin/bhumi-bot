import asyncio
import logging
import random
from decimal import Decimal

import discord

import settings
from crypto import Crypto
from mongo import MongoConnection
from wallet_controller import WalletController

# class MyClient(discord.Client):
#     async def on_ready(self):
#         print(f'Logged in as {self.user} (ID: {self.user.id})')
#         print('------')
#
#     async def on_member_join(self, member):
#         print(f'{member} has joined a server.')
#         guild = member.guild
#         if guild.system_channel is not None:
#             to_send = f'Welcome {member.mention} to {guild.name}!'
#             await guild.system_channel.send(to_send, components=[Button(label="Show Image", style=ButtonStyle.blue)])
#
#
# intents = discord.Intents.default()
# intents.members = True
#
# client = MyClient(intents=intents)
# client.run(settings.DISCORD_TOKEN)

bot = discord.Bot()
wallet_controller = WalletController()
crypto = Crypto()


async def check_balance(interaction):
    wallet = await wallet_controller.get_wallet(interaction.user.id)
    balance = await crypto.get_token_balance(wallet.pubkey)
    print(balance)
    if balance == Decimal(0):
        await interaction.response.send_message(
            f"Пока что на адрес ничего не пришло, попробуй еще раз через 10 секунд.", ephemeral=True,
            view=ViewCheckAgain())
    elif balance < Decimal(13):
        await interaction.response.send_message(f"Вижу на адресе {balance} BHUMI токенов. Этого недостаточно, нужно 13.", ephemeral=True,
                                                view=ViewCheckAgain())
    else:
        role = discord.utils.get(interaction.user.guild.roles, name="Открыватели")
        await interaction.user.add_roles(role)
        await interaction.response.send_message(
            f"Вижу на адресе {balance} BHUMI токенов ✨. Выдаю доступы! Сейчас у тебя появится канал #что-делать, читай его, там все написано.",
            ephemeral=True)


class ViewCheckAgain(discord.ui.View):

    @discord.ui.button(label="Проверить снова", style=discord.ButtonStyle.primary)
    async def button_callback(self, button, interaction):
        await check_balance(interaction)

class ViewIveSent(discord.ui.View): # Create a class called MyView that subclasses discord.ui.View

    @discord.ui.button(label="Отправил", style=discord.ButtonStyle.primary) # Create a button with the label "😎 Click me!" with color Blurple
    async def button_callback(self, button, interaction):
        await check_balance(interaction)



class ViewYesIWant(discord.ui.View): # Create a class called MyView that subclasses discord.ui.View
    @discord.ui.button(label="Хочу!", style=discord.ButtonStyle.primary, emoji="😎") # Create a button with the label "😎 Click me!" with color Blurple
    async def button_callback(self, button, interaction):
        wallet = await wallet_controller.get_wallet(interaction.user.id)
        embed = discord.Embed(
            title=f"{wallet.pubkey}",
            description="Чтобы открыть 13 буми, отправь 13 BHUMI токенов на [адреccс](solana:GwGzxKxeJgvyhi1QNuqWoqE1yTBwAJn84rfDsuCQjPKJ?amount=0.03&memo=muhaha&label=muhaha&message=I%20want%20to%20open%2013%20BHUMI&spl-token=FerpHzAK9neWr8Azn5U6qE4nRGkGU35fTPiCVVKr7yyF) выше.",
            url="solana:GwGzxKxeJgvyhi1QNuqWoqE1yTBwAJn84rfDsuCQjPKJ?amount=0.03&memo=muhaha&label=muhaha&message=I%20want%20to%20open%2013%20BHUMI&spl-token=FerpHzAK9neWr8Azn5U6qE4nRGkGU35fTPiCVVKr7yyF")
        embed.set_image(url="")
        await interaction.response.send_message(
            embed=embed,
            # f"Чтобы открыть 13 буми, отправь 13 BHUMI токенов на адрес {wallet.pubkey}.",
            ephemeral=True, view=ViewIveSent()) # Send a message when the button is clicked

async def first_message(member):
    logging.info(f"Sending first message to {member}")
    guild = member.guild
    if guild.system_channel is not None:
        await guild.system_channel.send(
            f'Привет, {member.mention}! Хочешь открыть 13 буми?', view=ViewYesIWant()
        )

@bot.event
async def on_member_join(member):
    await first_message(member)

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.slash_command(name = "hello", description = "Say hello to the bot")
async def hello(ctx):
    logging.info(f"Sending hello message to {ctx.author}")
    await ctx.respond(f'Привет, {ctx.author.mention}! Хочешь открыть 13 буми?', view=ViewYesIWant())

async def init():
    MongoConnection.initialize()
    await WalletController.initialize()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())
    bot.run(settings.DISCORD_TOKEN) # run the bot with the token