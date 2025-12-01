<p align="center">
    <img width="32" height="48" alt="berriz_ico" src="https://github.com/twkenxtis/Berriz-Media-pass/blob/main/berriz-extension-chrome/assets/icons/berry512.png" />
    <br/>
      <sup><em><a href="https://github.com/twkenxtis/Berrizdown/blob/main/README_ZH.md">中文</a></em></sup>
    <sup><strong>A command-line app for downloading Berriz video, photo post and comment notice</strong></sup>
</p>

# Berrizdown
* **Easy Installation** \- UV installation
* **Multi Quality** \- DASH/HLS manifest support
* **DRM** \- Widevine and PlayReady integration
* **Key** \- Remote CDM or local key vault
* **Session** \- Support for cookies and login
* **Customizable** \- YAML\-based configuration
* **Auto-Detection** \- Interactive menus or automatic URL recognition
* **Log** \- Automatically skip already downloaded files

![DEMO](https://github.com/twkenxtis/Berrizdown/blob/main/dmeo.gif)

# Quick Start
```
git clone https://github.com/twkenxtis/Berrizdown
cd Berrizdown
uv sync
uv run berrizdown -?
```



# Required
#### Python 3.11 or higher
- UV requires install in your sytem
    [UV](https://docs.astral.sh/uv/getting-started/installation/)
    check UV docs for more information
    ```
    Windows:
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    Mac and Linux:
    curl -LsSf https://astral.sh/uv/install.sh | sh

    wget -qO- https://astral.sh/uv/install.sh | sh
    ```

> [!NOTE]
> Make sure fully read and setting YAML config
> `berrizconfig.yaml` and `berrizconfig.example.yaml` files in the berrizdown folder contain default values ​​and references
- **YAML Config** \- Edit `berrizconfig.yaml` file to customize your settings
> [!IMPORTANT]
> Un support board 【Calendar】 [issues#1](https://github.com/twkenxtis/Berrizdown/issues/1)

#### FFmpeg only require when download videos
Put ffmpeg in `berrizdown\\lib\\tools` and add ffmpeg name in `berrizconfig.yaml` or `ffmpeg` in system env
- Windows: [AnimMouse's FFmpeg Builds](https://github.com/AnimMouse/ffmpeg-stable-autobuild/releases)
- Linux: [John Van Sickle's FFmpeg Builds](https://johnvansickle.com/ffmpeg/)

Put ffprobe in `berrizdown\\lib\\tools` and add ffprobe name in `berrizconfig.yaml` or `ffprobe` in system env



# Cookie / Login

> ⚠️ Only Fanclub and Videos require cookie

## Berriz Cookies

Export your browser cookies in **Netscape format** while logged in with an active at the Berriz website:

- **Firefox**: [Get cookies.txt LOCALLY](https://addons.mozilla.org/en-US/firefox/addon/get-cookies-txt-locally/)
- **Chromium**: [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)

📁 Copy `default.txt` to `berrizdown\\cookies\\Berriz` folder.  
✅ Script only reads **default.txt** in NETSCAPE format.

---

## Berriz Account Login

Use your **Berriz account and password** (not Google/Apple login):

1. Edit `[account:password]` in `berrizconfig.yaml` file.
2. Run:

   ```
   uv run berrizdown
   ```



### Optional
**mp4decrypt** \- Required for Decrypting DRM content if want use `mp4decrypt` for decrypting [mp4decrypt](https://www.bento4.com/documentation/mp4decrypt/)
* Put mp4decrypt in `berrizdown\\lib\\tools` and add mp4decrypt name in `berrizconfig.yaml` 

**shaka-packager** \- Required for Decrypting DRM content if want use `shaka-packager` for decrypting
[shaka-packager](https://github.com/shaka-project/shaka-packager)
* Put shaka-packager in `berrizdown\\lib\\tools` and add shaka-packager name in `berrizconfig.yaml` or `shaka-packager` in system env

**mkvmerge** \-\- Required for remuxing with `mkvtoolnix` or you can choese ffmpeg only [mkvtoolnix](https://mkvtoolnix.download/)
* Put mkvmerge in `berrizdown\\lib\\tools` and add mkvmerge name in `berrizconfig.yaml` or `mkvmerge` in system env


> [!IMPORTANT]
> No live stream support and no Youtube support, Live stream dl will be added in the future
> If console show missing tool, please follow path and put it in `berrizdown\\lib\\tools`


## 🧾 Berrizdown CLI Options

| Option(s) | Description |
|-----------|-------------|
| `-h`, `--help`, `-H`, `-?`, `--?` | Show this help message and exit |
| `-nc`, `--no_cookie`, `--nocookie`, `--no-cookie` | Do not use cookies |
| `-cm`, `--community` | List all current communities in Berriz |
| `--join 'COMMUNITY_NAME'` | Join a community |
| `--leave 'COMMUNITY_NAME'` | Leave a community |
| `-g 'ive'`, `--group 7` | Select artist's community (`ive` or `7`) — only one allowed |
| *(default)* | All items except comments (`CMT`) will be selected |
| `-b`, `--board` | Select board content |
| `-c`, `--cmt` | Select comment content |
| `-l`, `--live`, `--live-only` | Select live content |
| `-m`, `--media`, `--media-only` | Select media section video content |
| `-p`, `--photo`, `--photo-only` | Select media section photo content |
| `-n`, `--notice`, `--notice-only` | Select notice section content |
| `-fc`, `--fanclub-only`, `--fanclub` | Show fanclub-only content |
| `-nfc`, `--no-fanclub` | Show non-fanclub content |
| `--T`, `--t <datetime start>` | Filter content by start date/time (KST base only, use full year like `2025`)[ISO8601,YYMMDD,'19970101 00:00'] |
| `--TT`, `--tt <datetime end>` | [Optional] Filter content by end date/time (use full year like `2025`)[ISO8601,YYMMDD,'19970101 00:00'] |
| `--signup` | Berriz account registration |
| `--change-password`, `--changepassword` | Change current account password |
| `-q`, `--quality` | choese video quality (`1080p`, `720p`, `480p`, etc.) |
| `-v`, `--vcodec` | Video codec (e.g., `H264`) |
| `-na`, `-an`, `--no-audio`, `--skip-audio`, `--skip-a`, `--skipaudio` | Do not download audio tracks |
| `-nv`, `-vn`, `--no-video`, `--skip-videos`, `--skip-v`, `--skip-video`, `--skipvideo` | Do not download video tracks |
| `--ss` | Specify video start time |
| `--to` | Specify video end time |
| `--list` | Skip downloading and list available tracks |
| `--del-after-done` | Delete after completion (`true`/`false`) |
| `--skip-merge` | Skip merge after completion |
| `--skip-mux` | Skip mux after merge |
| `-k`, `--key`, `--keys` | Show key and skip download |
| `--skip-dl`, `--skip-download` | Skip all downloads |
| `--skip-json`, `--skip-Json`, `--skip-JSON`, `--skipjson` | Skip saving JSON locally |
| `--skip-thumbnails`, `--skip-thb`, `--skipthumbnails` | Skip saving thumbnails locally |
| `--skip-images`, `--skip-imgs`, `--skip-image`, `--skip-img`, `--skipimage` | Skip saving images locally |
| `--skip-playlist`, `--skip-Playlist`, `--skip-pl`, `--skipplaylist` | Skip saving playlist locally |
| `--skip-html`, `--skip-Html`, `--skip-HTML`, `--skiphtml` | Skip saving HTML format locally |
| `--no-info`, `--noinfo` | No JSON / HTML / m3u8 / MPD / thumbnails |
| `--nosubfolder`, `--no-subfolder`, `--no_subfolder` | No extra subfolders for each content |
| `--retitle` | Filter titles using regular expressions |
| `--artisid` | Specify ArtistID (e.g., `--artisid 71,72,73`) — only works at 0. Artis archive |
| `--cdm` | Override the CDM used for decryption |
| `--cache` | Use only Key Vaults for decryption keys |
| `--no-cache` | Use only CDM for decryption keys |
| `--save-dir` | Set output directory, and overwire berrizconfig.yaml |
| `--version`, `--v` | Show version |





# example
- Download from url (Receive url[str] that are split by commas, spaces or no spilt)
    ```
    uv run berrizdown https://link.berriz.in/web/main/jsh/live/replay/019681ce-aa41-6af0-b423-1c1cc6894bc5/https://berriz.in/en/jsh/live/replay/019681ce-aa41-6af0-b423-1c1cc6894bc5/https://berriz.in/applink/web/jsh/live/replay/019681ce-aa41-6af0-b423-1c1cc6894bc5/
    ```

- Download IU live-replay (-g 5, -g IU, -g iu) and download live start 60:00 to 70:00
    ```
    uv run berrizdown -g 5 -l --ss 60:00 --to 70:00
    ```

- Download IVE live-replay (-g 7, -g Ive, -g IVE) and download 720p set noinfo to only download video
    ```
    uv run berrizdown -g 5 -l -q 720 --no-info
    ```

- Download JSH live-replay (-g 1, -g jsh) and use --cdm to override the CDM to use for decryption
    ```
    uv run berrizdown -g jsh -l --cdm "path\\my_cdm\\cdm.wvd|prd"
    ```

- Download KiiiKiii live-replay (-g 2, -g kiiikiii) and use --nosubfolder for no extra subfolders for each contet then -vn for audio only
    ```
    uv run berrizdown -g jsh -l --nosubfolder -vn
    ```

- Download IU Media (-g 5, -g IU, -g iu) and use --skip-mux to skip mux after merge
    ```
    uv run berrizdown -g iu -m --skip-mux
    ```

- Download IVE Media (-g 7, -g ive) and use --fanclub for show only fanclub-only content
    ```
    uv run berrizdown -g ive -m -p --fanclub
    ```

- Download IU Media and use --skip-merge to skip merge after completion
    ```
    uv run berrizdown -g iu -m --skip-merge
    ```

- Download IU Post and use --tt 250818 to filter content by time, keep another (--t/--tt) empty to auto call datetime.now()
    - --tt or --t can be start time or end time
    ```
    uv run berrizdown -g iu -b --t 250818
    ```

- Download IU Post and use --retitle "묵참과 함께 돌아온 출근시간 🥰" to fzf filter content by title
    `Can write your own regex and be mindful of the escaping on console`
    ```
    uv run berrizdown -g iu -b --retitle "묵참과 함께 돌아온 출근시간 🥰"
    ```

- Download IU All content type by using -b, -c, -l, -m, -p, -n
    ```
    uv run berrizdown -g iu -b -c -l -m -p -n
    ```

- Download KiiiKiii Artis comment(reply) by using -c and --artisid 29
    `For comment must choese 0. Artis archive`
    ```
    uv run berrizdown -g 2 -c --artisid 29
    ```

- Download WJSN Notice and Photo use -n -p and filter by time --t 20240601T0900 --TT "202501031 23:00"
    ```
    uv run berrizdown -g WJSN -n -p --t 20240601T0900 --TT "202501031 23:00"
    ```

- Download Woodz comment and specify the download directory
    ```
    uv run berrizdown https://berriz.in/en/woodz/board/0197e392-1bc8-27f8-36ff-1233e29f3c0a/post/01992d84-662c-14a6-7487-206ebc06292b/?focus=comment --save-dir "C:\\Users\\omenbibi\\Desktop\\berrizdown\\Woodz"
    ```


# Demo
* Usage
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



<h1>Disclaimer</h1> <ol> <li>Users decide on their own whether to use this project and bear all associated risks. The author shall not be held responsible for any loss, liability, or risk arising from the use of this project.</li> <li>The code and features provided by the author are the result of development based on existing knowledge and technology. While the author makes every effort to ensure the correctness and security of the code according to current technical standards, no guarantee is made that the code is entirely free of errors or defects.</li> <li>This project relies on third-party libraries, plugins, or services, each governed by their original open-source or commercial licenses. Users must review and comply with the respective agreements. The author assumes no responsibility for the stability, security, or compliance of third-party components.</li> <li>Users must strictly comply with the <a href="https://github.com/twkenxtis/Berrizdown/blob/main/LICENSE">GNU Affero General Public License v3.0</a> when using this project, and must properly acknowledge the use of code licensed under the <a href="https://github.com/twkenxtis/Berrizdown/blob/main/LICENSE">GNU Affero General Public License v3.0</a>.</li> <li>Users are responsible for researching applicable laws and regulations when using the code and features of this project, and must ensure that their usage is legal and compliant. Any legal liability or risk resulting from violations shall be borne solely by the user.</li> <li>Users must not use this tool to engage in any activity that infringes intellectual property rights, including but not limited to unauthorized downloading or distribution of copyrighted content. The developer does not participate in, support, or endorse any illegal acquisition or distribution of content.</li> <li>This project does not assume responsibility for the compliance of users’ data collection, storage, transmission, or other processing activities. Users must comply with relevant laws and regulations and ensure that their actions are lawful and appropriate. Any legal liability resulting from non-compliant operations shall be borne solely by the user.</li> <li>Under no circumstances shall users associate the author, contributors, or any related parties of this project with their own usage behavior, nor hold them liable for any loss or damage resulting from the use of this project.</li> <li>The author will not offer any paid version of the Berrizdown project, nor provide any commercial services related to the Berrizdown project.</li> <li>Any secondary development, modification, or compilation based on this project is unrelated to the original author. The original author assumes no responsibility for such derivative actions or their outcomes. Users shall bear full responsibility for any consequences arising from secondary development.</li> <li>This project does not grant users any patent licenses. If the use of this project leads to patent disputes or infringement, users shall bear all risks and liabilities. Without written authorization from the author or rights holder, users may not use this project for any commercial promotion, marketing, or sublicensing.</li> <li>The author reserves the right to terminate services to any user who violates this disclaimer and may require the destruction of any acquired code or derivative works.</li> <li>The author reserves the right to update this disclaimer at any time without prior notice. Continued use of the project shall be deemed acceptance of the revised terms.</li> </ol> <b>Before using the code and features of this project, please carefully consider and accept the above disclaimer. If you have any questions or do not agree with the above terms, do not use the code or features of this project. By using the code and features of this project, you are deemed to have fully understood and accepted the above disclaimer and voluntarily assume all risks and consequences associated with its use.</b>



# Thanks
https://github.com/devine-dl/pywidevine
https://github.com/ready-dl/pyplayready
https://github.com/chu23465/VT-PR
https://github.com/devine-dl/devine
https://git.gay/ready-dl/pywidevine