import asyncio
import random
import discord

NUMBERS = {
    0: "green",
    1: "red",
    3: "red",
    5: "red",
    7: "red",
    9: "red",
    12: "red",
    14: "red",
    16: "red",
    18: "red",
    19: "red",
    21: "red",
    23: "red",
    25: "red",
    27: "red",
    30: "red",
    32: "red",
    34: "red",
    36: "red",
    2: "black",
    4: "black",
    6: "black",
    8: "black",
    10: "black",
    11: "black",
    13: "black",
    15: "black",
    17: "black",
    20: "black",
    22: "black",
    24: "black",
    26: "black",
    28: "black",
    29: "black",
    31: "black",
    33: "black",
    35: "black",
}

EMOJIS = {"black": "\u2B1B", "red": "\U0001F7E5", "green": "\U0001F7E9"}

COLUMNS = [
    [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34],
    [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
    [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
]
