# -*- coding: utf-8 -*-
import requests
import random
import string
from bs4 import BeautifulSoup
import re
import uuid
import json
from slugify import slugify
import os
import shutil
from yarl import URL
from chapter_parser import parse_chapter
from ebooklib import epub

ranobe_url = input("Ссылка на ранобэ: ")
ranobe_host = "https://ranobelib.me"
api_host = "https://api.lib.social"
reqs = requests.session()
reqs.headers = {"user-agent": "".join(random.choices(string.ascii_lowercase, k=12))}


def main_info(ranobe):
    ranobe_info = {"ranobe_url_id":ranobe}
    page = reqs.get(f"{api_host}/api/manga/{ranobe}?fields[]=background&fields[]=eng_name&fields[]=otherNames&fields[]=summary&fields[]=releaseDate&fields[]=type_id&fields[]=caution&fields[]=views&fields[]=close_view&fields[]=rate_avg&fields[]=rate&fields[]=genres&fields[]=tags&fields[]=teams&fields[]=franchise&fields[]=authors&fields[]=publisher&fields[]=userRating&fields[]=moderated&fields[]=metadata&fields[]=metadata.count&fields[]=metadata.close_comments&fields[]=manga_status_id&fields[]=chap_count&fields[]=status_id&fields[]=artists&fields[]=format").json()["data"]
    chapters = reqs.get(f"{api_host}/api/manga/{ranobe}/chapters").json()["data"]
    ranobe_id = page["id"]
    branches = reqs.get(f"{api_host}/api/branches/{ranobe_id}?team_defaults=1").json()["data"]
    ranobe_info["ranobe_id"] = ranobe_id
    ranobe_info["title"] = page["rus_name"]
    ranobe_info["description"] = page["summary"]
    ranobe_info["authors"] = [x["name"] for x in page["authors"]]
    ranobe_info["tags"] = [x["name"] for x in page["genres"]] + [x["name"] for x in page["tags"]]
    ranobe_info["poster_url"] = page["cover"]["default"]
    # выбор перевода
    teams = {}
    for b in branches:
        name = ", ".join([x["name"] for x in b["teams"]])
        branch_id = b["id"]
        teams[branch_id] = {"name":name, "total_chapters":0}

    if len(teams.items()) > 1:
        print("Выберите переводчика\n")
        for i in chapters:
            if i['branches']:
                for branch in i["branches"]:
                    teams[branch["branch_id"]]["total_chapters"]+=1
        for inx,team in enumerate(teams.items()):
            print(f"{inx} - {team[1]['name']}. Глав переведено {team[1]['total_chapters']}")
        branch_id = list(teams.keys())[int(input("Номер переводчика: "))]
    else:
        #branch_id = branches[0]["id"]
        branch_id = None
    # -------------------
    ranobe_info["branch_id"] = branch_id
    ranobe_info["chapters"] = {}
    for c in chapters:
        if not branch_id or int(branch_id) in [x["branch_id"] for x in c["branches"]]:
            if str(c["volume"]) not in ranobe_info["chapters"]:
                ranobe_info["chapters"][str(c["volume"])] = []
            ranobe_info["chapters"][str(c["volume"])].append(c)
    return ranobe_info


ranobe_url_host = URL(ranobe_url)
ranobe_url_id = ranobe_url_host.parts[-1]
ranobe_info = main_info(ranobe_url_id)
ranobe_url_host = URL.build(scheme=ranobe_url_host.scheme, host=ranobe_url_host.host, path=ranobe_url_host.path)
book_folder = slugify(ranobe_info["title"])
if os.path.exists(book_folder):
    shutil.rmtree(f"./{book_folder}")
    os.mkdir(book_folder)
else:
    os.mkdir(book_folder)
poster_content = reqs.get(ranobe_info["poster_url"]).content
for tom, chapters in ranobe_info["chapters"].items():
    book_imgs = []
    book = epub.EpubBook()
    book.set_cover(content=poster_content, file_name=f"cover.{ranobe_info['poster_url'].split('.')[-1]}")
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(f"{tom} Том | {ranobe_info['title']}")
    book_filename = slugify(f"{str(tom).rjust(3, '0')} Том | {ranobe_info['title']}")
    book.set_language("ru")
    for aut in ranobe_info["authors"]:
        book.add_author(aut)
    book.add_metadata("DC", "description", ranobe_info["description"])
    st = '''.image-container {display: flex; justify-content: center}'''
    nav_css = epub.EpubItem(uid="style_nav",
                            file_name="style/nav.css",
                            media_type="text/css",
                            content=st)
    book.add_item(nav_css)
    # -----------------------------------------------------------
    epub_chapters = []
    for chapter in chapters:
        print(f"Том {tom} Глава {chapter['number']}")
        if ranobe_info['branch_id']:
            chapter_url = f"{api_host}/api/manga/{ranobe_info['ranobe_url_id']}/chapter?branch_id={ranobe_info['branch_id']}&number={chapter['number']}&volume={tom}"
        else:
            chapter_url = f"{api_host}/api/manga/{ranobe_info['ranobe_url_id']}/chapter?number={chapter['number']}&volume={tom}"
        chapter_content, chapters_imgs = parse_chapter(chapter_url)
        book_imgs += chapters_imgs
        c = epub.EpubHtml(title=f"Глава {chapter['number']} - {chapter['name']}",
                          file_name=f"{str(uuid.uuid4())}.xhtml", lang="ru")
        c.content = f'<h2 align="center" style="text-align:center;">Глава {chapter["number"]} - {chapter["name"]}</h2>{chapter_content}'
        epub_chapters.append(c)
        book.add_item(c)
    book.toc = epub_chapters
    book.spine = [*epub_chapters, "nav"]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    for img in book_imgs:
        book.add_item(img)
    epub.write_epub(f"./{book_folder}/{book_filename}.epub", book, {"play_order": {"enabled": True, "start_from": 1}})
    # -----------------------------------------------------------
