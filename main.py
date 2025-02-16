import asyncio

from config import set_up_app, settings
from controllers import process_text_directory


async def main():
    set_up_app("wiki_app")
    await process_text_directory(settings.FOLDER_NAME)


if __name__ == "__main__":
    asyncio.run(main())
