from collections import abc
from typing import Iterator, Any
from tinydb import where

def identity(val):
    return val


class DefaultDict(abc.MutableMapping):
    def __init__(self, tinydb, default_factory, serializer=identity, deserializer=identity):
        self._client = tinydb
        self._default_factory = default_factory
        self._serializer = serializer
        self._deserializer = deserializer

    def __getitem__(self, key: Any) -> Any:
        values = self._client.search(where('key') == key)
        assert len(values) < 2, (f'More than one value was found for {key}, so either there is a'
                                 f' bug or the TinyDB instance was modified somewhere else')
        try:
            return self._deserializer(values[0]['value'])
        except IndexError as e:
            return self._default_factory()

    def __setitem__(self, key: Any, value: Any):
        self._client.upsert({'key': key, 'value': self._serializer(value)}, where('key') == key)

    def __delitem__(self, key: Any):
        self._client.remove(where('key') == key)

    def __iter__(self) -> Iterator:
        values = self._client.all()
        return iter([v["key"] for v in values])

    def __len__(self) -> int:
        return len(self._client)

    def __repr__(self):
        return f'{self.__class__.__name__}({self._client})'
