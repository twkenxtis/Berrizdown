try:
    import logging
    import asyncio
except KeyboardInterrupt:
    pass
def main():
    try:
        from .core import start
        asyncio.run(start())
    except ImportError:
        pass
    except KeyboardInterrupt as e:
        if str(e) == "":
            logging.info(f"Program interrupted: User canceled")
        else:
            logging.warning(f"Program interrupted: {e}")
    except RuntimeError as e:
        if str(e) == "Event loop is closed":
            logging.warning(f"Program interrupted: Event loop is closed re-run the program.")
            asyncio.run(start())
        else:
            raise e
    except asyncio.CancelledError:
        pass