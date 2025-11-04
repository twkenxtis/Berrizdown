import os
import sqlite3
from pathlib import Path
from typing import Any

from berrizdown.static.route import Route


class SQLiteKeyVault:
    DB_FILE: Path = Route().DB_FILE

    def __init__(self):
        os.makedirs(os.path.dirname(self.DB_FILE), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """初始化數據庫和表結構"""
        with sqlite3.connect(self.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS key_vault (
                    pssh TEXT PRIMARY KEY,
                    kid TEXT NOT NULL,
                    key TEXT NOT NULL,
                    drm_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 創建更新時間的觸發器
            cursor.execute(
                """
                CREATE TRIGGER IF NOT EXISTS update_timestamp
                AFTER UPDATE ON key_vault
                FOR EACH ROW
                BEGIN
                    UPDATE key_vault SET updated_at = CURRENT_TIMESTAMP 
                    WHERE pssh = OLD.pssh;
                END
            """
            )
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """獲取數據庫連接"""
        return sqlite3.connect(self.DB_FILE)

    def _parse_drm_key(self, value: str) -> tuple[str, str]:
        """
        解析 DRM KEY 格式: kid:key
        輸入: KID:KEY
        輸出: (kid, key)
        """
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid DRM key format: {value}. Expected format: kid:key")
        return parts[0].strip(), parts[1].strip()

    def _format_drm_key(self, kid: str, key: str) -> str:
        """
        格式化 DRM KEY: kid:key
        輸入: kid, key
        輸出: HEX_KID:HEX_KEY / 16bytes 32length
        """
        return f"{kid}:{key}"

    def store(self, new_data: dict[str, Any], drm_type: str = "unknown") -> None:
        """
        存儲多個鍵值對，並指定 DRM 類型
        new_data: {pssh: "kid:key", ...}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            for pssh, value in new_data.items():
                # 解析 kid:key 格式
                kid, key = self._parse_drm_key(str(value))

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO key_vault 
                    (pssh, kid, key, drm_type)
                    VALUES (?, ?, ?, ?)
                """,
                    (pssh, kid, key, drm_type),
                )

            conn.commit()

    async def store_single(self, key: str, value: Any, drm_type: str = "unknown") -> None:
        """
        存儲單個鍵值對，並指定 DRM 類型
        key: pssh
        value: "kid:key" 格式
        """
        self.store({key: value}, drm_type)

    async def retrieve(self, key: str) -> Any | None:
        """
        檢索指定鍵的值
        返回: "kid:key" 格式
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT kid, key 
                FROM key_vault WHERE pssh = ?
            """,
                (key,),
            )

            result: tuple[str, str] | None = cursor.fetchone()
            if result:
                return self._format_drm_key(result[0], result[1])
            return None

    def retrieve_with_drm_type(self, key: str) -> tuple[Any, str] | None:
        """
        檢索指定鍵的值和 DRM 類型
        返回: ("kid:key", drm_type)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT kid, key, drm_type 
                FROM key_vault WHERE pssh = ?
            """,
                (key,),
            )

            result: tuple[str, str, str] | None = cursor.fetchone()
            if result:
                drm_key = self._format_drm_key(result[0], result[1])
                return drm_key, result[2]  # 返回值和 DRM 類型
            return None

    def contains(self, key: str) -> bool:
        """檢查鍵是否存在"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM key_vault WHERE pssh = ?", (key,))
            return cursor.fetchone() is not None

    def delete(self, key: str) -> bool:
        """刪除指定鍵"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM key_vault WHERE pssh = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all(self) -> dict[str, Any]:
        """
        獲取所有鍵值對
        返回: {pssh: "kid:key", ...}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT pssh, kid, key 
                FROM key_vault
            """
            )

            results: dict[str, Any] = {}
            for row in cursor.fetchall():
                pssh: str = row[0]
                drm_key: str = self._format_drm_key(row[1], row[2])
                results[pssh] = drm_key

            return results

    def get_all_with_drm_type(self) -> dict[str, tuple[Any, str]]:
        """
        獲取所有鍵值對及其 DRM 類型
        返回: {pssh: ("kid:key", drm_type), ...}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT pssh, kid, key, drm_type 
                FROM key_vault
            """
            )

            results: dict[str, tuple[Any, str]] = {}
            for row in cursor.fetchall():
                pssh: str = row[0]
                drm_key: str = self._format_drm_key(row[1], row[2])
                results[pssh] = (drm_key, row[3])  # 存儲為 (值, DRM 類型)

            return results

    def get_by_drm_type(self, drm_type: str) -> dict[str, Any]:
        """
        根據 DRM 類型獲取鍵值對
        返回: {pssh: "kid:key", ...}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT pssh, kid, key 
                FROM key_vault WHERE drm_type = ?
            """,
                (drm_type,),
            )

            results: dict[str, Any] = {}
            for row in cursor.fetchall():
                pssh: str = row[0]
                drm_key: str = self._format_drm_key(row[1], row[2])
                results[pssh] = drm_key

            return results

    def keys(self) -> list[str]:
        """獲取所有鍵的列表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pssh FROM key_vault")
            return [row[0] for row in cursor.fetchall()]

    def count(self) -> int:
        """獲取鍵值對數量"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM key_vault")
            result: tuple[int] | None = cursor.fetchone()
            return result[0] if result else 0

    def count_by_drm_type(self, drm_type: str) -> int:
        """根據 DRM 類型獲取鍵值對數量"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM key_vault WHERE drm_type = ?", (drm_type,))
            result: tuple[int] | None = cursor.fetchone()
            return result[0] if result else 0
