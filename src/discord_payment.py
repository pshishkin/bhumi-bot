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
    wallet = await wallet_controller.get_wallet(interaction.user.id, interaction.user.name)
    balance = await crypto.get_token_balance(wallet.pubkey)
    logging.info(f"Balance for {interaction.user.id} is {balance} at wallet {wallet.pubkey}")
    if balance == Decimal(0):
        await interaction.response.send_message(
            f"Пока что на адрес ничего не пришло, попробуй еще раз через 10 секунд.", ephemeral=True,
            view=ViewCheckAgain())
    elif balance < Decimal(13):
        await interaction.response.send_message(f"Вижу на адресе {balance} BHUMI токенов. Этого недостаточно, нужно 13.", ephemeral=True,
                                                view=ViewCheckAgain())
    else:
        role = discord.utils.get(interaction.user.guild.roles, name="Открыватели+")
        await interaction.user.add_roles(role)
        embed = discord.Embed(
            title="Все получилось!",
            description=f"Вижу на адресе {balance} BHUMI токенов ✨. Выдаю доступы!\n\n Теперь у тебя появились новые каналы. \nПрочитай сначала [это сообщение]({settings.DISCORD_INTRO_URL}), мы описали там с чего начать.")
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True)


class ViewCheckAgain(discord.ui.View):

    @discord.ui.button(label="Проверить снова", style=discord.ButtonStyle.primary)
    async def button_callback(self, button, interaction):
        await check_balance(interaction)

class ViewIveSent(discord.ui.View): # Create a class called MyView that subclasses discord.ui.View

    @discord.ui.button(label="Отправил", style=discord.ButtonStyle.primary) # Create a button with the label "😎 Click me!" with color Blurple
    async def button_callback(self, button, interaction):
        await check_balance(interaction)


from urllib.parse import quote

class ViewYesIWant(discord.ui.View): # Create a class called MyView that subclasses discord.ui.View
    @discord.ui.button(label="Хочу!", style=discord.ButtonStyle.primary, emoji="😎") # Create a button with the label "😎 Click me!" with color Blurple
    async def button_callback(self, button, interaction):
        wallet = await wallet_controller.get_wallet(interaction.user.id, interaction.user.name)
        embed = discord.Embed(
            description=f"Чтобы открыть 13 буми, отправь 13 BHUMI токенов на адрес {wallet.pubkey} . Также можешь отсканировать QR код ниже если у тебя уже есть Phantom или другой кошелек для Solana.")
        deeplink = f'solana:{wallet.pubkey}?amount=13&spl-token=FerpHzAK9neWr8Azn5U6qE4nRGkGU35fTPiCVVKr7yyF&message={quote("Хочу открыть 13 буми")}'
        embed.set_image(url=f"http://188.166.55.155:8432/qrcode?data={quote(deeplink)}")
        await interaction.response.send_message(
            f'{wallet.pubkey}',
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
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())
    bot.run(settings.DISCORD_TOKEN) # run the bot with the token