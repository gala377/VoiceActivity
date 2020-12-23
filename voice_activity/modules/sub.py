import asyncio
import logging

from types import SimpleNamespace
from collections import defaultdict

from voice_activity.abc import (
    AbstractCommand,
    AbstractListener,
    AbstractPlugin,
)


LOGGER = logging.getLogger(__name__)

PER_CHAN_TIMEOUT = 60 # in seconds


class SubPlugin(AbstractPlugin):

    def __init__(self, bot, *args, **kwargs):
        if hasattr(bot, "storage"):
            raise AttributeError("Bot already has storage")
        bot.storage = SimpleNamespace()
        bot.storage._subs = defaultdict(set)
        bot.add_module(SubCommand)
        bot.add_module(UnsubCommand)
        bot.add_module(NotificationListener)


class SubCommand(AbstractCommand):

    def name(self) -> str:
        return "sub"

    async def run(self, ctx, chan):
        user, guild, resp_chan = ctx['user'], ctx['guild'], ctx['resp_chan']
        chan_name = chan
        try:
            [chan] = [ch for ch in guild.voice_channels if ch.name == chan_name]
        except ValueError:
            raise ValueError(f"channel {chan_name} doesn't exist")
        self._bot.storage._subs[chan.id].add(user)
        await resp_chan.send(f"subscribed you to channel {chan.name}")


class UnsubCommand(AbstractCommand):

    def name(self) -> str:
        return "unsub"

    async def run(self, ctx, chan):
        user, guild, resp_chan = ctx['user'], ctx['guild'], ctx['resp_chan']
        try:
            [chan] = [ch for ch in guild.voice_channels if ch.name == chan]
        except ValueError:
            raise ValueError(f"channel {chan} doesn't exist")
        self._bot.storage._subs[chan.id].remove(user)
        await resp_chan.send(f"unsubscribed you from channel {chan.name}")


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
            for user in self._bot.storage._subs[after.channel.id]:
                LOGGER.info("notifying user %s", user.name)
                if user != mem:
                    await user.send(f"Activity started on {after.channel} by {mem.name}")
            asyncio.create_task(self._revoke_timeout(after.channel.id))

    async def _revoke_timeout(self, channel_id):
        await asyncio.sleep(PER_CHAN_TIMEOUT)
        LOGGER.debug("revoking timeout on channel %A", channel_id)
        self._timeouts.remove(channel_id)

