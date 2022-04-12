#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import enum
import functools
import threading
import time

from itertools import cycle

# pip install python-telegram-bot
from telegram import Update, ReplyMarkup, Message, ParseMode
from telegram.ext import CallbackContext
from telegram.error import BadRequest


class ProgressValue(enum.Enum):
    LINES = '|', '/', '-', '\\'
    POINTS = '.', '..', '...'
    MOON_PHASES = '🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘'


class InfinityProgressIndicatorThread(threading.Thread):
    def __init__(
            self,
            text: str,
            message: Message,
            progress_value: ProgressValue = ProgressValue.POINTS,
            parse_mode: ParseMode = None,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.daemon = True

        self._stop = threading.Event()
        self._progress_bar = cycle(progress_value.value)

        self.text = text
        self.message = message
        self.parse_mode = parse_mode

    def run(self):
        while not self.is_stopped():
            text = f'{self.text} {next(self._progress_bar)}'

            try:
                self.message.edit_text(text, parse_mode=self.parse_mode)
            except BadRequest:
                return

            time.sleep(1)

    def stop(self):
        self._stop.set()

    def is_stopped(self) -> bool:
        return self._stop.is_set()


class show_temp_message:
    def __init__(
            self,
            text: str,
            update: Update,
            context: CallbackContext,
            reply_markup: ReplyMarkup = None,
            quote: bool = True,
            parse_mode: ParseMode = None,
            progress_value: ProgressValue = None,
            **kwargs,
    ):
        self.text = text
        self.update = update
        self.context = context
        self.reply_markup = reply_markup
        self.quote = quote
        self.parse_mode = parse_mode
        self.kwargs: dict = kwargs
        self.message: Message = None

        self.progress_value = progress_value
        self.thread_progress: InfinityProgressIndicatorThread = None

    def __enter__(self):
        self.message = self.update.effective_message.reply_text(
            text=self.text,
            reply_markup=self.reply_markup,
            quote=self.quote,
            parse_mode=self.parse_mode,
            **self.kwargs,
        )

        if self.progress_value:
            self.thread_progress = InfinityProgressIndicatorThread(
                text=self.text,
                message=self.message,
                progress_value=self.progress_value,
                parse_mode=self.parse_mode,
            )
            self.thread_progress.start()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.thread_progress:
            self.thread_progress.stop()

        if self.message:
            self.message.delete()


def show_temp_message_decorator(
        text: str = 'In progress...',
        reply_markup: ReplyMarkup = None,
        parse_mode: ParseMode = None,
        progress_value: ProgressValue = None,
        **kwargs,
):
    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(update: Update, context: CallbackContext):
            with show_temp_message(
                text=text,
                update=update,
                context=context,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                progress_value=progress_value,
                **kwargs,
            ):
                return func(update, context)

        return wrapper
    return actual_decorator
