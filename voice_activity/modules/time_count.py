import logging

from types import SimpleNamespace
from collections import defaultdict
from datetime import (
    datetime,
    timedelta,
)

from voice_activity.abc import (
    AbstractCommand,
    AbstractListener,
    AbstractPlugin,
)
from voice_activity.utility import (
    unapply_ctx,
    get_voice_channel,
)
# this unused import is here so that plugin
# autodiscovery discovers storage plugin earlier than
# us as it is our dependency (we use `storage` field created
# by it in our objects).
from voice_activity.modules import storage


LOGGER = logging.getLogger(__name__)


class TimeCountingPlugin(AbstractPlugin):

    def __init__(self, bot, *args, **kwargs):
        if not hasattr(bot, "storage"):
            raise AttributeError("Storage plugin required to use time counting plugin.")
        bot.storage.time_counting = SimpleNamespace()
        storage = bot.storage.time_counting

        storage.tracked_channels = {}
        storage.time_counts = {}

        bot.add_module(TrackChannel)
        bot.add_module(UntrackChannel)
        bot.add_module(ShowStats)
        bot.add_module(ShowTrackedChannels)
        bot.add_module(TimeListener)

class TrackChannel(AbstractCommand):

    def __init__(self, bot):
        super().__init__(bot)
        self.storage = bot.storage.time_counting

    def name(self):
        return "track"

    async def run(self, ctx, channel_name):
        _, guild, resp_chan = unapply_ctx(ctx)
        chan = get_voice_channel(guild, channel_name)
        if chan in self.storage.tracked_channels:
           return await resp_chan.send(f"channel '{channel_name}' is already tracked")
        self.storage.time_counts[chan] = defaultdict(lambda: timedelta(seconds=0))
        self.storage.tracked_channels[chan] = {}
        await resp_chan.send(f"channel {channel_name} is now tracked")


class UntrackChannel(AbstractCommand):

    def __init__(self, bot):
        super().__init__(bot)
        self.storage = bot.storage.time_counting

    def name(self):
        return "untrack"

    async def run(self, ctx, channel_name):
        _, guild, resp_chan = unapply_ctx(ctx)
        chan = get_voice_channel(guild, channel_name)
        if chan not in self.storage.tracked_channels:
           return await resp_chan.send(f"channel '{channel_name}' is not being tracked")
        del self.storage.tracked_channels[chan]
        del self.storage.time_counts[chan]
        await resp_chan.send(f"channel '{channel_name}' was removed from tracking")


class ShowStats(AbstractCommand):

    def __init__(self, bot):
        super().__init__(bot)
        self.storage = bot.storage.time_counting

    def name(self):
        return "track-stats"

    async def run(self, ctx, chan_name):
        _, guild, resp_chan = unapply_ctx(ctx)
        chan = get_voice_channel(guild, chan_name)
        if chan not in self.storage.tracked_channels:
           return await resp_chan.send(f"channel '{chan_name}' is not being tracked")
        stats = self.storage.time_counts[chan]
        msg = f"Stats for channel '{chan_name}':\n\n"
        for user, time in stats.items():
            msg += f"{user.name}: {time}\n"
        msg += "\nThat is all"
        await resp_chan.send(msg)


class ShowTrackedChannels(AbstractCommand):

    def __init__(self, bot):
        super().__init__(bot)
        self.storage = bot.storage.time_counting

    def name(self):
        return "track-channels"

    async def run(self, ctx):
        _, guild, resp_chan = unapply_ctx(ctx)
        msg = "Tracked channels:\n\n"
        for chan in self.storage.tracked_channels:
            msg += f"{chan.name}\n"
        msg += "\nThat's all"
        await resp_chan.send(msg)

class TimeListener(AbstractListener):

    def __init__(self, bot):
        super().__init__(bot)
        self.storage = bot.storage.time_counting

    async def on_voice_state_update(self, mem, bef, aft):
        channel_changed = bef.channel != aft.channel
        LOGGER.debug("TimeLister: Got voice activity for %a", mem.name)
        if not channel_changed:
            LOGGER.debug("%a Channels did not change", mem.name)
            return
        if aft.channel is not None and aft.channel in self.storage.tracked_channels:
            LOGGER.debug("%a Appeared in channel %a", mem.name, aft.channel.name)
            self.storage.tracked_channels[aft.channel][mem] = datetime.utcnow()
        if bef.channel is not None and bef.channel in self.storage.tracked_channels:
            LOGGER.debug("%a Left channel %a", mem.name, bef.channel.name)
            now = datetime.utcnow()
            appeared_at = self.storage.tracked_channels[bef.channel].get(mem, now)
            diff = now - appeared_at
            self.storage.time_counts[bef.channel][mem] += diff
