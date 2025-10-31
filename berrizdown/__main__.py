try:
    import asyncio
    import logging

    from berriz import main
    from static.color import Color

    asyncio.run(main())
except KeyboardInterrupt as e:
    if str(e) == "":
        logging.info(f"Program interrupted: {Color.fg('light_gray')}User canceled{Color.reset()}")
    else:
        logging.warning(f"Program interrupted: {Color.fg('light_gray')}{e}{Color.reset()}")
except RuntimeError as e:
    if str(e) == "Event loop is closed":
        logging.warning(f"Program interrupted: {Color.fg('light_gray')}Event loop is closed re-run the program.{Color.reset()}")
        asyncio.run(main())
    else:
        raise e
