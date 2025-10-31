import os
import shutil
from pathlib import Path
from typing import List, Set

# --- 常量定義 ---

# 要忽略（不進入）的黑名單資料夾名稱
# 使用集合(set)可以獲得更快的查找效能
BLACKLIST_DIRS: Set[str] = {".venv", "log", "logs", ".git", "node_modules", ".git"}

# 目標資料夾的名稱
TARGET_DIR_NAME: str = "__pycache__"

# 目標資料夾內唯一允許的副檔名
ALLOWED_EXTENSION: str = ".pyc"


def is_valid_pycache_folder(path: Path) -> bool:
    """
    檢查一個資料夾是否為'純淨'的 __pycache__ 資料夾。
    '純淨'的定義是：裡面只包含 .pyc 檔案，不包含任何子資料夾或其他類型的檔案。

    Args:
        path: 要檢查的資料夾路徑 (Path 物件)。

    Returns:
        如果資料夾內所有內容皆為 .pyc 檔案則返回 True，否則返回 False。
    """
    try:
        if not path.is_dir():
            return False

        for item in path.iterdir():
            # 如果裡面有任何子資料夾，則不符合條件
            if item.is_dir():
                return False
            # 如果裡面的檔案副檔名不是 .pyc，也不符合條件
            if item.is_file() and item.suffix != ALLOWED_EXTENSION:
                return False

        # 如果迴圈正常結束，代表所有內容都符合條件 (或是資料夾為空)
        return True
    except OSError as e:
        print(f"  [警告] 無法存取 {path}: {e}")
        return False


def find_pycache_to_delete(root_dir: Path) -> List[Path]:
    """
    從指定的根目錄開始，遞迴尋找所有符合條件待刪除的 __pycache__ 資料夾。

    Args:
        root_dir: 搜尋的起始目錄。

    Returns:
        一個包含所有符合條件的 Path 物件的列表。
    """
    eligible_folders = []

    # os.walk() 是一個高效的目錄遍歷器
    # topdown=True 允許我們在遍歷過程中修改 dirnames 來排除某些路徑
    for dirpath, dirnames, _ in os.walk(root_dir, topdown=True):

        # --- 黑名單機製 ---
        # 這是 os.walk 的一個重要技巧：
        # 當場修改 dirnames 列表，可以防止 os.walk 進入這些資料夾
        # 必須修改原始列表 (dirnames[:])，而不是賦予一個新列表
        dirnames[:] = [d for d in dirnames if d not in BLACKLIST_DIRS]

        # --- 條件檢查 ---
        if TARGET_DIR_NAME in dirnames:
            pycache_path = Path(dirpath) / TARGET_DIR_NAME

            # 驗證資料夾名稱符合，且內部檔案也符合條件
            print(f"-> 正在檢查: {pycache_path}")
            if is_valid_pycache_folder(pycache_path):
                print(f"  [符合條件] {pycache_path}")
                eligible_folders.append(pycache_path)
            else:
                print(f"  [不符條件] {pycache_path} (內部包含非 .pyc 檔案或子資料夾)")

    return eligible_folders


def main():
    """
    主執行函數
    """
    start_path = Path.cwd()
    print("=" * 60)
    print(f"腳本將從以下目錄開始搜尋：\n{start_path}\n")
    print(f"將會忽略的黑名單資料夾：\n{', '.join(BLACKLIST_DIRS)}")
    print("=" * 60)

    # 1. 取得所有要刪除的資料夾列表
    folders_to_delete = find_pycache_to_delete(start_path)

    # 2. 如果沒有找到任何目標，就提前結束
    if not folders_to_delete:
        print("\n🎉 搜尋完成，沒有找到任何符合條件的 __pycache__ 資料夾需要刪除。")
        return

    # 3. 執行刪除操作前，向使用者確認
    print("\n" + "=" * 60)
    print("🔍 搜尋完成，以下是所有符合條件且將被刪除的資料夾：")
    for folder in folders_to_delete:
        print(f"  - {folder}")
    print("=" * 60)

    # 這是重要的安全機製，防止誤刪
    try:
        confirm = (
            input("\n⚠️ 您確定要永久刪除以上所有資料夾嗎？ [y/N]: ").lower().strip()
        )
    except KeyboardInterrupt:
        print("\n操作已由使用者取消。")
        return

    if confirm not in ("y", "yes"):
        print("\n操作已取消，沒有任何檔案被刪除。")
        return

    # 4. 執行刪除
    print("\n🚀 開始執行刪除操作...")
    deleted_count = 0
    for folder in folders_to_delete:
        try:
            # 使用 shutil.rmtree 可以刪除整個資料夾及其內容
            shutil.rmtree(folder)
            print(f"  ✅ 已成功刪除: {folder}")
            deleted_count += 1
        except OSError as e:
            # 處理可能發生的錯誤，例如權限不足
            print(f"  ❌ 刪除失敗: {folder}")
            print(f"     錯誤原因: {e}")

    print(f"\n✨ 操作完成！總共刪除了 {deleted_count} 個資料夾。")


if __name__ == "__main__":
    main()
