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
import asyncio
import logging
from typing import Optional

from telegram import __version__ as TG_VER

import settings
from mongo import MongoConnection
from photo_controller import PhotoController
from user_controller import UserController

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
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
    CallbackQueryHandler,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logging.getLogger('hpack').setLevel(logging.INFO)
logger = logging.getLogger(__name__)

AWAIT_NAME, AWAIT_SUBSCRIPTION_PREFERENCE, DEFAULT_STATE, AWAIT_PHOTO, AWAIT_MAPPING_COMMENT = range(5)

default_reply_keyboard = [
    ["Отправить свое фото"],
    ["Замапить чужое фото"],
]
default_markup = ReplyKeyboardMarkup(default_reply_keyboard, one_time_keyboard=True)
user_controller = UserController()
photo_controller = PhotoController()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Привет! Это бумибот. Тут ты можешь послать свое фото для маппинга и мапить чужие фото, чтобы " \
                 "тренировать свою чувствительность. Чтобы начать, расскажи как тебя зовут. Это имя будут видеть " \
                 "рядом с твоим фото и результатами маппинга. "
    # await update.message.reply_text(reply_text, reply_markup=markup)
    markup = ReplyKeyboardRemove()
    await update.message.reply_text(reply_text, reply_markup=markup)

    return AWAIT_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    await user_controller.update_name(update.message.from_user.id, name)

    reply_text = "Приятно познакомиться, {}, будущий будда. Ты хочешь получать уведомления о новых фото, загруженных " \
                 "на маппинг? ".format(name)

    reply_keyboard = [
        ["Да", "Нет"],
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    await update.message.reply_text(reply_text, reply_markup=markup)

    return AWAIT_SUBSCRIPTION_PREFERENCE


async def receive_notification_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["notification_preference"] = update.message.text

    text = update.message.text.lower()
    if text == 'да':
        await user_controller.update_mapping_request_subscription(update.message.from_user.id, True)
    else:
        await user_controller.update_mapping_request_subscription(update.message.from_user.id, False)

    reply_text = "Отлично, теперь ты можешь отправить свое фото или мапить чужие. " \
                 "Для этого нажми на одну из кнопок ниже. "

    await update.message.reply_text(reply_text, reply_markup=default_markup)

    return DEFAULT_STATE


async def default_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Ты можешь загрузить свое фото для маппинга или замапить чужие. " \
                 "Для этого нажми на одну из кнопок ниже."

    await update.message.reply_text(reply_text, reply_markup=default_markup)
    return DEFAULT_STATE


async def ask_for_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Отправь свое фото 🤌"
    await update.message.reply_text(reply_text)
    return AWAIT_PHOTO


async def map_new_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Новых фото еще нет"
    await update.message.reply_text(reply_text, reply_markup=default_markup)
    return DEFAULT_STATE


# async def train(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     reply_text = "Режим обучения. Твоя оценка не будет сохранена, но ты увидишь чужие."
#     markup = InlineKeyboardMarkup([
#         [InlineKeyboardButton("показать фото", callback_data=f"trainmenu_next")],
#         [InlineKeyboardButton("закончить обучение", callback_data=f"trainmenu_next")],
#     ])
#     await update.message.reply_text(reply_text, reply_markup=markup)
#     return DEFAULT_STATE


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_id = update.message.photo[-1].file_id
    object_id = await photo_controller.add_photo(update.message.from_user.id, photo_id)
    reply_text = "Спасибо! Твое фото загружено, теперь жди результатов маппинга, я буду отправлять тебе каждый новый маппинг"

    await update.message.reply_text(reply_text, reply_markup=default_markup)

    subscribers = await user_controller.get_users_subscribed_to_mapping_requests()

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(str(bhumi), callback_data=f"map_{object_id}_{bhumi}") for bhumi in ['N/A', '0', '1', '2', '3']],
        [InlineKeyboardButton(str(bhumi), callback_data=f"map_{object_id}_{bhumi}") for bhumi in range(4, 9)],
        [InlineKeyboardButton(str(bhumi), callback_data=f"map_{object_id}_{bhumi}") for bhumi in range(9, 14)],
    ])

    user = await user_controller.get_user(update.message.from_user.id)

    for chat_id in subscribers:
        await context.bot.send_photo(chat_id=chat_id,
                                     photo=photo_id,
                                     caption="Новое фото для маппинга от {}!".format(user.name),
                                     reply_markup=markup)

    return DEFAULT_STATE


