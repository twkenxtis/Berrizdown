import asyncio

from lib.__init__ import OutputFormatter, dl_folder_name, resolve_conflict_path
from lib.load_yaml_config import CFG
from lib.name_metadata import fmt_dir, meta_name
from lib.path import Path
from static.parameter import paramstore

from unit.__init__ import FilenameSanitizer
from unit.community.community import custom_dict, get_community
from unit.date.date import get_formatted_publish_date
from unit.handle.handle_board_from import BoardFetcher
from unit.handle.handle_log import setup_logging
from unit.image.cache_image_info import CachePublicINFO
from unit.image.parse_public_contexts import IMG_PublicContext

logger = setup_logging("foldermanger", "soft_salmon")


if paramstore.get("savedir") is not None:
    BASEDIR: Path = Path(paramstore.get("savedir")).parent / FilenameSanitizer.sanitize_filename(Path(paramstore.get("savedir")).name)
else:
    BASEDIR: Path = Path.cwd() / Path(dl_folder_name)


class CMTFolderManager:
    """管理社群留言 (Comment) 類型的下載資料夾建立"""

    def __init__(self, input_community_name):
        """
        Args:
            input_community_name (str): 從使用者或上層模組傳入的社群名稱
        """
        self.input_community_name: str = input_community_name
        self._lock = asyncio.Lock()

    async def create_folder(self, folder_name: str, community_id: int) -> tuple[str, str]:
        """
        建立一個唯一的留言資料夾名稱（避免名稱衝突）
        Args:
            folder_name (str): 欲建立的資料夾名稱
            community_id (int): 社群 ID
        Returns:
            tuple[str, str]: (實際建立後的資料夾絕對路徑, community_name)
        """
        try:
            base_dir, community_name = await self.get_base_dir(community_id)
            async with self._lock:
                path = await self._make_unique_dir(base_dir, folder_name)
            return str(path.resolve()), community_name
        except Exception as e:
            logger.error(f"create_folder failed: {e!r}")
            return "Unknown", "Unknown Community"

    async def get_base_dir(self, community_id: int | None) -> tuple[Path, str]:
        """
        根據社群 ID 與自訂名稱決定基礎資料夾路徑

            1. custom_dict 中的自訂名稱
            2. 使用 self.input_community_name
            3. fallback 為 "Unknown Artis"

        Args:
            community_id (int | None): 社群 ID
        Returns:
            tuple[Path, str]: (base_dir, community_name_str)
        Raises:
            ValueError: 若 community_id 存在但查不到名稱
        """
        community_name = None
        if community_id is not None:
            community_name = await get_community(community_id)

        custom_community_name = None
        if community_name is not None:
            custom_community_name = await custom_dict(community_name)

        if custom_community_name:
            cm_folder_name = custom_community_name
        elif getattr(self, "input_community_name", None):
            cm_folder_name = self.input_community_name
        else:
            if community_id is not None and community_name is None:
                logger.warning("Community name not found")
                raise ValueError("Community name is null")
            cm_folder_name = "Unknown Artis"

        if community_name is None:
            community_name_str = "None"
        elif isinstance(community_name, int):
            community_name_str = str(community_name)
        else:
            community_name_str = community_name
        base = BASEDIR / cm_folder_name
        if paramstore.get("nosubfolder"):
            return base, community_name_str
        return base / "CMT", community_name_str

    async def _make_unique_dir(self, base_dir: Path, name: str) -> Path:
        """
        確保資料夾名稱唯一，如有重複則自動附加後綴
        Args:
            base_dir (Path): 基礎目錄
            name (str): 原始資料夾名稱
        Returns:
            Path: 最終建立的資料夾 Path 物件
        """
        if paramstore.get("nodl"):
            return base_dir
        base_dir.mkdirp()
        clean_candidate: Path = await resolve_conflict_path(Path.cwd() / base_dir / name)
        match paramstore.get("nosubfolder"):
            case True:
                return base_dir
            case _:
                clean_candidate.mkdir(exist_ok=False)
                return clean_candidate


