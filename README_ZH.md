<p align="center">
    <img width="32" height="48" alt="berriz_ico" src="https://github.com/twkenxtis/Berriz-Media-pass/blob/main/berriz-extension-chrome/assets/icons/berry512.png" />
    <br/>
      <sup><em><a href="https://github.com/twkenxtis/Berrizdown/blob/main/README.md">ENG</a></em></sup>
    <sup><strong>A command-line app for downloading Berriz video, photo post and comment notice</strong></sup>
</p>

# Berrizdown
* **輕鬆安裝** \- UV 支持
* **多種畫質** \- DASH/HLS 兩種協議支持
* **DRM** \- 內建 Widevine and PlayReady
* **Key** \- 遠程 CDM or 本地 Key 資料庫
* **持久化** \- 支持使用Cookie或直接登入
* **自訂** \- YAML\-豐富設定
* **自動化** \- 互動式選單或使用網址快速自動輸入並檢測
* **Log** \- 自動跳過已經下載過的項目
* **字幕** \- 支持下載Berriz AI字幕

![DEMO](https://github.com/twkenxtis/Berrizdown/blob/main/dmeo.gif)

# 快速開始
```
git clone https://github.com/twkenxtis/Berrizdown
cd Berrizdown
uv sync
uv run berrizdown -?
```
# 代理加速下快速开始
```
git clone --depth=1 https://githubfast.com/twkenxtis/Berrizdown
cd Berrizdown
uv sync --index https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
打开berrizdown档案夹中的 berrizconfig.yaml 编辑设定， ctrl+F 搜索 Proxy_Enable
调整成 true 并设定本地http(s)代理
uv run berrizdown -?
```


# 必要條件
#### Python 3.11 或更新版本
- UV 需要在您的系統上安裝
    [UV](https://docs.astral.sh/uv/getting-started/installation/)
    到UV官網查看詳細資訊
    ```
    Windows:
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    Mac and Linux:
    curl -LsSf https://astral.sh/uv/install.sh | sh

    wget -qO- https://astral.sh/uv/install.sh | sh
    ```

> [!NOTE]
> 確保完整閱讀 YAML 配置文件
> berrizdown檔案夾內的`berrizconfig.yaml`, berrizconfig.example.yaml為預設值和參考
- **YAML Config** \- 編輯 `berrizconfig.yaml` 檔案來確保你的客製設定


#### FFmpeg 需求只有在需要下載影片
將 ffmpeg 放到 `berrizdown\\lib\\tools` 和ffmpeg檔名寫入 `berrizconfig.yaml` 或 `ffmpeg` 已經在系統環境變數
- Windows: [AnimMouse's FFmpeg Builds](https://github.com/AnimMouse/ffmpeg-stable-autobuild/releases)
- Linux: [John Van Sickle's FFmpeg Builds](https://johnvansickle.com/ffmpeg/)

將 ffprobe 放到 `berrizdown\\lib\\tools` 和ffprobe檔名寫入 `berrizconfig.yaml` 或 `ffprobe` 已經在系統環境變數



# Cookie / Login

> ⚠️ 只有Fanclub和影片才要求Cookie

## Berriz Cookies

從你的瀏覽器導出 **Netscape format** 正常再Berriz登入的 cookie:

- **Firefox**: [Get cookies.txt LOCALLY](https://addons.mozilla.org/en-US/firefox/addon/get-cookies-txt-locally/)
- **Chromium**: [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)

📁 複製 `default.txt` 到 `berrizdown\\cookies\\Berriz` 檔案夾內，確保在複製前重新命名.txt
✅ 腳本只檢測 **default.txt** 並且是 Netscape 格式

---

## Berriz Account Login

使用 **Berriz 帳號 和 密碼** (非 Google/Apple login):

1. 編輯 `[account:password]` 在 `berrizconfig.yaml` 檔案
2. 運行:

   ```
   uv run berrizdown
   ```



### 可選
**mp4decrypt** \- 如果想要使用 `mp4decrypt` 解密 DRM 內容，則需要此檔案 [mp4decrypt](https://www.bento4.com/documentation/mp4decrypt/)
* 將 mp4decrypt 放到 `berrizdown\\lib\\tools` 和在配置文件寫入mp4decrypt的檔名 `berrizconfig.yaml` 

**shaka-packager** \- 如果您想要使用 `shaka-packager` 解密 DRM 內容，則需要此檔案
[shaka-packager](https://github.com/shaka-project/shaka-packager)
* 將 shaka-packager 放到 `berrizdown\\lib\\tools` 和在配置文件寫入shaka-packager的檔名 `berrizconfig.yaml` 或 `shaka-packager` 存在系統環境變數

**mkvmerge** \-\- 使用 `mkvtoolnix` 進行重新封裝需要此工具，或者您也可以選擇僅使用 ffmpeg [mkvtoolnix](https://mkvtoolnix.download/)
* 將 mkvmerge 放到 `berrizdown\\lib\\tools` 和在配置文件寫入mkvmerger的檔名 `berrizconfig.yaml` 或 `mkvmerge` 存在系統環境變數


> [!IMPORTANT]
> 如果終端報錯提示缺少工具 請按造指引添加到路徑中 `berrizdown\\lib\\tools`


## 🧾 Berrizdown CLI 命令參數

| Option(s) | Description |
|-----------|-------------|
| `-h`, `--help`, `-H`, `-?`, `--?` | 顯示此幫助訊息並退出 |
| `-nc`, `--no_cookie`, `--nocookie`, `--no-cookie` | 不使用 Cookies |
| `-cm`, `--community` | 列出 Berriz 中所有社群 |
| `--join 'COMMUNITY_NAME'` | 加入一個社區 |
| `--leave 'COMMUNITY_NAME'` | 離開一個社區 |
| `-g 'ive'`, `--group 7` | 選擇藝人社羣（例如：ive 或 7）— 僅允許一個 |
| *(預設)* | 選擇除評論（CMT）以外的所有項目 |
| `-b`, `--board` | 選擇看板內容 |
| `-c`, `--cmt` | 選擇留言內容 |
| `-l`, `--live`, `--live-only` | 選擇直播內容 |
| `-m`, `--media`, `--media-only` | 選擇media板塊中的上傳影片 |
| `-p`, `--photo`, `--photo-only` | 選擇media板塊中的上傳照片 |
| `-n`, `--notice`, `--notice-only` | 選擇通知板塊內容 |
| `-fc`, `--fanclub-only`, `--fanclub` | 只顯示粉絲俱樂部內容 |
| `-nfc`, `--no-fanclub` | 只顯示非粉絲俱樂部內容 |
| `--T`, `--t <datetime start>` | 過濾內容的開始日期/時間（基於 KST，請使用完整年份如 2025）[ISO8601,YYMMDD,'19970101 00:00'] |
| `--TT`, `--tt <datetime end>` | [可選] 過濾內容的開始日期/時間（基於 KST，請使用完整年份如 2025）[ISO8601,YYMMDD,'19970101 00:00'] |
| `--signup` | 註冊Berriz帳號 |
| `--change-password`, `--changepassword` | 變更當前登入帳號密碼 |
| `-q`, `--quality` | 選擇影片畫質 (`1080p`, `720p`, `480p`, etc.) |
| `-v`, `--vcodec` | 選影片編碼 (e.g., `H264`) |
| `-na`, `-an`, `--no-audio`, `--skip-audio`, `--skip-a`, `--skipaudio` | 跳過下載聲音 |
| `-nv`, `-vn`, `--no-video`, `--skip-videos`, `--skip-v`, `--skip-video`, `--skipvideo` | 跳過下載影像 |
| `--ss` | 指定影片的開始時間 |
| `--to` | 指定影片的結束時間 |
| `--list` | 跳過下載，僅列出所有可用的軌道 |
| `--del-after-done` | 下載後清理切片 (`true`/`false`) |
| `--skip-merge` | 下載後跳過切片合併 |
| `--skip-mux` | 切片合併後跳過多路復用 |
| `-k`, `--key`, `--keys` | 顯示金鑰並跳過下載 |
| `--skip-dl`, `--skip-download` | 跳過所有下載 |
| `--skip-json`, `--skip-Json`, `--skip-JSON`, `--skipjson` | 跳過下載Json到本地 |
| `--skip-thumbnails`, `--skip-thb`, `--skipthumbnails` | 跳過下載縮圖到本地 |
| `--skip-images`, `--skip-imgs`, `--skip-image`, `--skip-img`, `--skipimage` | 跳過下載圖片到本地 |
| `--skip-playlist`, `--skip-Playlist`, `--skip-pl`, `--skipplaylist` | 跳過下載播放列表到本地 |
| `--skip-html`, `--skip-Html`, `--skip-HTML`, `--skiphtml` | 跳過保存HTML到本地 |
| `--no-info`, `--noinfo` | 跳過Json, HTML, Thumbnails, Images, Playlist 的下載 |
| `--nosubfolder`, `--no-subfolder`, `--no_subfolder` | 不要建立任何子資料夾 |
| `--retitle` | 使用正則表達式篩選標題 |
| `--artisid` | 指定Artisid (例如:, `--artisid 71,72,73`) — 只有在0. Artis archive 工作|
| `--cdm` | 指定解密cdm路徑並覆蓋設定值 |
| `--cache` | 只使用本地Key資料庫解密 |
| `--no-cache` | 只使用cdm解密 |
| `--save-dir` | 指定下載的檔案夾路徑並覆蓋原始設定值 |
| `-S`, `--subs-only` | 只下載字幕 |
| `-ns`, `--no-subs` | 跳過下載字幕 |
| `--version`, `--v` | 顯示版本 |





# example
- 從 URL 下載（接收以逗號、空格或不以任何方式分隔的 URL[str]）
    ```
    uv run berrizdown https://link.berriz.in/web/main/jsh/live/replay/019681ce-aa41-6af0-b423-1c1cc6894bc5/https://berriz.in/en/jsh/live/replay/019681ce-aa41-6af0-b423-1c1cc6894bc5/https://berriz.in/applink/web/jsh/live/replay/019681ce-aa41-6af0-b423-1c1cc6894bc5/
    ```

- 下載 IU 直播回放（-g 5、-g IU、-g iu）並下載直播開始時間從 60:00 至 70:00
    ```
    uv run berrizdown -g 5 -l --ss 60:00 --to 70:00
    ```

- 下載 IVE 直播重播（-g 7、-g Ive、-g IVE），下載 720p 版本，設定 noinfo 參數僅下載影片
    ```
    uv run berrizdown -g 5 -l -q 720 --no-info
    ```

- 下載 JSH 直播回放（-g 1，-g jsh），並使用 --cdm 參數覆蓋用於解密的 CDM 設定
    ```
    uv run berrizdown -g jsh -l --cdm "path\\my_cdm\\cdm.wvd|prd"
    ```

- 下載 KiiiKiii 直播回放（-g 2，-g kiiiikiii），使用 --nosubfolder 參數避免每個內容建立額外的子資料夾，然後使用 -vn 參數僅顯示音訊
    ```
    uv run berrizdown -g jsh -l --nosubfolder -vn
    ```

- 下載 IU 媒體檔案（-g 5、-g IU、-g iu），並使用 --skip-mux 參數跳過合併後的複用操作
    ```
    uv run berrizdown -g iu -m --skip-mux
    ```

- 下載 IVE Media（-g 7，-g ive），並使用 --fanclub 參數僅顯示粉絲俱樂部成員才能觀看的內容
    ```
    uv run berrizdown -g ive -m -p --fanclub
    ```

- 下載 IU Media 文件，完成後使用 `--skip-merge` 參數跳過合併操作
    ```
    uv run berrizdown -g iu -m --skip-merge
    ```

- 下載 IU Post 並使用 `--tt 250818` 按時間篩選內容，將另一個參數（`--t/--tt`）留空以自動呼叫 `datetime.now()`
    - --tt or --t can be start time or end time
    ```
    uv run berrizdown -g iu -b --t 250818
    ```

- 下載 IU Post 並使用 --retitle "묵참과 함께 돌아온 출근시간 🥰" 來按標題過濾內容
    `您可以編寫自己的正規表示式，但請注意在console中進行轉義`
    ```
    uv run berrizdown -g iu -b --retitle "묵참과 함께 돌아온 출근시간 🥰"
    ```

- 使用 -b、-c、-l、-m、-p、-n 參數下載 IU 所有內容類型
    ```
    uv run berrizdown -g iu -b -c -l -m -p -n
    ```

- 使用 -c 和 --artisid 29 下載 KiiiKiii Artis 評論（回覆）
    `對於留言只能選 0. Artis archive`
    ```
    uv run berrizdown -g 2 -c --artisid 29
    ```

- 下載 WJSN 通知和照片，使用 -n -p 並按時間篩選 --t 20240601T0900 --TT "202501031 23:00"
    ```
    uv run berrizdown -g WJSN -n -p --t 20240601T0900 --TT "202501031 23:00"
    ```

- 下載 Woodz 評論並指定下載目錄
    ```
    uv run berrizdown https://berriz.in/en/woodz/board/0197e392-1bc8-27f8-36ff-1233e29f3c0a/post/01992d84-662c-14a6-7487-206ebc06292b/?focus=comment --save-dir "C:\\Users\\omenbibi\\Desktop\\berrizdown\\Woodz"
    ```

- 下載 i-dle 直播重播影片，僅需字幕
    ```
    uv run berrizdown https://berriz.in/en/i-dle/live/replay/019b4ed2-8b27-a4de-f4c2-30802de719ed/ --subs-only
    ```

- 下載 lightsum 直播重播影片，不需字幕
    ```
    uv run berrizdown -g lightsum -l --no-subs
    ```


# Demo
* 用法
```
uv run berrizdown\\demo.py
```
```python
import asyncio
from typing import Never

from lib.interface.interface import Community_Uniqueness, StartProcess, URL_Parser, selected_media_list
from pydantic import HttpUrl
from unit.http.request_berriz_api import BerrizAPIClient

# main aiohttp session for all request
BAPIClient: BerrizAPIClient = BerrizAPIClient()


async def media_live() -> bool:
    # sample live uuid
    liveid: str = "019681ce-aa41-6af0-b423-1c1cc6894bc5"
    # all the vaild url for live
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/jsh/live/{liveid}/",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/jsh/live/{liveid}/"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def media_video() -> bool:
    # sample media uuid
    mediaid: str = "0195cbb8-293a-43c4-f09f-9e04af1bbc2d"
    # all the vaild url for upload media
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/kiiikiii/media/content/{mediaid}/?mediaType=vod",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/kiiikiii/media/content/{mediaid}/"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def media_image() -> bool:
    # sample photo uuid
    mediaid: str = "0198ebbe-208c-63fb-03e5-a5fee518f4be"
    # all the vaild url for images
    urls: list[HttpUrl] = [f"https://link.berriz.in/web/main/kiiikiii/media/content/{mediaid}/"]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/kiiikiii/media/content/{mediaid}/"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def notice() -> bool:
    # sample notice id
    noticeid: int = 126
    # all the vaild url for notice
    urls: list[HttpUrl] = [f"https://link.berriz.in/web/main/iu/notice/{noticeid}/"]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/iu/notice/{noticeid}/"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post() -> bool:
    # sample post uuid
    postid: str = "0195cbc2-7223-6105-adb8-88e819dd545d"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post
    urls: list[HttpUrl] = [f"https://link.berriz.in/web/main/kiiikiii/board/{boardid}/post/{postid}/"]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/kiiikiii/board/{boardid}/post/{postid}/"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post_comment_last() -> bool:
    # sample post uuid
    postid: str = "0198bd54-98a4-6fe7-42fc-67923d1f14ff"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post-comment
    urls: list[HttpUrl] = [f"https://link.berriz.in/web/main/iu/board/{boardid}/post/{postid}/?focus=comment"]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/iu/board/{boardid}/post/{postid}/?focus=comment"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post_reply_artis() -> bool:
    # sample post uuid
    postid: str = "0199c97e-8cbf-ebd6-7952-ac1a68998050"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post-replay
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/iu/board/{boardid}/post/{postid}/?reply=1759787",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/iu/board/{boardid}/post/{postid}/?reply=1759787"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post_reply_user2user() -> Never:
    # sample post uuid
    postid: str = "019a3860-2851-c927-0e6f-678dcf6424cc"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post-replay
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/ive/board/{boardid}/post/{postid}/?reply=2040500",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/ive/board/{boardid}/post/{postid}/?reply=2040500"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def board_post_reply_user2artis() -> Never:
    # sample post uuid
    postid: str = "019a27bf-d625-4cf3-0443-dc91b64608e9"
    """Vaild UUID for board ID, Here I use null UUID for demo"""
    boardid: str = "00000000-0000-0000-0000-000000000000"
    # all the vaild url for post-replay
    urls: list[HttpUrl] = [
        f"https://link.berriz.in/web/main/iu/board/{boardid}/post/{postid}/?reply=2007535",
    ]
    """1. URL_Parser class accept List|str"""
    url: HttpUrl = f"https://berriz.in/iu/board/{boardid}/post/{postid}/?reply=2007535"
    bool_status: bool = await URL_Parser(urls).parser()
    return bool_status


async def get_results_selected_media() -> selected_media_list:
    """2. Community_Uniqueness List[dict[tuple, str | list[str]]]
    - make a pre list for process
    - key is community_id community_name community_name_nickname
    - valus is class selected_media_list
    - detil in lib\\interface\\interface.py
    """
    results_selected_media: selected_media_list = await Community_Uniqueness.group_by_community()
    return results_selected_media


async def start_run_process(results_selected_media: selected_media_list) -> Never:
    """3. Get results_selected_media this is a Regularization list for next process"""
    if results_selected_media != []:
        await StartProcess(results_selected_media).process()
    await close_session()


async def close_session() -> Never:
    """4. Make sure manuel close session after program end and leave funcation"""
    await BAPIClient.close_session()


if __name__ == "__main__":

    async def main() -> Never:
        """
        1. URL Parser and per all vaild urls data
        each chunk def will return a bool for status
        """
        bool_return: bool = await media_video()
        bool_return: bool = await media_live()
        bool_return: bool = await media_image()
        bool_return: bool = await notice()
        bool_return: bool = await board_post()
        bool_return: bool = await board_post_comment_last()
        bool_return: bool = await board_post_reply_artis()
        bool_return: bool = await board_post_reply_user2user()
        bool_return: bool = await board_post_reply_user2artis()
        """2. after all url parser finsh, collect all data into a class selected_media_list"""
        results_selected_media: selected_media_list = await get_results_selected_media()
        """3. start download process"""
        await start_run_process(results_selected_media)

    asyncio.run(main())

```



## 📄 License

AGPLv3 License - see [LICENSE](https://github.com/twkenxtis/Berrizdown/blob/main/LICENSE) file for details



# 免責聲明

<ol>
  <li>使用者自行決定是否使用本專案，並承擔所有相關風險。作者對因使用本專案而引起的任何損失、責任或風險概不負責。</li>
  <li>作者提供的程式碼和功能是基於現有知識和技術開發的成果。雖然作者盡一切努力確保程式碼的正確性和安全性符合當前技術標準，但並不保證程式碼完全沒有錯誤或缺陷。</li>
  <li>本專案依賴於第三方函式庫、外掛程式或服務，這些元件各自受其原始的開源或商業許可協議管轄。使用者必須審查並遵守相應的協議。作者對第三方元件的穩定性、安全性或合規性不承擔任何責任。</li>
  <li>使用者在使用本專案時必須嚴格遵守 
    <a href="https://github.com/twkenxtis/Berrizdown/blob/main/LICENSE">GNU Affero General Public License v3.0</a>，
    並須適當地承認使用了依據 
    <a href="https://github.com/twkenxtis/Berrizdown/blob/main/LICENSE">GNU Affero General Public License v3.0</a> 授權的程式碼。
  </li>
  <li>使用者有責任研究使用本專案程式碼和功能時應適用的法律和法規，並必須確保其使用行為是合法且合規的。任何因違規而導致的法律責任或風險將完全由使用者自行承擔。</li>
  <li><strong>使用者不得使用本工具從事任何侵犯智慧財產權的活動，包括但不限於未經授權地下載或散布受版權保護的內容。開發者不參與、不支持或認可任何非法獲取或散布內容的行為。</strong></li>
  <li>本專案對使用者資料的收集、儲存、傳輸或其他處理活動的合規性不承擔任何責任。使用者必須遵守相關法律法規，並確保其行為合法適當。任何因不合規操作而產生的法律責任將完全由使用者自行承擔。</li>
  <li>在任何情況下，使用者均不得將本專案的作者、貢獻者或任何相關方與其自身的使用行為相聯結，亦不得因使用本專案所造成的任何損失或損害而要求他們承擔責任。</li>
  <li>作者不會提供任何付費版本的 Berrizdown 專案，也不會提供任何與 Berrizdown 專案相關的商業服務。</li>
  <li>任何基於本專案的二次開發、修改或編譯與原作者無關。原作者對此類衍生行為或其結果不承擔任何責任。使用者應對二次開發所產生的任何後果承擔全部責任。</li>
  <li>本專案並未授予使用者任何專利許可。若使用本專案導致專利爭議或侵權，使用者應承擔所有風險與責任。未經作者或權利人書面授權，使用者不得將本專案用於任何商業推廣、行銷或再授權。</li>
  <li>作者保留終止對任何違反本免責聲明之使用者提供服務的權利，並可能要求銷毀任何已獲取的程式碼或衍生作品。</li>
  <li>作者保留隨時更新本免責聲明的權利，恕不另行通知。繼續使用本專案將被視為接受修訂後的條款。</li>
</ol>
<br>

**在使用本專案的程式碼和功能之前，請仔細考量並接受上述免責聲明。如果您有任何疑問或不同意上述條款，請勿使用本專案的程式碼或功能。透過使用本專案的程式碼和功能，即視為您已充分理解並接受上述免責聲明，並自願承擔使用所產生的一切風險與後果。**



# 致謝
https://github.com/devine-dl/pywidevine
https://github.com/ready-dl/pyplayready
https://github.com/chu23465/VT-PR
https://github.com/devine-dl/devine
https://git.gay/ready-dl/pywidevine
