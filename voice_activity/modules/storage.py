from types import SimpleNamespace

from voice_activity.abc import AbstractPlugin


class StoragePlugin(AbstractPlugin):

    def __init__(self, bot, *args, **kwargs):
        bot.storage = SimpleNamespace()
