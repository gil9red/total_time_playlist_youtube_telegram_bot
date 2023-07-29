#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Dispatcher,
    CallbackContext,
    MessageHandler,
    CommandHandler,
    Filters,
    CallbackQueryHandler,
)

from bot.common import reply_message, log_func, process_error, log, SeverityEnum
from bot.auth import (
    FILTER_BY_ADMIN,
    MARKUP_REPLY_ADMIN,
    MARKUP_INLINE_SET_BOT_PASSWORD,
    is_admin,
    get_bot_password,
    set_bot_password,
    access_check,
    generate_new_password,
    StateEnum,
    BotDataEnum,
)
from bot.regexp_patterns import (
    COMMAND_START,
    COMMAND_HELP,
    PATTERN_PLAYLIST_ID,
    PATTERN_PLAYLIST_ID_WITH_FILTERS,
    PATTERN_GENERATE_RANDOM_PASSWORD,
    PATTERN_CANCEL,
    PATTERN_GET_BOT_PASSWORD,
    PATTERN_SET_BOT_PASSWORD,
    COMMAND_GET_BOT_PASSWORD,
    COMMAND_SET_BOT_PASSWORD,
    COMMAND_REMOVE_REPLY_KEYBOARD,
    PATTERN_REMOVE_REPLY_KEYBOARD,
)
from third_party.auto_in_progress_message import (
    show_temp_message_decorator,
    ProgressValue,
)
from third_party.regexp import fill_string_pattern
from third_party.youtube_com__results_search_query import Playlist, Video, seconds_to_str


def get_description_playlist(
    playlist: Playlist,
    full: bool = True,
    filters: str = None,
) -> str:
    lines = [
        f"Playlist {playlist.title!r}",
        f"Video count: {len(playlist.video_list)}",
    ]

    seq_filters: list[int] = []
    if filters:
        if "," in filters:
            seq_filters += list(map(lambda x: int(x.strip()), filters.split(",")))
        elif "-" in filters:
            start, end = map(int, filters.split("-"))
            seq_filters += list(range(start, end + 1))

    if seq_filters:
        lines.append(f"Filters: {filters}")
    
    total_duration_seconds: int = 0
    video_list: list[Video] = []
    for video in playlist.video_list:
        if seq_filters and video.seq not in seq_filters:
            continue

        video_list.append(video)
        total_duration_seconds += video.duration_seconds

    total_duration_text = seconds_to_str(total_duration_seconds)

    if seq_filters:
        lines.append(f"Filtered video count: {len(video_list)}")

    if full:
        lines.append("Video:")
        for video in video_list:
            lines.append(f"  {video.seq}. {video.title!r} ({video.duration_text})")
        lines.append("")  # Empty line

    lines.append(
        f"Total time: {total_duration_text} ({total_duration_seconds} total seconds)"
    )
    return "\n".join(lines)


def reply_playlist(
    query: str,
    update: Update,
    context: CallbackContext,
    show_full: bool = True,
):
    if " " in query:
        playlist_id_or_url, filters = map(str.strip, query.split(" "))
    else:
        playlist_id_or_url = query
        filters = ""

    try:
        playlist = Playlist.get_from(playlist_id_or_url)
    except:
        text = "Invalid playlist id or url!"

        if is_admin(update):
            log.exception(text)

        reply_message(text, update, context, severity=SeverityEnum.ERROR)
        return

    text = get_description_playlist(playlist, full=show_full, filters=filters)

    if show_full:
        markup = None
    else:
        buttons = [
            InlineKeyboardButton(
                text="Show full playlist",
                callback_data=fill_string_pattern(PATTERN_PLAYLIST_ID, playlist.id),
            )
        ]
        if filters:
            buttons.append(
                InlineKeyboardButton(
                    text="Show filtered playlist",
                    callback_data=fill_string_pattern(
                        PATTERN_PLAYLIST_ID_WITH_FILTERS,
                        playlist.id,
                        filters,
                    ),
                )
            )
        markup = InlineKeyboardMarkup.from_column(buttons)

    reply_message(text, update, context, reply_markup=markup)


@log_func(log)
def on_start(update: Update, context: CallbackContext):
    markup = ReplyKeyboardRemove()
    text = (
        "Bot for displaying the total duration of the youtube playlist.\n\n"
        "Send me an id or link to a playlist (or video with playlist).\n"
        "Examples:\n"
        "    * PLndO6DOY2cLyxQYX7pkDspTJ42JWx07AO\n"
        "    * https://www.youtube.com/playlist?list=PLndO6DOY2cLyxQYX7pkDspTJ42JWx07AO\n"
        "    * https://www.youtube.com/watch?v=4ewTMva83tQ&list=PLndO6DOY2cLyxQYX7pkDspTJ42JWx07AO"
    )
    if is_admin(update):
        text += (
            "\n"
            f"\nUse /{COMMAND_REMOVE_REPLY_KEYBOARD} for remove reply keyboard"
            f"\nUse /{COMMAND_SET_BOT_PASSWORD} for set bot password"
            f"\nUse /{COMMAND_GET_BOT_PASSWORD} for get bot password"
        )
        markup = MARKUP_REPLY_ADMIN

    reply_message(
        text,
        update, context,
        disable_web_page_preview=True,
        reply_markup=markup,
    )


