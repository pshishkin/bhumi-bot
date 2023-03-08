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
import itertools
import logging
import random
from typing import Optional

from telegram import __version__ as TG_VER

import settings
from mongo import MongoConnection
from photo_controller import PhotoController, Photo
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

AWAIT_NAME, AWAIT_SUBSCRIPTION_PREFERENCE, DEFAULT_STATE, AWAIT_PHOTO, AWAIT_MAPPING_COMMENT,\
    AWAIT_PERSON_ON_PHOTO_1, AWAIT_PERSON_ON_PHOTO_2 = range(7)

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


async def send_train_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, photo: Photo) -> None:
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(str(bhumi), callback_data=f"trainmap_{photo.id}_{bhumi}") for bhumi in ['N/A', '0', '1', '2', '3']],
        [InlineKeyboardButton(str(bhumi), callback_data=f"trainmap_{photo.id}_{bhumi}") for bhumi in range(4, 9)],
        [InlineKeyboardButton(str(bhumi), callback_data=f"trainmap_{photo.id}_{bhumi}") for bhumi in range(9, 14)],
    ])
    await update.message.reply_photo(photo=photo.photo_id, caption='Как оценишь?', reply_markup=markup)


async def receive_train_photo_mapping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data.split('_')
    photo_id = data[1]
    bhumi = data[2]

    photo = await photo_controller.get_photo_by_id(photo_id)
    answers = ""
    for mapping in photo.mappings:
        user_name = (await user_controller.get_user(mapping.mapper_id)).name
        mapping_comment = ""
        if mapping.comment:
            mapping_comment = f" ({mapping.comment})"
        answers += f"{user_name}: {mapping.result}{mapping_comment}\n"

    # await query.answer()
    markup = InlineKeyboardMarkup([])

    await query.edit_message_caption(
        caption=f"Ты поставил {bhumi} буми. А вот ответы других:\n{answers}",
        reply_markup=markup,
    )
    return DEFAULT_STATE


def get_photo_collective_mapping(photo: Photo) -> Optional[str]:
    for mapping in photo.mappings:
        if mapping.mapper_id == settings.TRAIN_USER_ID:
            return mapping.result
    return None


