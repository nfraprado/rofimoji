import html
from collections import namedtuple
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from lxml import etree
from lxml.etree import XPath

Emoji = namedtuple('Emoji', 'char name')


def fetch_emoji_list() -> List[Emoji]:
    return extract_from_html(fetch_emoji_html())


def fetch_emoji_html() -> BeautifulSoup:
    max_tries = 5
    for i in range(max_tries):
        print('Downloading emojis... try %s' % (i + 1))
        data = requests.get(
            'https://unicode.org/emoji/charts-12.0/full-emoji-list.html',
            timeout=120
        )  # type: requests.Response
        if data:
            break

    if not data:
        print('Could not fetch emoji data. Try again later or use another URL.')
        exit(10)
    return BeautifulSoup(data.content, 'lxml')


def extract_from_html(html: BeautifulSoup) -> List[Emoji]:
    emojis = []

    for row in html.find('table').find_all('tr'):
        if row.th:
            continue
        emoji = row.find('td', {'class': 'chars'}).string
        description = row.find('td', {'class': 'name'}).string.replace('⊛ ', '')

        emojis.append(Emoji(emoji, description))

    return emojis


def fetch_human_emojis() -> List[chr]:
    print('Downloading list of human emojis...')

    data = requests.get(
        'https://unicode.org/Public/emoji/12.0/emoji-data.txt',
        timeout=60
    )  # type: requests.Response

    started = False
    emojis = []
    for line in data.content.decode(data.encoding).split('\n'):
        if not started and line != '# All omitted code points have Emoji_Modifier_Base=No ':
            continue
        started = True
        if started and line == '# Total elements: 120':
            break
        if started and (line.startswith('#') or len(line) == 0):
            continue
        emojis.extend(extract_emojis_from_line(line))

    return emojis


def extract_emojis_from_line(line: str) -> List[chr]:
    emoji_range = line.split(';')[0].strip()
    try:
        (start, end) = emoji_range.split('..')
        emojis = []
        for char in range(int(start, 16), int(end, 16) + 1):
            emojis.append(chr(char))
        return emojis
    except ValueError:
        return [chr(int(emoji_range, 16))]


def fetch_annotations() -> Dict[chr, List[str]]:
    print('Downloading annotations')

    data = requests.get(
        'https://raw.githubusercontent.com/unicode-org/cldr/release-35-1/common/annotations/en.xml',
        timeout=60
    )  # type: requests.Response

    xpath = XPath('./annotations/annotation[not(@type="tts")]')
    return {element.get('cp'): element.text.split(' | ') for element in
            xpath(etree.fromstring(data.content))}


def write_symbol_file(all_emojis: List[Emoji],  annotations: Dict[chr, List[str]]):
    print('Writing collected emojis to symbol file')
    symbol_file = open('../picker/data/emojis.csv', 'w')

    for entry in compile_entries(all_emojis, annotations):
        symbol_file.write(entry + "\n")

    symbol_file.close()


def write_metadata_file(human_emojis: List[chr]):
    print('Writing metadata to metadata file')
    metadata_file = open('../picker/copyme.py', 'w')

    metadata_file.write('skin_tone_selectable_emojis={\'')
    metadata_file.write('\', \''.join(human_emojis))
    metadata_file.write('\'}\n')
    metadata_file.close()


def compile_entries(emojis: List[Emoji], annotations: Dict[chr, List[str]]) -> List[str]:
    annotated_emojis = []
    for emoji in emojis:
        if emoji.char in annotations:
            entry = f"{emoji.char} {html.escape(emoji.name)} <small>({html.escape(', '.join(annotations[emoji.char]))})</small>"
        else:
            entry = f"{emoji.char} {html.escape(emoji.name)}"

        annotated_emojis.append(entry)

    return annotated_emojis


if __name__ == "__main__":
    write_symbol_file(fetch_emoji_list(), fetch_annotations())
    write_metadata_file(fetch_human_emojis())
