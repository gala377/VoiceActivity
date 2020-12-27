import os.path
import asyncio
import logging

from tinydb import TinyDB

from voice_activity.abc import (
    AbstractCommand,
    AbstractListener,
    AbstractPlugin,
)
from voice_activity.modules.default_modules import HelpMixin
# this unused import is here so that plugin
# autodiscovery discovers storage plugin earlier than
# us as it is our dependency (we use `storage` field created
# by it in our objects).
from voice_activity.modules import storage
from voice_activity.tinydb_exts.defaultdict import DefaultDict

LOGGER = logging.getLogger(__name__)

PER_CHAN_TIMEOUT = 60  # in seconds


class SubPlugin(AbstractPlugin):

    def __init__(self, bot, *args, config, **kwargs):
        if not hasattr(bot, "storage"):
            raise AttributeError("Storage plugin required to run SubModule")
        if config is None:
            raise AttributeError("Configuration is required")
        db_path = os.path.join(config.data_directory, "subs.db")
        db = TinyDB(db_path)
        bot.storage._subs = DefaultDict(db, set, list, set)

        bot.add_module(SubCommand)
        bot.add_module(UnsubCommand)
        bot.add_module(NotificationListener)


class SubCommand(AbstractCommand, HelpMixin):

    def name(self) -> str:
        return "sub"

    async def run(self, ctx, chan):
        user, guild, resp_chan = ctx['user'], ctx['guild'], ctx['resp_chan']
        chan_name = chan
        try:
            [chan] = [ch for ch in guild.voice_channels if ch.name == chan_name]
        except ValueError:
            raise ValueError(f"channel {chan_name} doesn't exist")

        subs = self._bot.storage._subs[chan.id]
        subs.add(user.id)
        self._bot.storage._subs[chan.id] = subs

        await resp_chan.send(f"subscribed you to channel {chan.name}")

    def description(self):
        return """
            receive a notification when somebody starts
            an activity on the given voice channel
        """


class UnsubCommand(AbstractCommand, HelpMixin):

    def name(self) -> str:
        return "unsub"

    async def run(self, ctx, chan):
        user, guild, resp_chan = ctx['user'], ctx['guild'], ctx['resp_chan']
        try:
            [chan] = [ch for ch in guild.voice_channels if ch.name == chan]
        except ValueError:
            raise ValueError(f"channel {chan} doesn't exist")
        subs = self._bot.storage._subs[chan.id]
        subs.remove(user.id)
        self._bot.storage._subs[chan.id] = subs
        await resp_chan.send(f"unsubscribed you from channel {chan.name}")

    def description(self):
        return "stop receiving notification about given channel"


class NotificationListener(AbstractListener):

    def __init__(self, bot):
        super().__init__(bot)
        self._timeouts = set()

    async def on_voice_state_update(self, mem, bef, after):
        channel_changed = bef.channel != after.channel
        LOGGER.debug("voice state changed for user %s channel changed %s", mem.name, channel_changed)
        if after.channel is None:
            LOGGER.debug("user %s left channel", mem.name)
            return
        if after.channel.id in self._timeouts:
            LOGGER.debug("channel %s is still timed out", after.channel.name)
            return
        if channel_changed and len(after.channel.members) == 1:
            LOGGER.info("%s just joined channel %s(%a)", mem.name, after.channel.name, after.channel.id)
            LOGGER.info("channel members %a", after.channel.members)
            self._timeouts.add(after.channel.id)
            for user_id in self._bot.storage._subs[after.channel.id]:
                user = await mem.guild.fetch_member(user_id)
                LOGGER.info("notifying user %s", user.name)
                if user != mem:
                    await user.send(f"Activity started on {after.channel} by {mem.name}")
            asyncio.create_task(self._revoke_timeout(after.channel.id))

    async def _revoke_timeout(self, channel_id):
        await asyncio.sleep(PER_CHAN_TIMEOUT)
        LOGGER.debug("revoking timeout on channel %a", channel_id)
        self._timeouts.remove(channel_id)