async def train01(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Режим обучения. Твоя оценка не будет сохранена, но ты увидишь чужие. Вот два фото одного человека." \
                 "Одно фото 0 буми, другое сколько-то."
    await update.message.reply_text(reply_text)
    photos = await photo_controller.get_photos_for_train()
    groups = []
    for key, group in itertools.groupby(photos, lambda x: "{}-{}".format(x.user_id, x.name)):
        groups.append(list(group))

    random.shuffle(groups)
    for group in groups:
        group = list(group)
        photos0 = [photo for photo in group if get_photo_collective_mapping(photo) == '0']
        photosA = [photo for photo in group if get_photo_collective_mapping(photo) == '1']
        if not photos0 or not photosA:
            continue
        photo0 = random.choice(photos0)
        photoA = random.choice(photosA)
        if random.random() > 0.5:
            await send_train_photo(update, context, photo0)
            await send_train_photo(update, context, photoA)
        else:
            await send_train_photo(update, context, photoA)
            await send_train_photo(update, context, photo0)

        return DEFAULT_STATE
    reply_text = "Не получается найти достаточно фото."
    await update.message.reply_text(reply_text)
    return DEFAULT_STATE


async def train12(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Режим обучения. Твоя оценка не будет сохранена, но ты увидишь чужие. Вот два фото одного человека." \
                 "Одно фото 0 буми, другое сколько-то."
    await update.message.reply_text(reply_text)
    photos = await photo_controller.get_photos_for_train()
    groups = []
    for key, group in itertools.groupby(photos, lambda x: "{}-{}".format(x.user_id, x.name)):
        groups.append(list(group))

    random.shuffle(groups)
    for group in groups:
        group = list(group)
        photos0 = [photo for photo in group if get_photo_collective_mapping(photo) == '1']
        photosA = [photo for photo in group if get_photo_collective_mapping(photo) == '2']
        if not photos0 or not photosA:
            continue
        photo0 = random.choice(photos0)
        photoA = random.choice(photosA)
        if random.random() > 0.5:
            await send_train_photo(update, context, photo0)
            await send_train_photo(update, context, photoA)
        else:
            await send_train_photo(update, context, photoA)
            await send_train_photo(update, context, photo0)

        return DEFAULT_STATE
    reply_text = "Не получается найти достаточно фото."
    await update.message.reply_text(reply_text)
    return DEFAULT_STATE


async def train23(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Режим обучения. Твоя оценка не будет сохранена, но ты увидишь чужие. Вот два фото одного человека." \
                 "Одно фото 0 буми, другое сколько-то."
    await update.message.reply_text(reply_text)
    photos = await photo_controller.get_photos_for_train()
    groups = []
    for key, group in itertools.groupby(photos, lambda x: "{}-{}".format(x.user_id, x.name)):
        groups.append(list(group))

    random.shuffle(groups)
    for group in groups:
        group = list(group)
        photos0 = [photo for photo in group if get_photo_collective_mapping(photo) == '2']
        photosA = [photo for photo in group if get_photo_collective_mapping(photo) == '3']
        if not photos0 or not photosA:
            continue
        photo0 = random.choice(photos0)
        photoA = random.choice(photosA)
        if random.random() > 0.5:
            await send_train_photo(update, context, photo0)
            await send_train_photo(update, context, photoA)
        else:
            await send_train_photo(update, context, photoA)
            await send_train_photo(update, context, photo0)

        return DEFAULT_STATE
    reply_text = "Не получается найти достаточно фото."
    await update.message.reply_text(reply_text)
    return DEFAULT_STATE


async def train0a(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Режим обучения. Твоя оценка не будет сохранена, но ты увидишь чужие. Вот два фото одного человека."
    await update.message.reply_text(reply_text)
    photos = await photo_controller.get_photos_for_train()
    for key, group in itertools.groupby(photos, lambda x: "{}-{}".format(x.user_id, x.name)):
        group = list(group)
        if len(group) < 2:
            continue
        photos = random.choices(group, k=2)
        await send_train_photo(update, context, photos[0])
        await send_train_photo(update, context, photos[1])
        return DEFAULT_STATE
    reply_text = "Не получается найти достаточно фото."
    await update.message.reply_text(reply_text)
    return DEFAULT_STATE


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["last_photo_id"] = update.message.photo[-1].file_id
    reply_text = "Это ты или другой человек?"
    reply_keyboard = [
        ["Я", "Другой"],
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await update.message.reply_text(reply_text, reply_markup=markup)
    return AWAIT_PERSON_ON_PHOTO_1


async def receive_photo_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # markup = ReplyKeyboardMarkup([], one_time_keyboard=True)
    reply_text = "Как зовут человека? Это имя будет видно рядом с фото и результатами маппинга."
    await update.message.reply_text(reply_text)
    return AWAIT_PERSON_ON_PHOTO_2


async def receive_photo_other_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    return await handle_new_photo(update, context, context.user_data["last_photo_id"], name)


async def receive_photo_me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await handle_new_photo(update, context, context.user_data["last_photo_id"], "")


async def handle_new_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, photo_id: str, name: str) -> int:
    object_id = await photo_controller.add_photo(update.message.from_user.id, photo_id, name)
    reply_text = "Спасибо! Твое фото загружено, теперь жди результатов маппинга," \
                 " я буду отправлять тебе каждый новый маппинг."

    await update.message.reply_text(reply_text, reply_markup=default_markup)

    subscribers = await user_controller.get_users_subscribed_to_mapping_requests()

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(str(bhumi), callback_data=f"map_{object_id}_{bhumi}") for bhumi in ['N/A', '0', '1', '2', '3']],
        [InlineKeyboardButton(str(bhumi), callback_data=f"map_{object_id}_{bhumi}") for bhumi in range(4, 9)],
        [InlineKeyboardButton(str(bhumi), callback_data=f"map_{object_id}_{bhumi}") for bhumi in range(9, 14)],
    ])

    user = await user_controller.get_user(update.message.from_user.id)

    person_on_photo_suffix = ""
    if name:
        person_on_photo_suffix = f" ({name})"
    caption = "Новое фото для маппинга от {}{}!".format(user.name, person_on_photo_suffix)
    for chat_id in subscribers:
        await context.bot.send_photo(chat_id=chat_id,
                                     photo=photo_id,
                                     caption=caption,
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
            AWAIT_PERSON_ON_PHOTO_1: [
                MessageHandler(filters.Text(["Я"]), receive_photo_me),
                MessageHandler(filters.Text(["Другой"]), receive_photo_other),
            ],
            AWAIT_PERSON_ON_PHOTO_2: [
                MessageHandler(filters.TEXT, receive_photo_other_name),
            ],
            AWAIT_MAPPING_COMMENT: [
                MessageHandler(filters.TEXT, receive_mapping_comment),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(receive_mapping_result, pattern=r"^map_.*$"),
            CallbackQueryHandler(receive_train_photo_mapping, pattern=r"^trainmap_.*$"),
            CallbackQueryHandler(skip_mapping_comment, pattern=r"^mapcomment_no$"),
            CallbackQueryHandler(ask_mapping_comment, pattern=r"^mapcomment_yes$"),
            application.add_handler(CommandHandler("train01", train01)),
            application.add_handler(CommandHandler("train12", train12)),
            application.add_handler(CommandHandler("train23", train23)),
            application.add_handler(CommandHandler("train0a", train0a)),
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
