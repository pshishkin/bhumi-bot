#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
from typing import Dict

from telegram import __version__ as TG_VER

import settings

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

RECEIVE_NAME, RECEIVE_SUBSCRIPTION_PREFERENCE, DEFAULT_STATE, RECEIVE_PHOTO = range(4)


def facts_to_str(user_data: Dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    facts = [f"{key} - {value}" for key, value in user_data.items()]
    return "\n".join(facts).join(["\n", "\n"])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Привет! Это бумибот. Тут ты можешь послать свое фото для маппинга и мапить чужие фото, чтобы " \
                 "тренировать свою чувствительность. Чтобы начать, расскажи как тебя зовут. Это имя будут видеть " \
                 "рядом с твоим фото и результатами маппинга. "
    # await update.message.reply_text(reply_text, reply_markup=markup)
    markup = ReplyKeyboardRemove()
    await update.message.reply_text(reply_text, reply_markup=markup)

    return RECEIVE_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text

    reply_text = "Приятно познакомиться, {}, будщий будда. Ты хочешь получать уведомления о новых фото, загруженных " \
                 "на маппинг? ".format(context.user_data["name"])

    reply_keyboard = [
        ["Да", "Нет"],
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    await update.message.reply_text(reply_text, reply_markup=markup)

    return RECEIVE_SUBSCRIPTION_PREFERENCE


default_reply_keyboard = [
    ["Отправить свое фото"],
    ["Замапить чужое фото"],
]
default_markup = ReplyKeyboardMarkup(default_reply_keyboard, one_time_keyboard=True)


async def receive_notification_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["notification_preference"] = update.message.text

    text = update.message.text.lower()
    if text == 'да':
        context.user_data["subscribed_to_new_photos"] = True
    else:
        context.user_data["subscribed_to_new_photos"] = False

    reply_text = "Отлично, теперь ты можешь отправить свое фото или мапить чужие. "

    await update.message.reply_text(reply_text, reply_markup=default_markup)

    return DEFAULT_STATE


async def default_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Теперь жди новых фото и мапь их или загрузи свое фото."

    await update.message.reply_text(reply_text, reply_markup=default_markup)
    return DEFAULT_STATE


async def ask_for_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Отправь свое фото 🤌"
    await update.message.reply_text(reply_text)
    return RECEIVE_PHOTO


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    # photo_file.download_to_memory()
    reply_text = "Спасибо! Твое фото загружено, теперь жди результатов маппинга, я буду отправлять тебе каждый новый маппинг"

    await update.message.reply_text(reply_text, reply_markup=default_markup)
    return DEFAULT_STATE

# async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Display the gathered info and end the conversation."""
#     if "choice" in context.user_data:
#         del context.user_data["choice"]
#
#     await update.message.reply_text(
#         f"I learned these facts about you: {facts_to_str(context.user_data)}Until next time!",
#         reply_markup=ReplyKeyboardRemove(),
#     )
#     return ConversationHandler.END
#

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    persistence = PicklePersistence(filepath="conversationbot")
    application = Application.builder().token(settings.TELEGRAM_TOKEN).persistence(persistence).build()

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            RECEIVE_NAME: [MessageHandler(filters.TEXT, receive_name)],
            RECEIVE_SUBSCRIPTION_PREFERENCE: [
                MessageHandler(filters.Regex("^(Да|Нет)$"), receive_notification_preference)
            ],
            DEFAULT_STATE: [
                MessageHandler(filters.Text(["Отправить свое фото"]), ask_for_photo),
                MessageHandler(filters.TEXT, default_state)
            ],
            RECEIVE_PHOTO: [
                MessageHandler(filters.PHOTO, receive_photo),
                MessageHandler(filters.TEXT, default_state),
            ],
        },
        fallbacks=[MessageHandler(filters.ALL, default_state)],
        name="my_conversation",
        persistent=True,
    )

    application.add_handler(conv_handler)

    # show_data_handler = CommandHandler("show_data", show_data)
    # application.add_handler(show_data_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()