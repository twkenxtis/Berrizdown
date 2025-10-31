class Color:
    __slots__ = ()
    __FG = "\033[38;5;"
    __BG = "\033[48;5;"
    __RESET = "\033[0m"
    __BOLD = "\033[1m"

    __colors = {
        # 基本色系
        "black": 0,
        "red": 1,
        "green": 2,
        "yellow": 3,
        "blue": 4,
        "magenta": 5,
        "cyan": 6,
        "gray": 8,
        "white": 15,
        # 亮色系
        "bright_black": 16,
        "bright_red": 9,
        "bright_green": 10,
        "bright_yellow": 11,
        "bright_blue": 12,
        "bright_magenta": 13,
        "bright_cyan": 14,
        "bright_white": 15,
        "bright_gray": 7,
        # 暗色系
        "dark_red": 52,
        "dark_green": 22,
        "dark_yellow": 58,
        "dark_blue": 19,
        "dark_magenta": 53,
        "dark_cyan": 30,
        "dark_gray": 236,
        # 淺色系
        "light_gray": 250,
        "light_red": 203,
        "light_green": 120,
        "light_yellow": 227,
        "light_blue": 117,
        "light_magenta": 213,
        "light_cyan": 159,
        "light_white": 231,
        # 擴充語意色
        "orange": 208,
        "gold": 220,
        "lime": 118,
        "teal": 37,
        "navy": 18,
        "olive": 100,
        "maroon": 1,
        "indigo": 54,
        "violet": 129,
        "pink": 218,
        "salmon": 216,
        "coral": 209,
        "peach": 223,
        "mint": 121,
        "sky_blue": 111,
        "steel_blue": 67,
        "turquoise": 80,
        "aquamarine": 86,
        "chartreuse": 112,
        "spring_green": 48,
        "forest_green": 28,
        "sea_green": 29,
        "khaki": 143,
        "beige": 180,
        "tan": 144,
        "chocolate": 130,
        "sienna": 130,
        "plum": 176,
        "orchid": 170,
        "lavender": 183,
        "periwinkle": 111,
        "slate_gray": 66,
        "light_slate_gray": 103,
        "royal_blue": 63,
        "midnight_blue": 17,
        "tomato": 203,
        "firebrick": 124,
        "crimson": 160,
        "ruby": 161,
        "amber": 214,
        "lemon": 226,
        "honeydew": 194,
        "ivory": 230,
        "snow": 231,
        "linen": 255,
        "wheat": 229,
        "sand": 180,
        "moss": 65,
        "fern": 34,
        "iceberg": 195,
        "fog": 252,
        "deep_blue": 19,
        "denim": 20,
        "ocean_blue": 21,
        "sage": 22,
        "peacock": 23,
        "teal_blue": 24,
        "vapor_blue": 25,
        "cerulean": 26,
        "azure": 27,
        "spring_aqua": 30,
        "light_mint": 31,
        "apple_green": 32,
        "light_lime": 33,
        "fresh_chartreuse": 35,
        "yellow_ochre": 36,
        "light_amber": 38,
        "sunrise": 39,
        "sunflower": 40,
        "daffodil": 41,
        "light_lemon": 42,
        "dark_honey": 43,
        "light_peach": 44,
        "blush": 45,
        "rose": 46,
        "soft_coral": 47,
        "soft_salmon": 49,
        "flamingo_pink": 50,
        "magenta_pink": 51,
        "cobalt": 52,
        "off_white": 232,
        "pearl": 233,
        "mist": 234,
        "ash_gray": 235,
        "cloud": 237,
        "foggy": 238,
        "smoke": 239,
        "silver_gray": 240,
        "dove": 241,
        "aluminum": 242,
        "titanium": 243,
        "platinum": 244,
        "graphite": 245,
        "charcoal_gray": 246,
        "steel_gray": 247,
        "iron": 248,
        "tungsten": 249,
        "cement": 250,
        "dusk": 251,
        "pitch_black": 253,
        "ebony": 254,
    }

    @classmethod
    def fg(cls, name: str) -> str:
        """前景色（文字顏色）"""
        code = cls.__colors.get(name.lower())
        return f"{cls.__FG}{code}m" if code is not None else ""

    @classmethod
    def bg(cls, name: str) -> str:
        """背景色"""
        code = cls.__colors.get(name.lower())
        return f"{cls.__BG}{code}m" if code is not None else ""

    @classmethod
    def bold(cls) -> str:
        return cls.__BOLD

    @classmethod
    def reset(cls) -> str:
        return cls.__RESET
