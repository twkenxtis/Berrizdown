import requests
from lxml import etree

from berrizdown.static.color import Color
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("msprpro", "aquamarine")


def extract_pssh(response: str | bytes) -> list[str]:
    """
    從 MPD XML 中提取 cenc:pssh 元素的文字內容

    :param response: XML 字串或 bytes
    :return: PSSH 字串列表
    """
    try:
        xml_data = response

        # 確保是 bytes，避免 encoding 問題
        if isinstance(xml_data, str):
            xml_data = xml_data.encode("utf-8")

        # 解析 XML
        root = etree.fromstring(xml_data)

        # 提取 pssh
        namespaces: dict[str, str] = {
            "cenc": "urn:mpeg:cenc:2013",
            "mspr": "urn:microsoft:playready",
        }

        pssh_elements = root.xpath("//mspr:pro", namespaces=namespaces)
        return [pssh.text.strip() for pssh in pssh_elements if pssh.text]

    except etree.XMLSyntaxError as e:
        logger.error(f"XML parsing error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error during PSSH extraction: {e}")
        return []


class GetMPD_prd:
    @staticmethod
    def parse_pssh(raw_mpd: requests.Response) -> list[str] | None:
        """
        解析 MPD 文件並過濾 MSPR:PRO PSSH 值（長度大於 400 的值）

        :param raw_mpd: requests.Response 物件
        :return: PSSH 列表或 None
        """
        pssh_values = extract_pssh(raw_mpd)

        if not pssh_values:
            logger.warning(f"{Color.bg('mint')}No MSPR:PRO PSSH values found in the MPD file.{Color.reset()}")
            return None

        valid_pssh_list: list[str] = []
        for pssh in pssh_values:
            if len(pssh) > 399:
                valid_pssh_list.append(pssh)

        if valid_pssh_list:
            return valid_pssh_list
        else:
            logger.error("No MSPR:PRO PSSH value with exactly 400 characters found")
            return None
