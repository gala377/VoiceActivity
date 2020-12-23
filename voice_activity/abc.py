import inspect

from abc import (
    ABC,
    abstractmethod,
)


def _id_conv(x):
    return x

class AbstractCommand(ABC):
    """
    Base class for the bot commands.
    """

    _subclasses = {}

    def __init__(self, bot):
        self._bot = bot

    @abstractmethod
    def name(self) -> str:
        """
        Should return commands name.
        When user sends a string starting with the commands
        name then the corresponding command will be invoked.
        """
        ...

    @abstractmethod
    async def run(self, ctx, *args):
        ...

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        if cls.__name__.startswith("Base"):
            return
        sig = inspect.signature(cls.run)
        if sig.parameters.get('self') is None:
            raise TypeError(
                "Commands `run` function should be an instance method")
        if len(sig.parameters) < 2:
            raise TypeError(
                "Commands `run` method should take at least two arguments, `self` and `ctx`")
        conventers = []
        for (name, param) in sig.parameters.items():
            conv = param.annotation
            if conv is inspect.Signature.empty:
                conv = _id_conv
            conventers.append(conv)
        cls._subclasses[cls] = conventers

        old_run = cls.run
        async def run(self, *args):
            conventers = self._subclasses[self.__class__]
            ctx, *args = args
            if len(conventers)-2 != len(args):
                await ctx['user'].send(
                    "wrong number of arguments, expected {} got {}".format(
                        len(conventers)-2, len(args)))
                return
            try:
                args = [conv(arg) for (conv, arg) in zip(conventers, args)]
            except ValueError as e:
                ctx["user"].send(str(e))
            await old_run(self, ctx, *args)

        cls.run = run

    async def __call__(self, *args):
        await self.run(*args)

    @classmethod
    def subclasses(cls):
        return cls._subclasses.keys()


class AbstractListener(ABC):

    def __init__(self, bot):
        self._bot = bot

    async def on_message(self, message) -> bool:
        return None

    async def on_voice_state_update(self, member, before, after) -> bool:
        return None


class AbstractPlugin(ABC):

    auto_discovery = True

    def __init__(self, bot, *args, **kwargs): ...
