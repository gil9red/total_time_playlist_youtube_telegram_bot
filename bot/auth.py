#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import enum
import functools
import logging
import uuid

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import Filters, CallbackContext, Dispatcher

from bot.common import reply_message, SeverityEnum
from config import USER_NAME_ADMINS, DEFAULT_PASSWORD
from bot.regexp_patterns import (
    PATTERN_GENERATE_RANDOM_PASSWORD,
    PATTERN_CANCEL,
    PATTERN_GET_BOT_PASSWORD,
    PATTERN_SET_BOT_PASSWORD,
)
from third_party.regexp import fill_string_pattern


class StateEnum(enum.Enum):
    TYPING_BOT_PASSWORD = enum.auto()
    TYPING_USER_PASSWORD = enum.auto()


class BotDataEnum(enum.Enum):
    PASSWORD = enum.auto()
    STATE = enum.auto()


def generate_new_password() -> str:
    return str(uuid.uuid4())


if not DEFAULT_PASSWORD:
    DEFAULT_PASSWORD = generate_new_password()


def is_admin(update: Update) -> bool:
    username = update.effective_user.username
    return any(
        username == admin[1:] if admin.startswith("@") else admin
        for admin in USER_NAME_ADMINS
    )


def set_bot_password(
    context_or_dispatcher: CallbackContext | Dispatcher,
    password: str = DEFAULT_PASSWORD,
):
    context_or_dispatcher.bot_data[BotDataEnum.PASSWORD] = password
    context_or_dispatcher.user_data[BotDataEnum.STATE] = None


def get_bot_password(context_or_dispatcher: CallbackContext | Dispatcher) -> str:
    return context_or_dispatcher.bot_data.get(BotDataEnum.PASSWORD)


def set_user_password(
    context_or_dispatcher: CallbackContext | Dispatcher,
    password: str,
):
    context_or_dispatcher.user_data[BotDataEnum.PASSWORD] = password
    context_or_dispatcher.user_data[BotDataEnum.STATE] = None


def get_user_password(context_or_dispatcher: CallbackContext | Dispatcher) -> str:
    return context_or_dispatcher.user_data.get(BotDataEnum.PASSWORD)


def access_check(log: logging.Logger):
    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(update: Update, context: CallbackContext):
            message = update.message
            is_message = bool(update.message)

            user_id = None
            if update.effective_user:
                user_id = update.effective_user.id
            if not user_id:
                reply_message(
                    "Allowed for users only",
                    update, context,
                    severity=SeverityEnum.ERROR,
                )
                return

            state = context.user_data.get(BotDataEnum.STATE)

            if is_admin(update):
                # If need change of password
                if is_message and state == StateEnum.TYPING_BOT_PASSWORD:
                    set_bot_password(context, message.text)
                    text = "Password has successful changed!"
                    reply_message(
                        text, update, context,
                        severity=SeverityEnum.INFO,
                    )

                    return

            elif get_bot_password(context) != get_user_password(context):
                if state is None or not is_message:
                    context.user_data[BotDataEnum.STATE] = StateEnum.TYPING_USER_PASSWORD
                    reply_message(
                        "No access! Enter your password:",
                        update, context,
                        reply_markup=MARKUP_INLINE_SET_USER_PASSWORD,
                        severity=SeverityEnum.ERROR,
                    )

                elif state == StateEnum.TYPING_USER_PASSWORD:
                    # Checking the entered password
                    if get_bot_password(context) != message.text:
                        text = "Invalid password!"
                        reply_message(
                            text, update, context,
                            reply_markup=MARKUP_INLINE_SET_USER_PASSWORD,
                            severity=SeverityEnum.ERROR,
                        )
                        return

                    set_user_password(context, message.text)

                    text = "The password is correct!"
                    log.info(text)

                    reply_message(
                        text, update, context,
                        severity=SeverityEnum.INFO,
                    )

                return

            return func(update, context)

        return wrapper

    return actual_decorator


FILTER_BY_ADMIN = Filters.user(username=USER_NAME_ADMINS)


INLINE_KEYBOARD_BUTTON_CANCEL = InlineKeyboardButton(
    text="🚫 Cancel",
    callback_data=fill_string_pattern(PATTERN_CANCEL),
)

MARKUP_INLINE_SET_BOT_PASSWORD = InlineKeyboardMarkup.from_column(
    [
        InlineKeyboardButton(
            text="✔️ Generate random",
            callback_data=fill_string_pattern(PATTERN_GENERATE_RANDOM_PASSWORD),
        ),
        INLINE_KEYBOARD_BUTTON_CANCEL,
    ]
)
MARKUP_INLINE_SET_USER_PASSWORD = InlineKeyboardMarkup.from_button(
    INLINE_KEYBOARD_BUTTON_CANCEL
)

MARKUP_REPLY_ADMIN = ReplyKeyboardMarkup.from_column(
    [
        fill_string_pattern(PATTERN_GET_BOT_PASSWORD),
        fill_string_pattern(PATTERN_SET_BOT_PASSWORD),
    ],
    resize_keyboard=True,
)