async def receive_mapping_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split('_')
    photo_id = data[1]
    bhumi = data[2]

    context.user_data["last_mapped_photo"] = photo_id
    context.user_data["last_mapped_result"] = bhumi

    # await query.answer()
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('добавить комментарий (рекомендуется)', callback_data=f"mapcomment_yes")],
        [InlineKeyboardButton('пропустить комментарий', callback_data=f"mapcomment_no")],
    ])

    await query.edit_message_caption(
        caption=f"Фото замаплено на {bhumi} буми. Что насчет комментария?",
        reply_markup=markup,
    )
    return DEFAULT_STATE


async def handle_new_mapping(update: Update, context: ContextTypes.DEFAULT_TYPE, mapper_id: int,  photo_id: str, bhumi: str, comment: Optional[str]):
    mapper = await user_controller.get_user(mapper_id)
    owner = await photo_controller.get_photo_sender(photo_id)
    await photo_controller.update_mapping_result(photo_id, mapper_id, bhumi, comment)

    await context.bot.send_message(chat_id=mapper_id, text="Оценка сохранена, удачи!", reply_markup=default_markup)
    text = f"{mapper.name} отмапил твое фото.\nБуми: {bhumi}."
    if comment:
        text += f"\nКомментарий: {comment}"
    await context.bot.send_message(chat_id=owner, text=text)
    return DEFAULT_STATE


async def skip_mapping_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_reply_markup(None)
    return await handle_new_mapping(
        update,
        context,
        update.callback_query.from_user.id,
        context.user_data["last_mapped_photo"],
        context.user_data["last_mapped_result"],
        None
    )


async def ask_mapping_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_reply_markup(None)
    await context.bot.send_message(
        chat_id=update.callback_query.from_user.id,
        text="Напиши комментарий. Например, чувствую пустотность в матке.",
        reply_markup=None
    )
    return AWAIT_MAPPING_COMMENT


async def receive_mapping_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await handle_new_mapping(
        update,
        context,
        update.message.from_user.id,
        context.user_data["last_mapped_photo"],
        context.user_data["last_mapped_result"],
        update.message.text
    )


async def init():
    MongoConnection.initialize()
    await UserController.initialize()
    await PhotoController.initialize()


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    persistence = PicklePersistence(filepath="conversationbot")
    application = Application.builder().token(settings.TELEGRAM_TOKEN).persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT, start),
        ],
        states={
            AWAIT_NAME: [MessageHandler(filters.TEXT, receive_name)],
            AWAIT_SUBSCRIPTION_PREFERENCE: [
                MessageHandler(filters.Regex("^(Да|Нет)$"), receive_notification_preference)
            ],
            DEFAULT_STATE: [
                CommandHandler("start", start),
                MessageHandler(filters.Text(["Отправить свое фото"]), ask_for_photo),
                MessageHandler(filters.Text(["Замапить чужое фото"]), map_new_photo),
                MessageHandler(filters.TEXT, default_state),
            ],
            AWAIT_PHOTO: [
                MessageHandler(filters.PHOTO, receive_photo),
                MessageHandler(filters.TEXT, default_state),
            ],
            AWAIT_MAPPING_COMMENT: [
                MessageHandler(filters.TEXT, receive_mapping_comment),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(receive_mapping_result, pattern=r"^map_.*$"),
            CallbackQueryHandler(skip_mapping_comment, pattern=r"^mapcomment_no$"),
            CallbackQueryHandler(ask_mapping_comment, pattern=r"^mapcomment_yes$"),
            # application.add_handler(CommandHandler("train", train)),
            MessageHandler(filters.ALL, default_state)
        ],
        name="my_conversation",
        persistent=True,
    )

    application.add_handler(conv_handler)

    # show_data_handler = CommandHandler("show_data", show_data)
    # application.add_handler(show_data_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())
    main()
