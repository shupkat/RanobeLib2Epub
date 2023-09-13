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
reqs = requests.session()
reqs.headers = {"user-agent": "".join(random.choices(string.ascii_lowercase, k=12))}
chapters_json_pattern = r"__DATA__ = (.*);"


def main_info(ranobe):
    ranobe_info = {}
    page_html = reqs.get(ranobe).text
    page = BeautifulSoup(page_html, "lxml")
    ranobe_info["title"] = page.find("div", {"class": "media-name__main"}).text.strip()
    ranobe_info["description"] = page.find("div", {"class": "media-description__text"}).text.strip()
    ranobe_info["authors"] = [x.text.strip() for x in page.find("div", string="Автор").parent.find_all("a")]
    ranobe_info["tags"] = [x.text.strip().title() for x in page.find("div", {"class": "media-tags"}).find_all("a")]
    ranobe_info["poster_url"] = page.find("div", {"class": "media-sidebar__cover paper"}).find("img")["src"]
    chapters = re.search(chapters_json_pattern, page_html).group(1)
    chapters = json.loads(chapters)
    # выбор перевода
    branches = chapters["chapters"]["teams"]
    teams = []
    if len(branches) > 1:
        print("Выберете переводчика\n")
        for inx, team in enumerate(branches):
            team_name = team["name"]
            team_branch_id = team["branch_id"]
            team_chapters_count = 0
            for c in chapters["chapters"]["list"]:
                if c["branch_id"] == team_branch_id:
                    team_chapters_count += 1
            teams.append(team_branch_id)
            print(f"{inx} - {team_name}. Глав переведено {team_chapters_count}")
        branch_id = teams[int(input("Номер переводчика: "))]
    else:
        branch_id = branches[0]["branch_id"]
    # -------------------
    ranobe_info["branch_id"] = branch_id
    ranobe_info["chapters"] = {}
    for c in reversed(chapters["chapters"]["list"]):
        if c["branch_id"] != branch_id: continue
        if str(c["chapter_volume"]) not in ranobe_info["chapters"]:
            ranobe_info["chapters"][str(c["chapter_volume"])] = []
        ranobe_info["chapters"][str(c["chapter_volume"])].append(c)
    return ranobe_info


ranobe_info = main_info(ranobe_url)
ranobe_url_host = URL(ranobe_url)
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
        print(f"Том {tom} Глава {chapter['chapter_number']}")
        chapter_url = f"{ranobe_url_host}/v{tom}/c{chapter['chapter_number']}?bid={ranobe_info['branch_id']}"
        chapter_content, chapters_imgs = parse_chapter(chapter_url)
        book_imgs += chapters_imgs
        c = epub.EpubHtml(title=f"Глава {chapter['chapter_number']} {chapter['chapter_name']}",
                          file_name=f"{str(uuid.uuid4())}.xhtml", lang="ru")
        c.content = f'<h2 align="center" style="text-align:center;">Глава {chapter["chapter_number"]} {chapter["chapter_name"]}</h2>{chapter_content}'
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
