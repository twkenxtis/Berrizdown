import json
import pathlib
import shutil
from collections.abc import Mapping
from typing import IO, Any, Literal, Self

import orjson
from ruamel.yaml import YAML


class Path(type(pathlib.Path())):
    def append_bytes(self, data: bytes, mode: Literal["ab", "wb"] = "ab", encoding: str = "utf-8") -> int:
        """
        將二進製數據附加到檔案末尾
        :param data: 要附加的二進製數據
        :param mode: 檔案開啟模式，預設為 "ab"（附加二進製）
        :param encoding: 檔案編碼（通常在二進製模式下會忽略）
        :return: 寫入的位元組數
        """
        with self.open(mode, encoding=encoding) as fd:
            return fd.write(data)

    def append_line(self, line: str, **kwargs: Any) -> int:
        """
        將一行文字附加到檔案末尾，並自動加上換行符
        :param line: 要附加的文字行
        :param kwargs: 傳遞給 append_text 的額外參數
        :return: 寫入的字元數
        """
        return self.append_text(f"{line}\n")

    def append_text(
        self,
        text: str,
        mode: Literal["a", "a+", "w", "w+"] = "a",
        encoding: str = "utf-8",
    ) -> int:
        """
        將文字附加到檔案末尾
        :param text: 要附加的文字
        :param mode: 檔案開啟模式，預設為 "a"（附加文字）
        :param encoding: 檔案編碼，預設為 "utf-8"
        :return: 寫入的字元數
        """
        with self.open(mode, encoding=encoding) as fd:
            return fd.write(text)

    def format(self, **kwargs: Any) -> Self:
        """
        使用 str.format() 格式化路徑字串後，返回新的 Path 實例
        :param kwargs: 用於格式化路徑字串的關鍵字參數
        :return: 格式化後的新 Path 實例
        """
        return Path(str(self).format(**kwargs))

    def mkdirp(self) -> None:
        """
        遞迴地建立目錄，類似於 mkdir -p，如果目錄已存在則不報錯
        """
        return self.mkdir(parents=True, exist_ok=True)

    def move(self, target: str | pathlib.Path) -> Self:
        """
        移動檔案或目錄，使用 shutil.move，返回移動後的新 Path 實例
        :param target: 目標路徑
        :return: 移動後的新 Path 實例
        """
        return Path(shutil.move(self, target))

    def open(self, mode: str = "r", encoding: str | None = None, **kwargs: Any) -> IO[Any]:
        """
        開啟檔案如果模式不是二進製 (b)，則預設使用 UTF-8 編碼
        :param mode: 檔案開啟模式，預設為 "r"
        :param encoding: 指定編碼如果為 None 且模式不是二進製，則預設為 "utf-8"
        :param kwargs: 傳遞給 pathlib.Path.open 的額外參數
        :return: 檔案物件
        """
        if not encoding and "b" not in mode:
            encoding = "utf-8"
        return super().open(mode, encoding=encoding, **kwargs)

    def read_json(self, missing_ok: bool = False) -> Mapping[str, Any]:
        """
        讀取 JSON 檔案並返回 Python 物件（通常是字典）
        :param missing_ok: 如果檔案不存在，返回空字典 {} 而不是引發 FileNotFoundError
        :return: 載入的 JSON 數據
        :raises FileNotFoundError: 如果檔案不存在且 missing_ok 為 False
        """
        try:
            with self.open() as fd:
                return json.load(fd)
        except FileNotFoundError:
            if missing_ok:
                return {}
            raise

    def read_text(self, encoding: str = "utf-8") -> str:
        """
        讀取檔案內容作為字串，預設使用 UTF-8 編碼
        :param encoding: 檔案編碼，預設為 "utf-8"
        :return: 檔案內容的字串
        """
        return super().read_text(encoding=encoding)

    def read_yaml(self, missing_ok: bool = False) -> Mapping[str, Any]:
        """
        讀取 YAML 檔案首先嘗試路徑加上 .yaml 結尾，然後是 .yml
        :param missing_ok: 如果找不到檔案，返回空字典 {} 而不是引發 FileNotFoundError
        :return: 載入的 YAML 數據
        :raises FileNotFoundError: 如果找不到 .yaml 或 .yml 檔案且 missing_ok 為 False
        """
        yaml_loader = YAML()

        try:
            # 嘗試載入路徑加上 .yaml 結尾的檔案
            # 注意: self 必須是路徑的主幹 (例如 Path('config') 而非 Path('config.yaml'))
            return yaml_loader.load(self.with_suffix(".yaml"))
        except FileNotFoundError:
            try:
                # 嘗試載入路徑加上 .yml 結尾的檔案
                return yaml_loader.load(self.with_suffix(".yml"))
            except FileNotFoundError:
                if missing_ok:
                    return {}
                raise
            except Exception:
                # 處理 ruamel.yaml 可能引發的其他載入錯誤
                raise

    def rmdir(self, missing_ok: bool = False) -> None:
        """
        刪除空目錄如果目錄不存在且 missing_ok 為 True，則不報錯
        :param missing_ok: 如果目錄不存在則忽略錯誤
        """
        try:
            super().rmdir()
        except FileNotFoundError:
            if not missing_ok:
                raise

    def rmtree(self, missing_ok: bool = False) -> None:
        """
        遞迴刪除目錄及其內容 (shutil.rmtree)如果目錄不存在且 missing_ok 為 True，則不報錯
        :param missing_ok: 如果目錄不存在則忽略錯誤
        """
        try:
            return shutil.rmtree(self)
        except FileNotFoundError:
            if not missing_ok:
                raise

    def write_json(self, obj: Mapping[str, Any]) -> None:
        """
        將 Python 物件寫入 JSON 檔案
        :param obj: 要序列化並寫入的 Python 物件
        """
        with self.open("w") as fd:
            json.dump(obj, fd)

    def write_orjson(self, obj: Mapping[str, Any]) -> None:
        """Write a Python mapping object to a JSON file.

        Args:
            obj: A mapping object (e.g., dict) to serialize as JSON
        """
        with self.open("wb") as fd:
            fd.write(orjson.dumps(obj))

    def write_text(self, text: str, encoding: str = "utf-8") -> int:
        """
        將文字內容寫入檔案，預設使用 UTF-8 編碼 (覆蓋原有內容)
        :param text: 要寫入的文字內容
        :param encoding: 檔案編碼，預設為 "utf-8"
        :return: 寫入的字元數
        """
        return super().write_text(text, encoding=encoding)