@log_func(log)
def on_get_bot_password(update: Update, context: CallbackContext):
    text = get_bot_password(context)
    reply_message(text, update, context)


@log_func(log)
def on_set_bot_password(update: Update, context: CallbackContext):
    text = "Ok, now enter your new password or select actions below:"

    context.user_data[BotDataEnum.STATE] = StateEnum.TYPING_BOT_PASSWORD

    reply_message(
        text,
        update, context,
        severity=SeverityEnum.INFO,
        reply_markup=MARKUP_INLINE_SET_BOT_PASSWORD,
    )


@log_func(log)
def on_typing_bot_password(update: Update, context: CallbackContext):
    message = update.effective_message

    set_bot_password(context, message.text)
    text = "Password has successful changed!"

    reply_message(text, update, context, severity=SeverityEnum.INFO)


@log_func(log)
@show_temp_message_decorator(
    text=SeverityEnum.INFO.get_text("In progress..."),
    reply_markup=ReplyKeyboardRemove(),
)
def on_remove_reply_keyboard(update: Update, context: CallbackContext):
    time.sleep(1)


@log_func(log)
@access_check(log)
@show_temp_message_decorator(
    text=SeverityEnum.INFO.get_text("In progress {value}"),
    progress_value=ProgressValue.RECTS_SMALL,
)
def on_request(update: Update, context: CallbackContext):
    message = update.effective_message
    reply_playlist(message.text, update, context, show_full=False)


@log_func(log)
@access_check(log)
def on_callback_get_full_playlist(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        query.answer()

    playlist_id = context.match.group(1)
    reply_playlist(playlist_id, update, context, show_full=True)


@log_func(log)
@access_check(log)
def on_callback_get_filtered_playlist(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        query.answer()

    playlist_id, filters = context.match.groups()
    query = f"{playlist_id} {filters}"
    reply_playlist(query, update, context, show_full=True)


@log_func(log)
def on_callback_generate_random_password(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        query.answer()

    password = generate_new_password()
    set_bot_password(context, password)

    text = f"New password: {password}"
    reply_message(
        text, update, context,
        severity=SeverityEnum.INFO,
    )


@log_func(log)
def on_cancel_input_password(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        query.answer()

    context.user_data[BotDataEnum.STATE] = None

    text = "You're canceled input password"
    reply_message(
        text, update, context,
        severity=SeverityEnum.INFO,
    )


def on_error(update: Update, context: CallbackContext):
    process_error(log, update, context)


def setup(dp: Dispatcher):
    set_bot_password(dp)

    dp.add_handler(CommandHandler(COMMAND_START, on_start))
    dp.add_handler(CommandHandler(COMMAND_HELP, on_start))

    dp.add_handler(
        MessageHandler(
            FILTER_BY_ADMIN & Filters.regex(PATTERN_GET_BOT_PASSWORD),
            on_get_bot_password,
        )
    )
    dp.add_handler(
        CommandHandler(COMMAND_GET_BOT_PASSWORD, on_get_bot_password, FILTER_BY_ADMIN)
    )

    dp.add_handler(
        MessageHandler(
            FILTER_BY_ADMIN & Filters.regex(PATTERN_SET_BOT_PASSWORD),
            on_set_bot_password,
        )
    )
    dp.add_handler(
        CommandHandler(COMMAND_SET_BOT_PASSWORD, on_set_bot_password, FILTER_BY_ADMIN)
    )

    dp.add_handler(
        CommandHandler(COMMAND_REMOVE_REPLY_KEYBOARD, on_remove_reply_keyboard)
    )
    dp.add_handler(
        MessageHandler(
            Filters.regex(PATTERN_REMOVE_REPLY_KEYBOARD), on_remove_reply_keyboard
        )
    )

    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_handler(
        CallbackQueryHandler(on_callback_get_full_playlist, pattern=PATTERN_PLAYLIST_ID)
    )
    dp.add_handler(
        CallbackQueryHandler(on_callback_get_filtered_playlist, pattern=PATTERN_PLAYLIST_ID_WITH_FILTERS)
    )
    dp.add_handler(
        CallbackQueryHandler(
            on_callback_generate_random_password,
            pattern=PATTERN_GENERATE_RANDOM_PASSWORD,
        )
    )
    dp.add_handler(
        CallbackQueryHandler(on_cancel_input_password, pattern=PATTERN_CANCEL)
    )

    dp.add_error_handler(on_error)
