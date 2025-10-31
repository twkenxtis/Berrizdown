import logging

from lib.path import Path


class CDM_PATH:
    def __init__(self, CFG: dict):
        try:
            if CFG["CDM"]["playready"] is not None:
                self.prd_device_path: str = Path(__file__).parent.parent.joinpath("key\\device\\" + CFG["CDM"]["playready"])
            else:
                self.prd_device_path: str = None
            if CFG["CDM"]["widevine"] is not None:
                self.wv_device_path: str = Path(__file__).parent.parent.joinpath("key\\device\\" + CFG["CDM"]["widevine"])
            else:
                self.wv_device_path: str = None
        except KeyError as e:
            logging.error(f"KeyError in CDM config: {e}")
            raise KeyboardInterrupt("Check config/berrizconfig.yaml CDM setting Not found CDM setting in YAML.")
