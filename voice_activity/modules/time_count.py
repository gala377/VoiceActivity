import logging
import os.path
import time

from tinydb import TinyDB
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
from voice_activity.tinydb_exts.defaultdict import DefaultDict
from voice_activity.utility import (
    unapply_ctx,
    get_voice_channel,
)
from voice_activity.modules.default_modules import HelpMixin

# this unused import is here so that plugin
# autodiscovery discovers storage plugin earlier than
# us as it is our dependency (we use `storage` field created
# by it in our objects).
from voice_activity.modules import storage

LOGGER = logging.getLogger(__name__)


class TimeCountingPlugin(AbstractPlugin):

    def __init__(self, bot, *args, config, **kwargs):
        if not hasattr(bot, "storage"):
            raise AttributeError("Storage plugin required to use time counting plugin.")
        if config is None:
            raise AttributeError("Configuration is required")

        db_path = os.path.join(config.data_directory, "time_count.db")
        db = TinyDB(db_path)

        bot.storage.time_counting = SimpleNamespace(
            tracked_channels=DefaultDict(TinyDB.table(db, "tracked_channels"), dict),
            time_counts=DefaultDict(TinyDB.table(db, "time_counts"), lambda: defaultdict(float)),
        )

        bot.add_module(TrackChannel)
        bot.add_module(UntrackChannel)
        bot.add_module(ShowStats)
        bot.add_module(ShowTrackedChannels)
        bot.add_module(TimeListener)


class TrackChannel(AbstractCommand, HelpMixin):

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

    def description(self):
        return """
            start tracking activity time
            on the given voice channel
        """


class UntrackChannel(AbstractCommand, HelpMixin):

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

    def description(self):
        return """
            stop tracking activity time
            on the given channel
        """


class ShowStats(AbstractCommand, HelpMixin):

    def __init__(self, bot):
        super().__init__(bot)
        self.storage = bot.storage.time_counting

    def name(self):
        return "track-stats"

    async def run(self, ctx, chan_name):
        _, guild, resp_chan = unapply_ctx(ctx)
        chan = get_voice_channel(guild, chan_name)
        if chan.id not in self.storage.tracked_channels:
            return await resp_chan.send(f"channel '{chan_name}' is not being tracked")
        stats = self.storage.time_counts[chan.id]
        msg = f"Stats for channel '{chan_name}':\n\n"

        for user_id, tim in stats.items():
            user = await guild.fetch_member(user_id)
            t = time.strftime('%H:%M:%S', time.gmtime(tim))
            msg += f"{user.name}: {t}\n"
        msg += "\nThat is all"
        await resp_chan.send(msg)

    def description(self):
        return """
            show activity time on the given
            voice channel for each user
        """


class ShowTrackedChannels(AbstractCommand, HelpMixin):

    def __init__(self, bot):
        super().__init__(bot)
        self.storage = bot.storage.time_counting

    def name(self):
        return "track-channels"

    async def run(self, ctx):
        _, guild, resp_chan = unapply_ctx(ctx)
        msg = "Tracked channels:\n\n"
        for chan_id in self.storage.tracked_channels:
            chan = guild.get_channel(chan_id)
            msg += f"{chan.name}\n"
        msg += "\nThat's all"
        await resp_chan.send(msg)

    def description(self):
        return "show time-tracked channels"


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
            chan = self.storage.tracked_channels[aft.channel.id]
            chan[str(mem.id)] = datetime.utcnow().timestamp()
            self.storage.tracked_channels[aft.channel.id] = chan

        if bef.channel is not None and bef.channel in self.storage.tracked_channels:
            LOGGER.debug("%a Left channel %a", mem.name, bef.channel.name)
            now = datetime.utcnow().timestamp()
            tracked_chan = self.storage.tracked_channels[bef.channel.id]
            appeared_at = tracked_chan[str(mem.id)]
            diff = now - appeared_at

            chan = self.storage.time_counts[bef.channel.id]
            chan[str(mem.id)] += diff
            self.storage.time_counts[bef.channel.id] = chan