class IMGFolderManager:
    """管理圖片 (Images) 相關的資料夾建立"""

    def __init__(
        self,
        _IMG_PublicContext: IMG_PublicContext,
        input_communityname,
    ) -> None:
        """
        Args:
            _IMG_PublicContext (IMG_PublicContext): 圖片上下文資訊解析物件
            input_communityname (str): 社群名稱
        """
        self.IMG_PublicContext: IMG_PublicContext = _IMG_PublicContext
        self.cachepublicINFO: CachePublicINFO = CachePublicINFO(self.IMG_PublicContext, input_communityname)
        self.title: str = FilenameSanitizer.sanitize_filename(self.cachepublicINFO.title)
        self.input_communityname = input_communityname
        self.custom_community_name = self.cachepublicINFO.community_name or input_communityname
        self.base_dir: Path = self.get_base_dir()

    def get_base_dir(self) -> Path:
        """
        根據社群名稱建立圖片基礎路徑
        Returns:
            Path: 基礎資料夾路徑
        """
        if self.custom_community_name is not None:
            cm_folder_name: str = self.custom_community_name
        elif self.input_communityname is not None:
            cm_folder_name: str = self.input_communityname
        else:
            logger.warning("Community name not found, using 'Unknown Artis' instead.")
            cm_folder_name: str = "Unknown Artis"
        cm_folder_name = FilenameSanitizer.sanitize_filename(cm_folder_name)
        match paramstore.get("nosubfolder"):
            case True:
                return BASEDIR / cm_folder_name
            case _:
                return BASEDIR / cm_folder_name / "Images"

    async def create_image_folder(self) -> tuple[Path | None, dict[str, str]]:
        """
        建立圖片資料夾（若已存在則自動添加後綴以確保唯一性）

        Returns:
            tuple[Path | None, dict[str, str]]:
                - 實際建立的資料夾路徑
                - 圖片相關 metadata 字典
        """
        self.base_dir.mkdirp()
        dt: str = get_formatted_publish_date(self.cachepublicINFO.published_at, fmt_dir)
        if self.input_communityname == self.custom_community_name:
            input_communityname: str = self.input_communityname.lower()
        else:
            input_communityname: str = self.input_communityname
        image_meta: dict[str, str] = meta_name(
            dt,
            self.title,
            input_communityname,
            self.custom_community_name,
        )
        folder_name: str = OutputFormatter(f"{CFG['donwload_dir_name']['dir_name']}").format(image_meta)
        match paramstore.get("nosubfolder"):
            case True:
                return self.base_dir, image_meta
            case _:
                data = await self._ensure_unique_folder(folder_name), image_meta
                return data

    async def _ensure_unique_folder(self, folder_name: str) -> Path | None:
        """
        確保圖片資料夾名稱唯一，若不存在則建立

        Args:
            folder_name (str): 資料夾名稱
        Returns:
            Path | None: 已建立的資料夾路徑
        """
        clean_candidate: Path = await resolve_conflict_path(Path.cwd() / self.base_dir / folder_name)
        if not clean_candidate.exists():
            clean_candidate.mkdirp()
            return clean_candidate


