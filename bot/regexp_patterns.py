#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import re


def pattern_to_command(pattern: re.Pattern) -> str:
    pattern = pattern.pattern
    pattern = pattern.strip("^$").lower().replace(" ", "_")
    return pattern


PATTERN_PLAYLIST_ID = re.compile("^playlist_id=(.+)$")
PATTERN_GENERATE_RANDOM_PASSWORD = re.compile("^generate_random_password$")
PATTERN_CANCEL = re.compile("^cancel$")

PATTERN_GET_BOT_PASSWORD = re.compile("^Get bot password$", flags=re.IGNORECASE)
COMMAND_GET_BOT_PASSWORD = pattern_to_command(PATTERN_GET_BOT_PASSWORD)

PATTERN_SET_BOT_PASSWORD = re.compile("^Set bot password$", flags=re.IGNORECASE)
COMMAND_SET_BOT_PASSWORD = pattern_to_command(PATTERN_SET_BOT_PASSWORD)

PATTERN_REMOVE_REPLY_KEYBOARD = re.compile("^Remove reply keyboard$", flags=re.IGNORECASE)
COMMAND_REMOVE_REPLY_KEYBOARD = pattern_to_command(PATTERN_REMOVE_REPLY_KEYBOARD)


if __name__ == "__main__":
    assert pattern_to_command(PATTERN_GET_BOT_PASSWORD) == "get_bot_password"
    assert COMMAND_GET_BOT_PASSWORD == "get_bot_password"
