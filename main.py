# -*- coding: utf-8 -*-
import requests
import random
import string
import uuid
import sys
from slugify import slugify
import os
import shutil
from yarl import URL
from chapter_parser import parse_chapter
from ebooklib import epub
from args_cfg import args

if not args.url:
    ranobe_url = input("Ссылка на ранобэ: ")
else:
    ranobe_url = args.url
ranobe_host = "https://ranobelib.me"
api_host = "https://api.lib.social"
reqs = requests.session()
reqs.headers = {
    "user-agent": "Mozilla/5.0 (Linux i675 ) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/55.0.3924.176 Safari/534"
}

def main_info(ranobe):
    ranobe_info = {
        "ranobe_url_id": ranobe
        }
    info_url = f"{api_host}/api/manga/{ranobe}?fields[]=background&fields[]=eng_name&fields[]=otherNames&fields[]=summary&fields[]=releaseDate&fields[]=type_id&fields[]=caution&fields[]=views&fields[]=close_view&fields[]=rate_avg&fields[]=rate&fields[]=genres&fields[]=tags&fields[]=teams&fields[]=franchise&fields[]=authors&fields[]=publisher&fields[]=userRating&fields[]=moderated&fields[]=metadata&fields[]=metadata.count&fields[]=metadata.close_comments&fields[]=manga_status_id&fields[]=chap_count&fields[]=status_id&fields[]=artists&fields[]=format"
    page = reqs.get(info_url)
    if page.status_code == 404:
        if os.path.isfile("token.txt"):
            with open("token.txt", "r") as f:
                reqs.headers["Authorization"] = f"Bearer {f.read()}"
            page = reqs.get(info_url)
        else:
            print(
                "Невозможно получить данные. Если страница имеет ограничение по возрасту, то прочтите файл howToAuth.md")
            sys.exit()
    page = page.json()["data"]
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
        teams[branch_id] = {
            "name": name,
            "total_chapters": 0
        }
    no_branch_id_count = 0
    if len(teams.items()) > 1:
        if not str(args.translation):
            print("Выберите переводчика\n")
        for i in chapters:
            if i['branches']:
                for branch in i["branches"]:
                    if not branch["branch_id"]:
                        no_branch_id_count+=1
                    else:
                        teams[branch["branch_id"]]["total_chapters"] += 1
        if not args.translation:
            for inx, team in enumerate(teams.items()):
                print(f"{inx} - {team[1]['name']}. Глав переведено {team[1]['total_chapters']}")
            if no_branch_id_count:
                if args.no_null_branch_id:
                    print(f"Также НЕ будут скачаны {no_branch_id_count} глав с неизвестным переводчиком (см. флаг -n в разделе --help).")
                else:
                    print(
                        f"Также будут скачаны {no_branch_id_count} глав с неизвестным переводчиком (см. флаг -n в разделе --help).")
            branch_id = list(teams.keys())[int(input("Номер переводчика: "))]
        else:
            branch_id = list(teams.keys())[int(args.translation)]
    else:
        # branch_id = branches[0]["id"]
        branch_id = None
    # -------------------
    ranobe_info["branch_id"] = branch_id
    ranobe_info["chapters"] = {}
    if not args.range or args.check_nums:
        _chapters = []
        for c in chapters:
            if not branch_id or int(branch_id) in [x["branch_id"] for x in c["branches"]] or (None in [x["branch_id"] for x in c["branches"]] and not args.no_null_branch_id):
                if str(c["volume"]) not in ranobe_info["chapters"]:
                    ranobe_info["chapters"][str(c["volume"])] = []
                ranobe_info["chapters"][str(c["volume"])].append(c)
                _chapters.append(c)
        if args.check_nums:
            for inx, c in enumerate(_chapters):
                print(f"{inx+1} - Том {c['volume']} Глава {c['number']}")
            sys.exit()

    else:
        if args.range.isnumeric():
            for c in chapters:
                if not branch_id or int(branch_id) in [x["branch_id"] for x in c["branches"]] or (
                        None in [x["branch_id"] for x in c["branches"]] and not args.no_null_branch_id):
                    if str(c["volume"]) not in ranobe_info["chapters"] and str(c["volume"]) == str(args.range):
                        ranobe_info["chapters"][str(c["volume"])] = []
                    if str(c["volume"]) == str(args.range):
                        ranobe_info["chapters"][str(c["volume"])].append(c)
        else:
            _chapters = []
            for c in chapters:
                if not branch_id or int(branch_id) in [x["branch_id"] for x in c["branches"]] or (
                        None in [x["branch_id"] for x in c["branches"]] and not args.no_null_branch_id):
                    if str(c["volume"]) not in ranobe_info["chapters"]:
                        ranobe_info["chapters"][str(c["volume"])] = []
                    _chapters.append(c)
            _range = args.range
            _range = _range.replace(" ", "")
            _range = _range.split("-")
            if all(_range):
                _chapters = _chapters[int(_range[0])-1:int(_range[1])]
            else:
                _chapters = _chapters[int(_range[0])-1:] if _range[0] else _chapters[:int(_range[1])]
            for c in _chapters:
                ranobe_info["chapters"][str(c["volume"])].append(c)
            ranobe_info["chapters"] = {x:y for x, y in ranobe_info["chapters"].items() if y}
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
poster_content = requests.get(ranobe_info["poster_url"]).content
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
    # st = ''''''
    # nav_css = epub.EpubItem(uid="style_nav",
    #                        file_name="style/nav.css",
    #                        media_type="text/css",
    #                        content=st)
    # book.add_item(nav_css)
    # -----------------------------------------------------------
    epub_chapters = []
    for chapter in chapters:
        print(f"Том {tom} Глава {chapter['number']}")
        if ranobe_info['branch_id']:
            chapter_url = f"{api_host}/api/manga/{ranobe_info['ranobe_url_id']}/chapter?branch_id={ranobe_info['branch_id']}&number={chapter['number']}&volume={tom}"
        else:
            chapter_url = f"{api_host}/api/manga/{ranobe_info['ranobe_url_id']}/chapter?number={chapter['number']}&volume={tom}"
        chapter_content, chapters_imgs = parse_chapter(chapter_url, reqs)
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
    epub.write_epub(f"./{book_folder}/{book_filename}.epub", book, {
        "play_order": {
            "enabled": True,
            "start_from": 1
        }
    })
    # -----------------------------------------------------------
