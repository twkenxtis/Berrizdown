from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, Self, TypeVar, cast

P = ParamSpec("P")
R = TypeVar("R")


F = Callable[P, R]


class ParamStore:
    """
    一個全域單例參數儲存庫，提供持久化裝飾器
    """

    _instance: ParamStore | None = None
    _store: dict[str, Any]

    def __new__(cls: type[Self], external_dict: dict[str, Any] | None = None) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store = dict(external_dict) if external_dict else {}
        return cast(Self, cls._instance)

    def __init__(self, external_dict: dict[str, Any] | None = None) -> None:
        pass

    def persist(self, key: str) -> Callable[[F], F]:
        """
        回傳一個裝飾器，用於儲存被裝飾函式的回傳值到內部儲存庫

        :param key: 儲存回傳值的鍵名
        :return: 裝飾器函式
        """

        def decorator(func: F) -> F:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                result: Any = func(*args, **kwargs)
                self._store[key] = result
                return result

            return wrapper

        return decorator

    def get(self, key: str) -> Any | None:
        """
        回傳儲存庫中對應鍵的值如果鍵不存在，則回傳 None
        """
        return self._store.get(key)

    def has(self, key: str) -> bool:
        """
        檢查儲存庫中是否存在指定的鍵
        """
        return key in self._store

    def all(self) -> dict[str, Any]:
        """
        回傳內部儲存庫的一個淺拷貝
        """
        return dict(self._store)


paramstore: ParamStore = ParamStore()
