from functools import wraps
import logging
import os
import re
import time

import httpx

from config import settings


def sanitize_filename(raw_name: str) -> str:
    name = raw_name.replace(" ", "-").replace(".", "-")
    name = re.sub(r"[^а-яА-Яa-zA-Z0-9\-_]+", "", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")
    return name


async def create_page_in_wikijs(title: str, content: str, description: str):
    logging.getLogger("httpx").setLevel(logging.WARNING)
    query = """
    mutation (
      $content: String!,
      $description: String!,
      $editor: String!,
      $isPublished: Boolean!,
      $isPrivate: Boolean!,
      $locale: String!,
      $path: String!,
      $title: String!,
      $tags: [String]!
    ) {
      pages {
        create(
          content: $content,
          description: $description,
          editor: $editor,
          isPublished: $isPublished,
          isPrivate: $isPrivate,
          locale: $locale,
          path: $path,
          title: $title,
          tags: $tags
        ) {
          responseResult {
            succeeded
            errorCode
            slug
            message
          }
          page {
            id
            path
            title
            isPrivate
            isPublished
          }
        }
      }
    }
    """

    variables = {
        "content": content,
        "description": description,
        "editor": "markdown",
        "isPublished": True,
        "isPrivate": False,
        "locale": "ru",
        "path": f"/{description}/{title}",
        "title": title,
        "tags": [],
    }

    headers = {
        "Authorization": f"Bearer {settings.WIKI_TOKEN.get_secret_value()}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.API_URL,
            headers=headers,
            json={"query": query, "variables": variables},
        )

    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            logging.info(f"Error while creating page '{title}': {data['errors']}")
        else:
            mutation_result = data["data"]["pages"]["create"]
            if mutation_result["responseResult"]["succeeded"]:
                page_info = mutation_result["page"]
                logging.info(
                    f"Page '{page_info['title']}' created at {page_info['path']}"
                )
            else:
                logging.info(
                    f"Page creation failed: {mutation_result['responseResult']['message']}"
                )
    else:
        logging.info(f"HTTP error {response.status_code}: {response.text}")


def execution_time(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        end = time.perf_counter()
        elapsed_time = end - start

        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        formatted_time = f"{minutes:02}:{seconds:02}"

        logging.info(
            f"Function {func.__name__} finished. Execution time: {formatted_time}."
        )
        return result

    return wrapper


@execution_time
async def process_text_directory(base_dir: str):
    for root, dirs, files in os.walk(base_dir):
        if root == base_dir:
            continue
        folder_name = os.path.basename(root)

        for file_name in files:
            old_path = os.path.join(root, file_name)
            if not os.path.isfile(old_path):
                continue

            base_name, ext = os.path.splitext(file_name)
            sanitized_base = sanitize_filename(base_name)
            new_file_name = sanitized_base + ext

            if new_file_name != file_name:
                new_path = os.path.join(root, new_file_name)
                os.rename(old_path, new_path)
                logging.info(f"Renamed file: '{file_name}' → '{new_file_name}'")
                old_path = new_path

            with open(old_path, encoding="utf-8") as f:
                content = f.read()

            title = sanitized_base
            await create_page_in_wikijs(
                title=title, content=content, description=folder_name
            )