class NOTICEFolderManager:
    """管理公告 (Notice) 類型的資料夾建立"""

    def __init__(self, input_community_name):
        """
        Args:
            input_community_name (str): 社群名稱
        """
        self.input_community_name: str = input_community_name
        self._lock = asyncio.Lock()

    async def create_folder(self, folder_name: str, community_id: int) -> tuple[Path | str, str, str]:
        """
        建立公告資料夾

        Args:
            folder_name (str): 資料夾名稱
            community_id (int): 社群 ID
        Returns:
            tuple[Path | str, str, str]:
                - 實際建立的資料夾路徑
                - custom_community_name
                - community_name
        """
        try:
            base_dir, custom_community_name, community_name = await self.get_base_dir(community_id)
            async with self._lock:
                path = await self._make_unique_dir(base_dir, folder_name)
            return str(path.resolve()), custom_community_name, community_name
        except Exception as e:
            logger.error(f"create_folder failed: {e!r}")
            return "Unknown", "Unknown Custom Community", "Unknown Community"

    async def get_base_dir(self, community_id: int) -> tuple[Path, str, str]:
        """
        取得公告下載的基礎資料夾資訊

        Returns:
            tuple[Path, str, str]: (base_path, custom_community_name_str, community_name_str)
        """
        community_name: str | int | None = await get_community(community_id) if community_id is not None else None
        custom_community_name = await custom_dict(community_name) if community_name is not None else None
        if custom_community_name:
            cm_folder_name = custom_community_name
        elif getattr(self, "input_community_name", None):
            cm_folder_name = self.input_community_name
        else:
            logger.warning("Community name not found, using 'Unknown Artis' instead.")
            cm_folder_name = "Unknown Artis"

        cm_folder_name = FilenameSanitizer.sanitize_filename(cm_folder_name)

        community_name_str = "None" if community_name is None else str(community_name)
        custom_community_name_str = "None" if custom_community_name is None else str(custom_community_name)
        base = BASEDIR / cm_folder_name
        match paramstore.get("nosubfolder"):
            case True:
                return base, custom_community_name_str, community_name_str
            case _:
                return base / "Notice", custom_community_name_str, community_name_str

    async def _make_unique_dir(self, base_dir: Path, name: str) -> Path:
        """
        建立唯一的公告資料夾
        Args:
            base_dir (Path): 基礎路徑
            name (str): 資料夾名稱
        Returns:
            Path: 建立後的資料夾 Path
        """
        if paramstore.get("nodl"):
            return base_dir
        base_dir.mkdirp()
        clean_candidate: Path = await resolve_conflict_path(Path.cwd() / base_dir / name)
        match paramstore.get("nosubfolder"):
            case True:
                return base_dir
            case _:
                clean_candidate.mkdir(exist_ok=False)
                return clean_candidate


class POSTFolderManager:
    """管理貼文 (Post) 類型的資料夾建立"""

    def __init__(self, post_media: dict, input_community_name: str):
        """
        Args:
            post_media (dict): 包含貼文內容、社群與 fetcher 資訊
            input_community_name (str): 傳入的社群名稱
        """
        self.post_media: dict = post_media
        self.folder_name: str = FilenameSanitizer.sanitize_filename(post_media["folderName"])
        self.fetcher: BoardFetcher = post_media["fetcher"]
        self.community_name = self.post_media["communityName"]
        self.community_id: int = self.fetcher.get_board_community_id()
        self.input_community_name: str = input_community_name
        self._lock = asyncio.Lock()

    async def create_folder(self) -> tuple[Path, str | None]:
        """
        建立貼文資料夾
        Returns:
            tuple[Path, str | None]: (最終資料夾路徑, custom_community_name)
        """
        base_dir, custom_community_name = await self.get_base_dir()
        if paramstore.get("nodl") is True:
            return base_dir, custom_community_name
        async with self._lock:
            path = await self._make_unique_dir(base_dir)
        return path, custom_community_name

    async def get_base_dir(self) -> tuple[Path, str | None]:
        """
        取得貼文下載的基礎資料夾路徑
        Returns:
            tuple[Path, str | None]: (base_path, custom_community_name)
        """
        custom_community_name = "Unknown Artis"
        if self.community_name is not None:
            custom_community_name = await custom_dict(self.community_name)
        if custom_community_name is not None:
            cm_folder_name: str = custom_community_name
        elif self.input_community_name is not None:
            cm_folder_name: str = self.input_community_name
        else:
            logger.warning("Community name not found, using 'Unknown Artis' instead.")
            cm_folder_name: str = "Unknown Artis"
        cm_folder_name = FilenameSanitizer.sanitize_filename(cm_folder_name)
        match paramstore.get("nosubfolder"):
            case True:
                return (
                    BASEDIR / cm_folder_name,
                    custom_community_name,
                )
            case _:
                return (
                    BASEDIR / cm_folder_name / "Post",
                    custom_community_name,
                )

    async def _make_unique_dir(self, base_dir: Path) -> Path:
        """
        確保貼文資料夾名稱唯一
        Args:
            base_dir (Path): 基礎資料夾
        Returns:
            Path: 已建立資料夾的 Path
        """
        base_dir.mkdirp()
        clean_candidate: Path = await resolve_conflict_path(Path.cwd() / base_dir / self.folder_name)
        match paramstore.get("nosubfolder"):
            case True:
                return base_dir
            case _:
                clean_candidate.mkdirp()
                return clean_candidate
