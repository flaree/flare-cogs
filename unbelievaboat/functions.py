import random


def roll():
    roll = random.randint(1, 20)
    if roll == 1:
        return 0.005
    if roll > 1 and roll <= 6:
        return 0.03
    if roll > 6 and roll <= 8:
        return 0.10
    if roll > 8 and roll <= 10:
        return 0.20
    if roll > 10 and roll <= 13:
        return 0.25
    if roll > 13 and roll <= 16:
        return 0.4
    if roll > 16 and roll <= 17:
        return 0.655
    if roll > 17 and roll <= 19:
        return 0.8
    if roll == 20:
        return 0.85


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]
