import string
import traceback

import requests
import random
import uuid
import os
from bs4 import BeautifulSoup
from ebooklib import epub
ranobe_host = "https://ranobelib.me"
def parse_chapter(url):
    images = {}
    while 1:
        try:
            headers = {"user-agent": "".join(random.choices(string.ascii_lowercase, k=12))}
            r = requests.get(url, headers=headers).json()["data"]
            content = BeautifulSoup(r["content"], "lxml")
            break
        except:
            print(traceback.format_exc())
    for i in content.find_all(recursive=True):
        a = list(i.attrs.keys())
        for y in a:
            if y not in ["data-src", "src"]:
                del i.attrs[y]
        if "data-src" in i.attrs:
            i.attrs["src"] = i.attrs["data-src"]
            del i.attrs["data-src"]
    for img in content.find_all("img", recursive=True):
        img.parent.attrs["class"] = "image-container"
        uid = uuid.uuid4().hex
        filetype = str(img.attrs["src"]).split(".")[-1]
        images[uid] = {"url": img.attrs["src"] if str(img.attrs["src"]).startswith("http") else ranobe_host+str(img.attrs["src"]), "filetype": filetype}
        img.attrs["src"] = f"static/{uid}.{filetype}"
    epub_images = []
    for uid, info in images.items():
        r = requests.get(info["url"], headers=headers)
        content_type = r.headers["content-type"]
        img = epub.EpubImage(
            uid=uid,
            file_name=f"static/{uid}.{info['filetype']}",
            media_type=content_type,
            content=r.content,
        )
        epub_images.append(img)
        #book.add_item(img)
    return content, epub_images
