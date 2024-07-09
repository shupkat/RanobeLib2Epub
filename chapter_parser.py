import string
import time
import traceback
from prosemirror.model import Node
from prosemirror.model import DOMSerializer
from scheme import schema
import requests
import random
import uuid
from bs4 import BeautifulSoup
from ebooklib import epub

api_host = "https://api.lib.social"
ranobe_host = "https://ranobelib.me"


def fix_images_scheme(json_doc, img_urls):
    new_images = {}
    for inx, i in enumerate(json_doc["content"]):
        images = []
        if i["type"] == "image":
            for img in i["attrs"]["images"]:
                images.append({
                                  "type": "image",
                                  "attrs": {
                                      "src": f"{api_host}{img_urls[img['image']]}"
                                      }
                                  })
        if images:
            new_images[inx] = images
    indices_to_replace = list(new_images.keys())
    indices_to_replace.sort(reverse=True)
    for index in indices_to_replace:
        json_doc["content"].pop(index)
        for new_element in reversed(new_images[index]):
            json_doc["content"].insert(index, new_element)
    return json_doc


def parse_chapter(url, reqs):
    images = {}
    while 1:
        try:
            resp = reqs.get(url)
            if resp.status_code == 429:
                # Too many requests! Wait for 10 seconds
                time.sleep(10)
                continue
            r = resp.json()["data"]
            if isinstance(r["content"], str):
                page_html = r["content"]
            else:
                img_urls = {x["name"]:x["url"] for x in r["attachments"]}
                json_content = fix_images_scheme(r["content"], img_urls)
                doc_node = Node.from_json(schema, json_content)
                page_html = str(DOMSerializer.from_schema(schema).serialize_fragment(doc_node.content))
            content = BeautifulSoup(page_html, "lxml")
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
        img.attrs["style"] = "display: block; margin: auto; max-width: 100%; max-height: 100%; height: auto;"
        uid = uuid.uuid4().hex
        filetype = str(img.attrs["src"]).split(".")[-1]
        images[uid] = {
            "url": img.attrs["src"] if str(img.attrs["src"]).startswith("http") else api_host + str(
                img.attrs["src"]),
            "filetype": filetype
            }
        img.attrs["src"] = f"static/{uid}.{filetype}"
    epub_images = []
    for hr in content.find_all("hr", recursive=True):
        hr.replace_with(BeautifulSoup('<p style="text-align:center">***</p>', "html.parser"))
    for uid, info in images.items():
        info["url"] = info["url"].replace(ranobe_host, api_host)
        r = requests.get(info["url"])
        content_type = r.headers["content-type"]
        img = epub.EpubImage(
            uid=uid,
            file_name=f"static/{uid}.{info['filetype']}",
            media_type=content_type,
            content=r.content,
        )
        epub_images.append(img)
        # book.add_item(img)
    return content, epub_images
