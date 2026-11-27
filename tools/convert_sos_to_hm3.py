#!/usr/bin/env python3
"""Deterministic converter from upstream Foundry VTT module (hm-adv-sos) to FGU HarnMaster3.5E."""

import html
from html.parser import HTMLParser
import json
import math
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM_ASSETS = os.path.join(ROOT_DIR, "upstream", "assets")
IMAGES_DIR = os.path.join(ROOT_DIR, "images")
TOKENS_DIR = os.path.join(ROOT_DIR, "tokens")
DB_PATH = os.path.join(ROOT_DIR, "db.xml")

ACTORS_DIR = os.path.join(UPSTREAM_ASSETS, "packs", "actors-hm3", "unique")
JOURNALS_DIR = os.path.join(UPSTREAM_ASSETS, "packs", "journals", "unique")
SCENES_DIR = os.path.join(UPSTREAM_ASSETS, "packs", "scenes", "unique")

# ---------------------------------------------------------------------------
# Canonical asset mappings
# ---------------------------------------------------------------------------

PREGEN_ACTORS = [
    ("Gorrys_of_Lunn_fZRVLT8T5B5iMxgN.json", "gorrys-of-lunn", "Gorrys of Lunn"),
    ("Harlin_of_Kleve_v0Z90exD5DaGN7eh.json", "harlin-of-kleve", "Harlin of Kleve"),
    ("Kalas_of_Delsin_MLzzfHa8A3VBqyQ2.json", "kalas-of-delsin", "Kalas of Delsin"),
    ("Lysha_of_Rakath_ejcyk6Nt5uCBpIa8.json", "lysha-of-rakath", "Lysha of Rakath"),
    ("Ondren_of_Lemra_5Sox26oiHZcYYdE0.json", "ondren-of-lemra", "Ondren of Lemra"),
    ("Ryssi_of_Chert_83bDi0eAHIBBA8zI.json", "ryssi-of-chert", "Ryssi of Chert"),
]

NPC_ACTORS = [
    ("Corik_Yepbtfzpigc0OHH6.json", "Corik"),
    ("Jedes_Guard_iWMqajzUOAcKQA5z.json", "Jedes Guard"),
    ("Larith_lKNSZXRavKCfhgcj.json", "Larith"),
    ("Larith_s_Bear_lvRvYtkBE1yoCvsJ.json", "Larith's Bear"),
]

NPC_PORTRAITS = [
    ("sir-tamys-poulty.webp", "Sir Tamys Poulty"),
    ("straken-of-ornelt.webp", "Straken of Ornelt"),
    ("sir-shernath-mirdarne.webp", "Sir Shernath Mirdarne"),
    ("lady-helarn-poutry.webp", "Lady Helarn Poutry"),
    ("sir-jasyff-mazerony.webp", "Sir Jasyff Mazerony"),
    ("jastrin-of-dyrl.webp", "Jastrin of Dyrl"),
]

SUNSIGN_ABBREV = {
    "ulandia": "Ula", "ulandus": "Ula", "ulandis": "Ula",
    "aralius": "Ara",
    "feniri": "Fen",
    "ahnu": "Ahn",
    "angberelius": "Ang",
    "nadai": "Nad",
    "hirin": "Hir",
    "tarael": "Tar",
    "tai": "Tai",
    "skorus": "Sko",
    "masara": "Mas", "masada": "Mas", "madada": "Mas",
    "lado": "Lad",
}

ABILITY_SHORTHAND = {
    "agility": "AGL",
    "aura": "AUR",
    "comeliness": "CML",
    "dexterity": "DEX",
    "endurance": "END",
    "eyesight": "EYE",
    "hearing": "HRG",
    "intelligence": "INT",
    "morality": "MOR",
    "smell": "SML",
    "stamina": "STA",
    "strength": "STR",
    "voice": "VOI",
    "will": "WIL",
}

PC_ABILITY_KEYS = [
    ("agility", "Agility"),
    ("aura", "Aura"),
    ("comeliness", "Comeliness"),
    ("dexterity", "Dexterity"),
    ("endurance", "Endurance"),
    ("eyesight", "Eyesight"),
    ("hearing", "Hearing"),
    ("intelligence", "Intelligence"),
    ("morality", "Morality"),
    ("smell", "Smell"),
    ("stamina", "Stamina"),
    ("strength", "Strength"),
    ("voice", "Voice"),
    ("will", "Will"),
]

NPC_ABILITY_KEYS = [
    ("agility", "Agility"),
    ("aura", "Aura"),
    ("comeliness", "Comeliness"),
    ("dexterity", "Dexterity"),
    ("endurance", "Endurance"),
    ("eyesight", "Eyesight"),
    ("fly", "Fly"),
    ("hearing", "Hearing"),
    ("intelligence", "Intelligence"),
    ("morality", "Morality"),
    ("move", "Move"),
    ("smell", "Smell"),
    ("stamina", "Stamina"),
    ("strength", "Strength"),
    ("swim", "Swim"),
    ("voice", "Voice"),
    ("will", "Will"),
]

FOUNDRY_LOC_TO_CODE = {
    "skull": "Sk",
    "face": "Fa",
    "neck": "Nk",
    "shoulder": "Sh",
    "upper arm": "Ua",
    "elbow": "El",
    "forearm": "Fo",
    "hand": "Ha",
    "thorax": "Tx",
    "chest": "Ch",
    "back": "Bk",
    "abdomen": "Ab",
    "groin": "Gr",
    "hip": "Hp",
    "thigh": "Th",
    "knee": "Kn",
    "calf": "Ca",
    "foot": "Ft",
}

# Exact HM3.5E Humanoid Hit Location Rows (matches HarnMaster3.5E data_common_hm3.lua)
HUMANOID_HIT_ROWS = [
    {"loc": "sk", "res": "Skull",     "rank": 10, "lat": 0, "from": 1,  "to": 5,   "f_hi": 1,  "t_hi": 15,  "f_lo": 0,  "t_lo": 0},
    {"loc": "fa", "res": "Face",      "rank": 11, "lat": 0, "from": 6,  "to": 10,  "f_hi": 16, "t_hi": 30,  "f_lo": 0,  "t_lo": 0},
    {"loc": "nk", "res": "Neck",      "rank": 12, "lat": 0, "from": 11, "to": 15,  "f_hi": 31, "t_hi": 45,  "f_lo": 0,  "t_lo": 0},
    {"loc": "sh", "res": "Shoulder",  "rank": 13, "lat": 1, "from": 16, "to": 27,  "f_hi": 46, "t_hi": 57,  "f_lo": 0,  "t_lo": 0},
    {"loc": "ua", "res": "Upper Arm", "rank": 14, "lat": 1, "from": 28, "to": 33,  "f_hi": 58, "t_hi": 69,  "f_lo": 0,  "t_lo": 0},
    {"loc": "el", "res": "Elbow",     "rank": 15, "lat": 1, "from": 34, "to": 35,  "f_hi": 70, "t_hi": 73,  "f_lo": 0,  "t_lo": 0},
    {"loc": "fo", "res": "Forearm",   "rank": 16, "lat": 1, "from": 36, "to": 39,  "f_hi": 74, "t_hi": 81,  "f_lo": 1,  "t_lo": 6},
    {"loc": "ha", "res": "Hand",      "rank": 17, "lat": 1, "from": 40, "to": 43,  "f_hi": 82, "t_hi": 85,  "f_lo": 7,  "t_lo": 12},
    {"loc": "tx", "res": "Thorax",    "rank": 18, "lat": 0, "from": 44, "to": 60,  "f_hi": 86, "t_hi": 95,  "f_lo": 13, "t_lo": 19},
    {"loc": "ch", "res": "Chest",     "rank": 19, "lat": 0, "from": 44, "to": 60,  "f_hi": 0,  "t_hi": 0,   "f_lo": 0,  "t_lo": 0},
    {"loc": "bk", "res": "Back",      "rank": 20, "lat": 0, "from": 44, "to": 60,  "f_hi": 0,  "t_hi": 0,   "f_lo": 0,  "t_lo": 0},
    {"loc": "ab", "res": "Abdomen",   "rank": 21, "lat": 0, "from": 61, "to": 70,  "f_hi": 96, "t_hi": 100, "f_lo": 20, "t_lo": 39},
    {"loc": "gr", "res": "Groin",     "rank": 22, "lat": 0, "from": 71, "to": 74,  "f_hi": 0,  "t_hi": 0,   "f_lo": 40, "t_lo": 50},
    {"loc": "hp", "res": "Hip",       "rank": 23, "lat": 1, "from": 75, "to": 80,  "f_hi": 0,  "t_hi": 0,   "f_lo": 51, "t_lo": 56},
    {"loc": "th", "res": "Thigh",     "rank": 24, "lat": 1, "from": 81, "to": 88,  "f_hi": 0,  "t_hi": 0,   "f_lo": 57, "t_lo": 70},
    {"loc": "kn", "res": "Knee",      "rank": 25, "lat": 1, "from": 89, "to": 90,  "f_hi": 0,  "t_hi": 0,   "f_lo": 71, "t_lo": 78},
    {"loc": "ca", "res": "Calf",      "rank": 26, "lat": 1, "from": 91, "to": 96,  "f_hi": 0,  "t_hi": 0,   "f_lo": 79, "t_lo": 92},
    {"loc": "ft", "res": "Foot",      "rank": 27, "lat": 1, "from": 97, "to": 100, "f_hi": 0,  "t_hi": 0,   "f_lo": 93, "t_lo": 100},
]

DEFENSE_ARMORLIST_ZONES = [
    ("Skull", "Sk"), ("Face", "Fa"), ("Neck", "Nk"),
    ("Shoulders", "Sh"), ("Upper Arms", "Ua"), ("Elbow", "El"),
    ("Forearms", "Fo"), ("Hands", "Ha"),
    ("Thorax", "Tx"), ("Chest", "Ch"), ("Back", "Bk"),
    ("Abdomen", "Ab"), ("Groin", "Gr"),
    ("Hips", "Hp"), ("Thighs", "Th"), ("Knees", "Kn"),
    ("Calves", "Ca"), ("Feet", "Ft"),
]

QUADRUPED_HIT_ROWS = [
    {"from": 1,  "to": 10,  "loc": "he", "lat": 0, "res": "Head"},
    {"from": 11, "to": 20,  "loc": "nk", "lat": 0, "res": "Neck"},
    {"from": 21, "to": 30,  "loc": "fo", "lat": 1, "res": "Fore Leg"},
    {"from": 31, "to": 50,  "loc": "tx", "lat": 0, "res": "Thorax"},
    {"from": 51, "to": 80,  "loc": "ab", "lat": 0, "res": "Abdomen"},
    {"from": 81, "to": 95,  "loc": "th", "lat": 1, "res": "Hind Leg"},
    {"from": 96, "to": 100, "loc": "ta", "lat": 0, "res": "Tail"},
]

SKILLGROUP_META = {
    "Physical":      ("10", "Physical"),
    "Communication": ("20", "Communication"),
    "Language":      ("30", "Language"),
    "Religion":      ("40", "Religion"),
    "Combat":        ("50", "Combat"),
    "Crafts & Lore": ("60", "Crafts & Lore"),
    "Convocation":   ("70", "Convocation"),
}

FOUNDRY_SKILLTYPE_MAP = {
    "Physical": "Physical",
    "Communication": "Communication",
    "Combat": "Combat",
    "Craft": "Crafts & Lore",
    "Ritual": "Religion",
    "Magic": "Convocation",
    "Psionic": "Communication",
}

WEAPON_SUBTYPE_FROM_SKILL = {
    "bow": "Bow",
    "shortbow": "Bow",
    "longbow": "Bow",
    "hartbow": "Bow",
    "dagger": "Dagger",
    "taburi": "Dagger",
    "knife": "Dagger",
    "sword": "Sword",
    "falchion": "Sword",
    "shortsword": "Sword",
    "broadsword": "Sword",
    "spear": "Spear",
    "staff": "Spear",
    "shield": "Shield",
    "buckler": "Shield",
    "round shield": "Shield",
    "axe": "Axe",
    "club": "Club",
    "flail": "Flail",
    "polearm": "Polearm",
    "unarmed": "Unarmed",
}


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def sub_typed(parent, tag, typ, text=None):
    el = ET.SubElement(parent, tag, {"type": typ})
    if text is not None:
        el.text = str(text)
    return el


def set_formattedtext(parent, tag, inner_xml):
    """Attach raw FGU formattedtext XML safely inside <tag type="formattedtext">."""
    wrapped = f'<{tag} type="formattedtext">{inner_xml}</{tag}>'
    try:
        node = ET.fromstring(wrapped)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid formattedtext XML for <{tag}>: {exc}\n{wrapped[:600]}") from exc
    parent.append(node)
    return node


def escape_text(s):
    return html.escape(s or "", quote=False)


# ---------------------------------------------------------------------------
# HTML -> FGU FormattedText Sanitizer
# ---------------------------------------------------------------------------

class FguHtmlSanitizer(HTMLParser):
    """Converts Foundry HTML into strict FGU formattedtext XML."""

    def __init__(self, strip_images=True):
        super().__init__(convert_charrefs=True)
        self.strip_images = strip_images
        self.blocks = []
        self.cur_tag = None
        self.cur_buf = []
        self.in_table = False
        self.table_rows = []
        self.cur_row = None
        self.cur_cell = None
        self.cell_is_header = False
        self.table_caption = []
        self.in_caption = False
        self.in_list = False
        self.list_items = []
        self.cur_li = None
        self.in_blockquote = False
        self.bq_buf = []
        self.in_dl = False
        self.dl_term = None
        self.dl_def = None
        self.inline_stack = []
        self.link_href = None

    def _active_buf(self):
        if self.in_caption:
            return self.table_caption
        if self.cur_cell is not None:
            return self.cur_cell
        if self.cur_li is not None:
            return self.cur_li
        if self.dl_def is not None:
            return self.dl_def
        if self.dl_term is not None:
            return self.dl_term
        if self.in_blockquote and self.cur_tag is None:
            return self.bq_buf
        if self.cur_tag is not None:
            return self.cur_buf
        return None

    def _emit_inline(self, text):
        text = text.replace("\xa0", " ")
        escaped = escape_text(text)
        buf = self._active_buf()
        if buf is not None:
            buf.append(escaped)
        elif escaped.strip():
            self.blocks.append(f"<p>{escaped.strip()}</p>")

    def _flush_paragraph(self):
        if self.cur_tag is not None:
            content = "".join(self.cur_buf).strip()
            content = re.sub(r"[ \t\r\n]+", " ", content)
            if content:
                if self.cur_tag == "h":
                    self.blocks.append(f"<h>{content}</h>")
                elif self.cur_tag == "h3":
                    self.blocks.append(f"<p><b>{content}</b></p>")
                else:
                    if self.in_blockquote:
                        self.bq_buf.append(f"<p>{content}</p>")
                    else:
                        self.blocks.append(f"<p>{content}</p>")
            self.cur_tag = None
            self.cur_buf = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        attr_dict = dict(attrs)
        if t == "img":
            return
        if t in ("h1", "h2"):
            self._flush_paragraph()
            self.cur_tag = "h"
            self.cur_buf = []
        elif t in ("h3", "h4", "h5", "h6"):
            self._flush_paragraph()
            self.cur_tag = "h3"
            self.cur_buf = []
        elif t == "p":
            if self.cur_cell is not None or self.cur_li is not None:
                return
            self._flush_paragraph()
            self.cur_tag = "p"
            self.cur_buf = []
        elif t == "br":
            if self.cur_tag == "p":
                self._flush_paragraph()
                self.cur_tag = "p"
                self.cur_buf = []
            elif self.cur_cell is not None:
                self.cur_cell.append(" ")
        elif t in ("strong", "b"):
            buf = self._active_buf()
            if buf is None:
                self.cur_tag = "p"
                self.cur_buf = []
                buf = self.cur_buf
            buf.append("<b>")
            self.inline_stack.append("b")
        elif t in ("em", "i"):
            buf = self._active_buf()
            if buf is None:
                self.cur_tag = "p"
                self.cur_buf = []
                buf = self.cur_buf
            buf.append("<i>")
            self.inline_stack.append("i")
        elif t == "u":
            buf = self._active_buf()
            if buf is not None:
                buf.append("<u>")
                self.inline_stack.append("u")
        elif t == "a":
            self.link_href = attr_dict.get("href", "")
        elif t == "blockquote":
            self._flush_paragraph()
            self.in_blockquote = True
            self.bq_buf = []
        elif t in ("ul", "ol"):
            self._flush_paragraph()
            self.in_list = True
            self.list_items = []
        elif t == "li":
            self.cur_li = []
        elif t == "dl":
            self._flush_paragraph()
            self.in_dl = True
        elif t == "dt":
            self.dl_term = []
        elif t == "dd":
            self.dl_def = []
        elif t == "table":
            self._flush_paragraph()
            self.in_table = True
            self.table_rows = []
            self.table_caption = []
        elif t == "caption" and self.in_table:
            self.in_caption = True
        elif t == "tr" and self.in_table:
            self.cur_row = []
        elif t in ("td", "th") and self.in_table and self.cur_row is not None:
            self.cur_cell = []
            self.cell_is_header = (t == "th")

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("h1", "h2", "h3", "h4", "h5", "h6", "p"):
            if self.cur_cell is not None or self.cur_li is not None:
                if t == "p" and self.cur_cell is not None and self.cur_cell:
                    self.cur_cell.append(" ")
                return
            self._flush_paragraph()
        elif t in ("strong", "b"):
            if self.inline_stack and self.inline_stack[-1] == "b":
                self.inline_stack.pop()
                buf = self._active_buf()
                if buf is not None:
                    buf.append("</b>")
        elif t in ("em", "i"):
            if self.inline_stack and self.inline_stack[-1] == "i":
                self.inline_stack.pop()
                buf = self._active_buf()
                if buf is not None:
                    buf.append("</i>")
        elif t == "u":
            if self.inline_stack and self.inline_stack[-1] == "u":
                self.inline_stack.pop()
                buf = self._active_buf()
                if buf is not None:
                    buf.append("</u>")
        elif t == "a":
            if self.link_href and self.link_href.startswith("http"):
                buf = self._active_buf()
                if buf is not None:
                    buf.append(escape_text(f" ({self.link_href})"))
            self.link_href = None
        elif t == "blockquote":
            self._flush_paragraph()
            inner = "".join(self.bq_buf).strip()
            if inner:
                # FGU <frame> expects plain text or simple inline, flatten <p> if needed
                plain = re.sub(r"</?p>", " ", inner).strip()
                plain = re.sub(r"\s+", " ", plain)
                self.blocks.append(f"<frame>{plain}</frame>")
            self.in_blockquote = False
            self.bq_buf = []
        elif t == "li":
            if self.cur_li is not None:
                item_txt = re.sub(r"\s+", " ", "".join(self.cur_li)).strip()
                if item_txt:
                    self.list_items.append(f"<li>{item_txt}</li>")
                self.cur_li = None
        elif t in ("ul", "ol"):
            if self.list_items:
                self.blocks.append(f"<list>{''.join(self.list_items)}</list>")
            self.in_list = False
            self.list_items = []
        elif t == "dt":
            pass
        elif t == "dd":
            term = re.sub(r"\s+", " ", "".join(self.dl_term or [])).strip()
            defn = re.sub(r"\s+", " ", "".join(self.dl_def or [])).strip()
            if term or defn:
                if term:
                    self.blocks.append(f"<p><b>{term}:</b> {defn}</p>")
                else:
                    self.blocks.append(f"<p>{defn}</p>")
            self.dl_term = None
            self.dl_def = None
        elif t == "dl":
            self.in_dl = False
        elif t == "caption" and self.in_table:
            self.in_caption = False
        elif t in ("td", "th") and self.in_table and self.cur_row is not None and self.cur_cell is not None:
            cell_txt = re.sub(r"\s+", " ", "".join(self.cur_cell)).strip()
            if self.cell_is_header and cell_txt and not (cell_txt.startswith("<b>") and cell_txt.endswith("</b>")):
                cell_txt = f"<b>{cell_txt}</b>"
            self.cur_row.append(f"<td>{cell_txt}</td>")
            self.cur_cell = None
            self.cell_is_header = False
        elif t == "tr" and self.in_table and self.cur_row is not None:
            if self.cur_row:
                self.table_rows.append(f"<tr>{''.join(self.cur_row)}</tr>")
            self.cur_row = None
        elif t == "table" and self.in_table:
            cap = re.sub(r"\s+", " ", "".join(self.table_caption)).strip()
            if cap:
                self.blocks.append(f"<p><b>{cap}</b></p>")
            if self.table_rows:
                self.blocks.append(f"<table>{''.join(self.table_rows)}</table>")
            self.in_table = False
            self.table_rows = []
            self.table_caption = []

    def handle_data(self, data):
        self._emit_inline(data)

    def get_fgu_xml(self):
        self._flush_paragraph()
        # Clean empty bold/italic tags
        out = "".join(self.blocks)
        out = re.sub(r"<b>\s*</b>", "", out)
        out = re.sub(r"<i>\s*</i>", "", out)
        return out or "<p />"


def resolve_uuids_and_sanitize(raw_html, uuid_resolver, extra_links=None):
    """Replace @UUID[...]{Label} inline, convert HTML to FGU XML, and append <linklist>."""
    collected_links = []
    seen_records = set()

    if extra_links:
        for cls, rec, label in extra_links:
            if (cls, rec) not in seen_records:
                seen_records.add((cls, rec))
                collected_links.append((cls, rec, label))

    def _repl(match):
        target = match.group(1)
        label = (match.group(2) or target).strip()
        resolved = uuid_resolver(target, label)
        if resolved:
            cls, rec, link_label = resolved
            if (cls, rec) not in seen_records:
                seen_records.add((cls, rec))
                collected_links.append((cls, rec, link_label))
        return f"<strong>{html.escape(label)}</strong>"

    replaced = re.sub(r"@UUID\[([^\]]+)\](?:\{([^}]*)\})?", _repl, raw_html or "")
    parser = FguHtmlSanitizer()
    parser.feed(replaced)
    parser.close()
    body_xml = parser.get_fgu_xml()

    if collected_links:
        links_xml = "".join(
            f'<link class="{escape_text(cls)}" recordname="{escape_text(rec)}">{escape_text(lbl)}</link>'
            for cls, rec, lbl in collected_links
        )
        body_xml = f"{body_xml}<linklist>{links_xml}</linklist>"
    return body_xml


def html_to_plain_text(raw_html):
    txt = re.sub(r"<br\s*/?>", "\n", raw_html or "", flags=re.I)
    txt = re.sub(r"</(?:p|h1|h2|h3|tr|li|div)>", "\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html.unescape(txt).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in txt.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def extract_kv_table(raw_html):
    kv = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", raw_html or "", re.DOTALL | re.I):
        cells = [
            re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c)).replace("\xa0", " ")).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.I)
        ]
        if len(cells) >= 2 and cells[0]:
            kv[cells[0].strip(": ")] = cells[1]
    return kv


# ---------------------------------------------------------------------------
# Step 2.1: Copy & convert image/token assets
# ---------------------------------------------------------------------------

def copy_assets():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(TOKENS_DIR, exist_ok=True)

    def cp(src_name, dst_dir, dst_name):
        src = os.path.join(UPSTREAM_ASSETS, "images", src_name)
        dst = os.path.join(dst_dir, dst_name)
        shutil.copy2(src, dst)

    # Map & Handouts
    cp("gm-map.webp", IMAGES_DIR, "Shower of Silver Map GM.webp")
    cp("letter-to-sir-kodar.webp", IMAGES_DIR, "Letter to Sir Kodar.webp")
    cp("the-prophecy.webp", IMAGES_DIR, "The Prophecy.webp")

    # Convert characters.jpg -> WebP (quality=75)
    char_jpg = os.path.join(UPSTREAM_ASSETS, "images", "characters.jpg")
    with Image.open(char_jpg) as im:
        im.convert("RGB").save(os.path.join(IMAGES_DIR, "PreGen Characters.webp"), format="WEBP", quality=75)

    # NPC portraits
    for src_name, title in NPC_PORTRAITS:
        cp(src_name, IMAGES_DIR, f"{title}.webp")

    # Bear
    cp("black-bear.webp", IMAGES_DIR, "Black Bear.webp")
    cp("black-bear-headshot.webp", IMAGES_DIR, "Black Bear Headshot.webp")
    cp("black-bear-token.webp", TOKENS_DIR, "Black Bear Token.webp")

    # PreGen PCs
    for _, slug, full_name in PREGEN_ACTORS:
        cp(f"{slug}.webp", IMAGES_DIR, f"{full_name}.webp")
        cp(f"{slug}-headshot.webp", IMAGES_DIR, f"{full_name} Headshot.webp")
        cp(f"{slug}-token.webp", TOKENS_DIR, f"{full_name} Token.webp")


# ---------------------------------------------------------------------------
# Helpers for HM3.5E skill/weapon/armor conversion
# ---------------------------------------------------------------------------

def parse_skill_formula(formula):
    """Parse '@str, @dex, @agl, Ulandus:2, Aralius:2' -> (stat1, stat2, stat3, sunsign_str)."""
    stats = []
    sunsigns_by_bonus = {}
    for part in [p.strip() for p in (formula or "").split(",") if p.strip()]:
        if part.startswith("@"):
            code = part[1:].upper()
            stats.append(code)
        else:
            if ":" in part:
                sname, val = part.split(":", 1)
                bonus = val.strip()
            else:
                sname, bonus = part, "1"
            abbr = SUNSIGN_ABBREV.get(sname.strip().lower(), sname.strip()[:3].title())
            sunsigns_by_bonus.setdefault(bonus, []).append(abbr)

    while len(stats) < 3:
        stats.append("")

    if sunsigns_by_bonus:
        chunks = [f"{'/'.join(abbrs)}+{bonus}" for bonus, abbrs in sunsigns_by_bonus.items()]
        sunsign_str = "; ".join(chunks)
    else:
        sunsign_str = "None"

    return stats[0], stats[1], stats[2], sunsign_str


def split_specialized_skill(raw_name):
    """Convert Foundry 'Shortbow (Bow)' or 'Language: Hârnic' to HM3.5E (name, name_focus, name_displayed)."""
    raw = raw_name.strip()
    if ":" in raw:
        base, focus = [x.strip() for x in raw.split(":", 1)]
        return base, focus, f"{base} - {focus}"
    m = re.match(r"^(.+?)\s*\(([^)]+)\)$", raw)
    if m:
        focus = m.group(1).strip()
        base = m.group(2).strip()
        # Note: Trapping (Hunting) has base Hunting or Trapping; keep Trapping - Hunting if Hunting is category
        if focus.lower() == "trapping" and base.lower() == "hunting":
            return "Trapping", "Hunting", "Trapping - Hunting"
        return base, focus, f"{base} - {focus}"
    if raw == "Round Shield":
        return "Shield", "Round Shield", "Shield - Round Shield"
    return raw, "", raw


def map_weapon_subtype(assoc_skill, item_name):
    txt = f"{assoc_skill} {item_name}".lower()
    for key, subtype in WEAPON_SUBTYPE_FROM_SKILL.items():
        if key in txt:
            return subtype
    return "Sword"


def resolve_weapon_skill_display(assoc_skill, actor_skills):
    """Find matching skill's name_displayed on this actor."""
    if not assoc_skill:
        return "Unarmed"
    _, _, desired_disp = split_specialized_skill(assoc_skill)
    for sk in actor_skills:
        _, _, disp = split_specialized_skill(sk["name"])
        if disp.lower() == desired_disp.lower():
            return disp
    # fallback match on base name
    base_target = desired_disp.split(" - ")[0].lower()
    for sk in actor_skills:
        base, _, disp = split_specialized_skill(sk["name"])
        if base.lower() == base_target:
            return disp
    return desired_disp


def locations_to_coverage(locations):
    codes = []
    seen = set()
    for loc in locations or []:
        c = FOUNDRY_LOC_TO_CODE.get(loc.strip().lower())
        if c and c not in seen:
            seen.add(c)
            codes.append(c)
    return " ".join(codes)


def compute_zone_protection(armorgear_items):
    """Sum Blunt/Edge/Point/Fire protection per location code from equipped armorgear."""
    totals = {}
    for it in armorgear_items:
        sysd = it["system"]
        if not sysd.get("isEquipped", False):
            continue
        prot = sysd.get("protection", {})
        b = int(prot.get("blunt", 0) or 0)
        e = int(prot.get("edged", 0) or 0)
        p = int(prot.get("piercing", 0) or 0)
        f = int(prot.get("fire", 0) or 0)
        for loc in sysd.get("locations", []):
            code = FOUNDRY_LOC_TO_CODE.get(loc.strip().lower())
            if not code:
                continue
            cur = totals.setdefault(code.lower(), {"b": 0, "e": 0, "p": 0, "f": 0})
            cur["b"] += b
            cur["e"] += e
            cur["p"] += p
            cur["f"] += f
            if code.lower() == "tx":
                for alias in ("ch", "bk"):
                    acur = totals.setdefault(alias, {"b": 0, "e": 0, "p": 0, "f": 0})
                    acur["b"] += b
                    acur["e"] += e
                    acur["p"] += p
                    acur["f"] += f
    return totals


def parse_height_inches(h_str):
    if not h_str:
        return ""
    m = re.search(r"(\d+)\s*(?:feet|ft|')\s*(\d+)?", h_str, re.I)
    if m:
        feet = int(m.group(1))
        inches = int(m.group(2) or 0)
        return str(feet * 12 + inches)
    return h_str.strip()


def format_bep(b, e, p):
    bs = str(b) if b > 0 else "*"
    es = str(e) if e > 0 else "*"
    ps = str(p) if p > 0 else "*"
    return bs, es, ps, f"{bs}/{es}/{ps}"


def primary_aspect_idx(b, e, p):
    # 0 = Blunt, 1 = Edge, 2 = Point
    best_idx, best_val = 0, b
    if e > best_val:
        best_idx, best_val = 1, e
    if p > best_val:
        best_idx, best_val = 2, p
    return best_idx


# ---------------------------------------------------------------------------
# Step 2.3: Build <charsheet> (6 PreGen PCs)
# ---------------------------------------------------------------------------

def build_charsheet(root_charsheet, pc_id, actor_json, full_name):
    sysd = actor_json["system"]
    items = actor_json.get("items", [])
    skills = [i for i in items if i["type"] == "skill"]
    armors = [i for i in items if i["type"] == "armorgear"]
    weapons = [i for i in items if i["type"] == "weapongear"]
    missiles = [i for i in items if i["type"] == "missilegear"]
    miscs = [i for i in items if i["type"] in ("miscgear", "containergear")]
    traits = [i for i in items if i["type"] == "trait"]
    invocations = [i for i in items if i["type"] == "invocation"]

    cs = ET.SubElement(root_charsheet, pc_id)
    sub_typed(cs, "chardbversion", "number", 2)
    sub_typed(cs, "locked", "number", 0)
    sub_typed(cs, "name", "string", full_name)
    sub_typed(cs, "portrait", "token", f"campaign/images/{full_name} Headshot.webp")
    sub_typed(cs, "token", "token", f"campaign/tokens/{full_name} Token.webp")
    sub_typed(cs, "token3Dflat", "token", f"campaign/images/{full_name}.webp")

    # Abilities
    ab_src = sysd.get("abilities", {})
    str_v = int(ab_src.get("strength", {}).get("base", 10))
    sta_v = int(ab_src.get("stamina", {}).get("base", 10))
    wil_v = int(ab_src.get("will", {}).get("base", 10))
    end_v = int(round((str_v + sta_v + wil_v) / 3.0))

    ab_node = ET.SubElement(cs, "abilities")
    for key, title in PC_ABILITY_KEYS:
        val = end_v if key == "endurance" else int(ab_src.get(key, {}).get("base", 10))
        el = ET.SubElement(ab_node, key)
        sub_typed(el, "base", "number", val)
        sub_typed(el, "bonus", "number", 0)
        sub_typed(el, "group", "string", "physical")
        sub_typed(el, "name", "string", title)
        sub_typed(el, "score", "number", val)

    # Speed, Initiative, HP
    move_base = int(sysd.get("move", {}).get("base", 60))
    speed_el = ET.SubElement(cs, "speed")
    sub_typed(speed_el, "total", "number", round(move_base / 5))

    init_ml = next((int(s["system"].get("masteryLevel", 50)) for s in skills if s["name"] == "Initiative"), 50)
    init_el = ET.SubElement(cs, "initiative")
    sub_typed(init_el, "total", "number", init_ml)

    hp_el = ET.SubElement(cs, "hp")
    sub_typed(hp_el, "total", "number", end_v)
    sub_typed(hp_el, "fatigue", "number", 0)
    sub_typed(hp_el, "wounds", "number", 0)
    sub_typed(hp_el, "penalty_physical", "number", 0)
    sub_typed(hp_el, "penalty_universal", "number", 0)

    # Background & Bio
    desc_kv = extract_kv_table(sysd.get("description", ""))
    bio_kv = extract_kv_table(sysd.get("biography", ""))
    ritual_skills = [s for s in skills if s["system"].get("type") == "Ritual"]
    primary_ritual = max(ritual_skills, key=lambda s: s["system"].get("ritual", {}).get("piety", 0), default=None)

    bg = ET.SubElement(cs, "background")
    gender = (sysd.get("gender") or "").strip()
    if not gender and full_name == "Harlin of Kleve":
        gender = "Male"
    sunsign = (sysd.get("sunsign") or "").strip()
    sub_typed(bg, "species", "string", sysd.get("species", "Human"))
    sub_typed(bg, "gender", "string", gender)
    sub_typed(bg, "sunsign", "string", sunsign)
    sub_typed(bg, "sunsign_main", "string", sunsign or "None")
    sub_typed(bg, "sunsign_cusp", "string", "None")
    sub_typed(bg, "culture", "string", desc_kv.get("Culture", "Feudal"))
    sub_typed(bg, "class", "string", desc_kv.get("Social Class", ""))
    occ = (sysd.get("occupation") or desc_kv.get("Apparent Occupation") or "").strip()
    sub_typed(bg, "occupation", "string", occ)
    sub_typed(bg, "height", "string", parse_height_inches(desc_kv.get("Height", "")))
    sub_typed(bg, "weight", "string", desc_kv.get("Weight", ""))
    sub_typed(bg, "frame", "string", desc_kv.get("Frame", ""))
    app_com = desc_kv.get("Appearance/Comeliness", "")
    sub_typed(bg, "complexion", "string", app_com)
    sub_typed(bg, "comeliness", "string", app_com)
    sub_typed(bg, "color_hair", "string", desc_kv.get("Hair Color", ""))
    sub_typed(bg, "color_eye", "string", desc_kv.get("Eye Color", ""))
    sub_typed(bg, "birthdate", "string", bio_kv.get("Birthdate", ""))
    sub_typed(bg, "birthplace", "string", bio_kv.get("Birthplace", ""))
    sub_typed(bg, "siblingrank", "string", bio_kv.get("Sibling Rank", ""))
    sub_typed(bg, "parent", "string", bio_kv.get("Parent(s)", ""))
    sub_typed(bg, "parentocc", "string", bio_kv.get("Parent Occupation", ""))
    sub_typed(bg, "clanhead", "string", bio_kv.get("Clanhead", ""))
    sub_typed(bg, "estrangement", "string", bio_kv.get("Estrangement", ""))

    if primary_ritual:
        deity_name = primary_ritual["name"]
        piety_val = int(primary_ritual["system"].get("ritual", {}).get("piety", 0))
        sub_typed(bg, "deity", "string", deity_name)
        sub_typed(bg, "piety", "string", str(piety_val))
        if invocations:
            sub_typed(bg, "cleric_of", "string", deity_name)
        pl = ET.SubElement(cs, "pietylist")
        p1 = ET.SubElement(pl, "id-00001")
        sub_typed(p1, "name", "string", deity_name)
        sub_typed(p1, "piety", "number", piety_val)
        sub_typed(p1, "primary", "number", 1)

    # Extract Life Story text after <h1>Life Story</h1>
    bio_html = sysd.get("biography", "") or ""
    ls_split = re.split(r"<h1[^>]*>\s*Life Story\s*</h1>", bio_html, maxsplit=1, flags=re.I)
    if len(ls_split) == 2:
        notes_plain = html_to_plain_text(ls_split[1])
        sub_typed(bg, "notes", "string", notes_plain)

    # Medical & Mental Traits
    med_traits = []
    men_traits = []
    for tr in traits:
        ttype = (tr["system"].get("type") or "").lower()
        tname = tr["name"]
        if ttype == "mental":
            men_traits.append(tname)
        else:
            med_traits.append(tname)

    bio_med = bio_kv.get("Medical Traits", "").strip()
    if bio_med and bio_med.lower() != "none" and not med_traits:
        med_traits.append(bio_med)
    bio_psy = bio_kv.get("Psyche Traits", "").strip()
    if bio_psy and bio_psy.lower() != "none" and not men_traits:
        men_traits.append(bio_psy)

    if med_traits:
        mt_el = ET.SubElement(cs, "medicaltraitlist")
        for idx, tname in enumerate(med_traits, 1):
            node = ET.SubElement(mt_el, f"id-{idx:05d}")
            sub_typed(node, "name", "string", tname)
    if men_traits:
        mt_el = ET.SubElement(cs, "mentaltraitlist")
        for idx, tname in enumerate(men_traits, 1):
            node = ET.SubElement(mt_el, f"id-{idx:05d}")
            sub_typed(node, "name", "string", tname)

    # Skills & Skillgroups
    used_groups = set()
    sk_list_el = ET.SubElement(cs, "skilllist")
    for idx, sk in enumerate(skills, 1):
        sk_sys = sk["system"]
        f_type = sk_sys.get("type", "Physical")
        grp_name = FOUNDRY_SKILLTYPE_MAP.get(f_type, "Physical")
        if sk["name"].startswith("Language:") or sk["name"].startswith("Script:"):
            grp_name = "Communication"
        used_groups.add(grp_name)
        groupid, _ = SKILLGROUP_META.get(grp_name, ("10", grp_name))

        name_base, name_focus, name_disp = split_specialized_skill(sk["name"])
        sb_val = int(sk_sys.get("skillBase", {}).get("value", 10) or 10)
        ml_val = int(sk_sys.get("masteryLevel", sb_val) or sb_val)
        st1, st2, st3, sunsign_str = parse_skill_formula(sk_sys.get("skillBase", {}).get("formula", ""))

        sk_el = ET.SubElement(sk_list_el, f"id-{idx:05d}")
        sub_typed(sk_el, "group", "string", grp_name)
        sub_typed(sk_el, "groupid", "string", groupid)
        sub_typed(sk_el, "misc", "number", 0)
        sub_typed(sk_el, "name", "string", name_base)
        if name_focus:
            sub_typed(sk_el, "name_focus", "string", name_focus)
        sub_typed(sk_el, "name_displayed", "string", name_disp)
        sub_typed(sk_el, "sb", "number", sb_val)
        sub_typed(sk_el, "shortcut", "number", 0)
        sub_typed(sk_el, "stat", "string", st1)
        sub_typed(sk_el, "stat2", "string", st2)
        sub_typed(sk_el, "stat3", "string", st3)
        sub_typed(sk_el, "sunsign", "string", sunsign_str)
        sub_typed(sk_el, "total", "number", ml_val)

    sg_el = ET.SubElement(cs, "skillgroup")
    for idx, grp_name in enumerate(sorted(used_groups, key=lambda g: SKILLGROUP_META.get(g, ("99", g))[0]), 1):
        g_node = ET.SubElement(sg_el, f"id-{idx:05d}")
        sub_typed(g_node, "name", "string", grp_name)

    # Inventory & Weapons
    # Map missilegear by assocSkill so bows receive ranged damage/ranges cleanly
    missile_by_skill = {}
    for ms in missiles:
        ask = ms["system"].get("assocSkill", "")
        missile_by_skill.setdefault(ask.lower(), []).append(ms)

    inv_el = ET.SubElement(cs, "inventorylist")
    wpn_el = ET.SubElement(cs, "weaponlist")

    # Standard id-00001 Unarmed weaponlist entry
    u_el = ET.SubElement(wpn_el, "id-00001")
    u_acts = ET.SubElement(u_el, "actionlist")
    for uidx, (uname, b, e, p, ma, md) in enumerate([
        ("Head", "1", "0", "0", "0", "0"),
        ("Hand / Arm", "0", "*", "*", "0", "15"),
        ("Foot/Leg/Knee", "1", "*", "*", "5", "5"),
    ], 1):
        ua = ET.SubElement(u_acts, f"id-{uidx:05d}")
        sub_typed(ua, "aimzone", "number", 0)
        sub_typed(ua, "ammo", "number", 0)
        sub_typed(ua, "atktype", "number", 0)
        sub_typed(ua, "dmg_aspect", "number", 0)
        sub_typed(ua, "dmg_bep", "string", f"{b}/{e}/{p}")
        sub_typed(ua, "dmg_blunt", "string", b)
        sub_typed(ua, "dmg_edge", "string", e)
        sub_typed(ua, "dmg_point", "string", p)
        sub_typed(ua, "maxammo", "number", 0)
        sub_typed(ua, "mod_atk", "string", ma)
        sub_typed(ua, "mod_def", "string", md)
        sub_typed(ua, "mod_hm", "string", "0")
        sub_typed(ua, "name", "string", uname)
        sub_typed(ua, "range_bracket", "number", 0)
        sub_typed(ua, "skill", "string", "Unarmed")
    sub_typed(u_el, "atktype", "number", 0)
    sub_typed(u_el, "carried", "number", 1)
    sub_typed(u_el, "handling", "number", 0)
    sub_typed(u_el, "isidentified", "number", 1)
    sub_typed(u_el, "name", "string", "Unarmed")
    sub_typed(u_el, "skill", "string", "Unarmed")

    inv_idx = 0
    wpn_idx = 1
    equipped_wt = 0.0
    carried_wt = 0.0

    # Armors
    for arm in armors:
        inv_idx += 1
        asys = arm["system"]
        qty = max(1, int(asys.get("quantity", 1) or 1))
        wt = float(asys.get("weight", 0) or 0)
        carried_state = 2 if asys.get("isEquipped") else (1 if asys.get("isCarried") else 0)
        if carried_state == 2:
            equipped_wt += wt * qty
        elif carried_state == 1:
            carried_wt += wt * qty
        prot = asys.get("protection", {})
        cov = locations_to_coverage(asys.get("locations", []))

        inode = ET.SubElement(inv_el, f"id-{inv_idx:05d}")
        sub_typed(inode, "armor_blunt", "number", int(prot.get("blunt", 0) or 0))
        sub_typed(inode, "armor_edge", "number", int(prot.get("edged", 0) or 0))
        sub_typed(inode, "armor_point", "number", int(prot.get("piercing", 0) or 0))
        sub_typed(inode, "armor_fire", "number", int(prot.get("fire", 0) or 0))
        sub_typed(inode, "armor_coverage", "string", cov)
        sub_typed(inode, "armor_size", "number", int(asys.get("size", 6) or 6))
        sub_typed(inode, "carried", "number", carried_state)
        val = asys.get("value", 0)
        if val:
            sub_typed(inode, "cost", "string", f"{val}d")
        sub_typed(inode, "count", "number", qty)
        sub_typed(inode, "locked", "number", 1)
        sub_typed(inode, "name", "string", arm["name"])
        sub_typed(inode, "nonid_name", "string", arm["name"])
        sub_typed(inode, "subtype", "string", asys.get("material", "Cloth"))
        sub_typed(inode, "type", "string", "Armor")
        sub_typed(inode, "weight", "number", round(wt, 2))
        sub_typed(inode, "weight_base", "number", round(wt, 2))

    # Weapons (including merged ranged stats if bow)
    for wpn in weapons:
        wsys = wpn["system"]
        assoc = wsys.get("assocSkill", "")
        if assoc.lower() == "unarmed":
            # Ryssi's innate Hand/Arm is already covered by Unarmed id-00001
            continue
        inv_idx += 1
        inv_id = f"id-{inv_idx:05d}"
        qty = max(1, int(wsys.get("quantity", 1) or 1))
        wt = float(wsys.get("weight", 0) or 0)
        carried_state = 2 if wsys.get("isEquipped") else (1 if wsys.get("isCarried") else 0)
        if carried_state == 2:
            equipped_wt += wt * qty
        elif carried_state == 1:
            carried_wt += wt * qty

        subtype = map_weapon_subtype(assoc, wpn["name"])
        is_bow = (subtype == "Bow")
        skill_disp = resolve_weapon_skill_display(assoc, skills)

        b_v = int(wsys.get("blunt", 0) or 0)
        e_v = int(wsys.get("edged", 0) or 0)
        p_v = int(wsys.get("piercing", 0) or 0)
        bs, es, ps, bep = format_bep(b_v, e_v, p_v)
        m_atk = str(int(wsys.get("attack", 0) or 0))
        m_def = str(int(wsys.get("defense", 0) or 0))
        wq = int(wsys.get("weaponQuality", 10) or 10)

        inode = ET.SubElement(inv_el, inv_id)
        sub_typed(inode, "armor_blunt", "number", 0)
        sub_typed(inode, "armor_edge", "number", 0)
        sub_typed(inode, "armor_fire", "number", 0)
        sub_typed(inode, "armor_point", "number", 0)
        sub_typed(inode, "carried", "number", carried_state)
        val = wsys.get("value", 0)
        if val:
            sub_typed(inode, "cost", "string", f"{val}d")
        sub_typed(inode, "count", "number", qty)
        sub_typed(inode, "dmg_blunt", "string", bs)
        sub_typed(inode, "dmg_edge", "string", es)
        sub_typed(inode, "dmg_point", "string", ps)
        sub_typed(inode, "locked", "number", 1)
        sub_typed(inode, "mod_atk", "string", m_atk)
        sub_typed(inode, "mod_def", "string", m_def)
        sub_typed(inode, "mod_hm", "string", "*")
        sub_typed(inode, "name", "string", wpn["name"])
        sub_typed(inode, "nonid_name", "string", wpn["name"])
        sub_typed(inode, "quality", "number", wq)
        sub_typed(inode, "subtype", "string", subtype)
        sub_typed(inode, "type", "string", "Weapon")
        sub_typed(inode, "weight", "number", round(wt, 2))

        matched_missiles = missile_by_skill.get(assoc.lower(), []) if is_bow else []
        actor_skill_names = {s["name"].strip().lower() for s in skills}
        bow_melee_skill = "Spear" if "spear" in actor_skill_names else ("Club" if "club" in actor_skill_names else skill_disp)
        if is_bow and matched_missiles:
            ms = matched_missiles[0]["system"]
            rng = ms.get("range", {})
            imp = ms.get("impact", {})
            max_imp = str(int(imp.get("short", 6) or 6))
            sub_typed(inode, "ammo_name", "string", "Arrow")
            sub_typed(inode, "dmg_blunt_ranged", "string", "*")
            sub_typed(inode, "dmg_edge_ranged", "string", "*")
            sub_typed(inode, "dmg_point_ranged", "string", max_imp)
            sub_typed(inode, "properties", "string", "High Velocity Missile")
            sub_typed(inode, "range_short", "string", str(round(float(rng.get("short", 100)) / 5)))
            sub_typed(inode, "range_medium", "string", str(round(float(rng.get("medium", 200)) / 5)))
            sub_typed(inode, "range_long", "string", str(round(float(rng.get("long", 400)) / 5)))
            sub_typed(inode, "range_extreme", "string", str(round(float(rng.get("extreme", 800)) / 5)))
            sub_typed(inode, "skill_melee", "string", bow_melee_skill)
            sub_typed(inode, "skill_ranged", "string", skill_disp)
        else:
            sub_typed(inode, "skill_melee", "string", skill_disp)
            sub_typed(inode, "skill_ranged", "string", "Throwing")

        # Weaponlist entry
        wpn_idx += 1
        wnode = ET.SubElement(wpn_el, f"id-{wpn_idx:05d}")
        wacts = ET.SubElement(wnode, "actionlist")
        act_id = 0
        if is_bow and matched_missiles:
            ms = matched_missiles[0]["system"]
            rng = ms.get("range", {})
            imp = ms.get("impact", {})
            max_imp = str(int(imp.get("short", 6) or 6))
            ammo_qty = int(ms.get("quantity", 12) or 12)
            act_id += 1
            ra = ET.SubElement(wacts, f"id-{act_id:05d}")
            sub_typed(ra, "aimzone", "number", 1)
            sub_typed(ra, "ammo", "number", 0)
            sub_typed(ra, "ammo_name", "string", "Arrow")
            sub_typed(ra, "ammocounter", "number", ammo_qty)
            sub_typed(ra, "atktype", "number", 1)
            sub_typed(ra, "dmg_aspect", "number", 2)
            sub_typed(ra, "dmg_bep", "string", f"*/*/{max_imp}")
            sub_typed(ra, "dmg_blunt", "string", "*")
            sub_typed(ra, "dmg_edge", "string", "*")
            sub_typed(ra, "dmg_point", "string", max_imp)
            sub_typed(ra, "maxammo", "number", ammo_qty)
            sub_typed(ra, "mod_atk", "string", m_atk)
            sub_typed(ra, "mod_def", "string", m_def)
            sub_typed(ra, "mod_hm", "string", "n/a")
            sub_typed(ra, "name", "string", "Arrow")
            sub_typed(ra, "properties", "string", "High Velocity Missile")
            sub_typed(ra, "range_bracket", "number", 0)
            sub_typed(ra, "range_short", "string", str(round(float(rng.get("short", 100)) / 5)))
            sub_typed(ra, "range_medium", "string", str(round(float(rng.get("medium", 200)) / 5)))
            sub_typed(ra, "range_long", "string", str(round(float(rng.get("long", 400)) / 5)))
            sub_typed(ra, "range_extreme", "string", str(round(float(rng.get("extreme", 800)) / 5)))
            sub_typed(ra, "skill", "string", skill_disp)

        act_id += 1
        ma = ET.SubElement(wacts, f"id-{act_id:05d}")
        sub_typed(ma, "aimzone", "number", 1)
        sub_typed(ma, "ammo", "number", 0)
        sub_typed(ma, "atktype", "number", 0)
        sub_typed(ma, "dmg_aspect", "number", primary_aspect_idx(b_v, e_v, p_v))
        sub_typed(ma, "dmg_bep", "string", bep)
        sub_typed(ma, "dmg_blunt", "string", bs)
        sub_typed(ma, "dmg_edge", "string", es)
        sub_typed(ma, "dmg_point", "string", ps)
        sub_typed(ma, "maxammo", "number", 0)
        sub_typed(ma, "mod_atk", "string", m_atk)
        sub_typed(ma, "mod_def", "string", m_def)
        sub_typed(ma, "mod_hm", "string", "*")
        sub_typed(ma, "name", "string", "Melee Attack")
        sub_typed(ma, "range_bracket", "number", 0)
        sub_typed(ma, "skill", "string", bow_melee_skill if is_bow else skill_disp)

        sub_typed(wnode, "atktype", "number", 1 if is_bow else 0)
        sub_typed(wnode, "carried", "number", carried_state)
        sub_typed(wnode, "handling", "number", 0)
        sub_typed(wnode, "isidentified", "number", 1)
        sub_typed(wnode, "name", "string", wpn["name"])
        sub_typed(wnode, "quality", "number", wq)
        sub_typed(wnode, "quality_current", "number", wq)
        sc = ET.SubElement(wnode, "shortcut", {"type": "windowreference"})
        ET.SubElement(sc, "class").text = "item"
        ET.SubElement(sc, "recordname").text = f"....inventorylist.{inv_id}"

    # Ammunition & Misc gear
    for gear in missiles + miscs:
        inv_idx += 1
        gsys = gear["system"]
        qty = max(1, int(gsys.get("quantity", 1) or 1))
        wt = float(gsys.get("weight", 0) or 0)
        carried_state = 2 if gsys.get("isEquipped") else (1 if gsys.get("isCarried") else 0)
        if carried_state == 2:
            equipped_wt += wt * qty
        elif carried_state == 1:
            carried_wt += wt * qty
        inode = ET.SubElement(inv_el, f"id-{inv_idx:05d}")
        sub_typed(inode, "armor_blunt", "number", 0)
        sub_typed(inode, "armor_edge", "number", 0)
        sub_typed(inode, "armor_fire", "number", 0)
        sub_typed(inode, "armor_point", "number", 0)
        sub_typed(inode, "carried", "number", carried_state)
        val = gsys.get("value", 0)
        if val:
            sub_typed(inode, "cost", "string", f"{val}d")
        sub_typed(inode, "count", "number", qty)
        sub_typed(inode, "locked", "number", 1)
        sub_typed(inode, "name", "string", gear["name"])
        sub_typed(inode, "nonid_name", "string", gear["name"])
        sub_typed(inode, "type", "string", "Adventuring Gear")
        sub_typed(inode, "weight", "number", round(wt, 2))
        notes = (gsys.get("notes") or "").strip()
        if notes:
            set_formattedtext(inode, "description", f"<p>{escape_text(notes)}</p>")

    # Encumbrance (matches manager_char_encumbrance_5E_hm3.lua)
    base_enc = round((str_v + sta_v + wil_v) / 3.0, 1)
    enc_limit = int(math.floor((base_enc / 2.0) + 0.5))
    load_wt = round(equipped_wt + carried_wt, 2)
    enc_level = int(load_wt // base_enc) if base_enc > 0 else 0
    enc_el = ET.SubElement(cs, "encumbrance")
    sub_typed(enc_el, "base", "number", base_enc)
    sub_typed(enc_el, "carried", "number", round(carried_wt, 2))
    sub_typed(enc_el, "encumbered", "number", enc_limit)
    sub_typed(enc_el, "equipped", "number", round(equipped_wt, 2))
    sub_typed(enc_el, "level", "number", enc_level)
    sub_typed(enc_el, "load", "number", load_wt)
    sub_typed(enc_el, "penalty", "number", enc_level)
    sub_typed(enc_el, "state", "string", f"Penalty: -{enc_level * 5}%")

    # Hitlocations & Defenses
    zone_prot = compute_zone_protection(armors)
    hl_el = ET.SubElement(cs, "hitlocations")
    hl_main = ET.SubElement(hl_el, "main")
    hl_rows = ET.SubElement(hl_main, "tablerows")
    for ridx, r in enumerate(HUMANOID_HIT_ROWS, 1):
        zp = zone_prot.get(r["loc"], {"b": 0, "e": 0, "p": 0, "f": 0})
        row = ET.SubElement(hl_rows, f"id-{ridx:05d}")
        sub_typed(row, "armor_blunt", "number", zp["b"])
        sub_typed(row, "armor_edge", "number", zp["e"])
        sub_typed(row, "armor_point", "number", zp["p"])
        sub_typed(row, "armor_fire", "number", zp["f"])
        sub_typed(row, "fromrange", "number", r["from"])
        sub_typed(row, "fromrange_high", "number", r["f_hi"])
        sub_typed(row, "fromrange_low", "number", r["f_lo"])
        sub_typed(row, "islateral", "number", r["lat"])
        sub_typed(row, "location", "string", r["loc"])
        sub_typed(row, "name", "string", r["res"])
        sub_typed(row, "result", "string", r["res"])
        sub_typed(row, "sortkey", "string", f"{r['rank']}_{r['res']}")
        sub_typed(row, "torange", "number", r["to"])
        sub_typed(row, "torange_high", "number", r["t_hi"])
        sub_typed(row, "torange_low", "number", r["t_lo"])

    def_el = ET.SubElement(cs, "defenses")
    ac_el = ET.SubElement(def_el, "ac")
    sub_typed(ac_el, "dexbonus", "string", "no")
    sub_typed(ac_el, "prof", "number", 1)
    sub_typed(ac_el, "total", "number", 10)
    al_el = ET.SubElement(def_el, "armorlist")
    for zidx, (zname, zcode) in enumerate(DEFENSE_ARMORLIST_ZONES, 1):
        zp = zone_prot.get(zcode.lower(), {"b": 0, "e": 0, "p": 0, "f": 0})
        zn = ET.SubElement(al_el, f"id-{zidx:05d}")
        sub_typed(zn, "armor_blunt", "number", zp["b"])
        sub_typed(zn, "armor_edge", "number", zp["e"])
        sub_typed(zn, "armor_fire", "number", zp["f"])
        sub_typed(zn, "armor_point", "number", zp["p"])
        sub_typed(zn, "name", "string", zname)

    # Powers (Invocations for Ryssi of Chert)
    if invocations:
        deity_name = invocations[0]["system"].get("diety", "Peoni") or "Peoni"
        pg_el = ET.SubElement(cs, "powergroup")
        pg1 = ET.SubElement(pg_el, "id-00001")
        sub_typed(pg1, "name", "string", deity_name)

        rit_sb = int(primary_ritual["system"].get("skillBase", {}).get("value", 16)) if primary_ritual else 16
        rit_ml = int(primary_ritual["system"].get("masteryLevel", 64)) if primary_ritual else 64

        pw_el = ET.SubElement(cs, "powers")
        for pidx, inv in enumerate(invocations, 1):
            isys = inv["system"]
            circle = int(isys.get("circle", 1) or 1)
            raw_desc = isys.get("description", "") or ""
            meta = {}
            for m in re.finditer(r"<td><b>(Time|Ritual|Range|Duration):</b>\s*(.*?)</td>", raw_desc, re.I | re.DOTALL):
                meta[m.group(1).lower()] = html_to_plain_text(m.group(2))
            # Strip first metadata table
            body_html = re.sub(r"^\s*<table>.*?</table>", "", raw_desc, count=1, flags=re.I | re.DOTALL)
            parser = FguHtmlSanitizer()
            parser.feed(body_html)
            parser.close()
            fgu_desc = parser.get_fgu_xml()

            clean_name = re.sub(r"\s*\([IVX]+\)\s*$", "", inv["name"]).strip()
            pnode = ET.SubElement(pw_el, f"id-{pidx:05d}")
            acts = ET.SubElement(pnode, "actions")
            a1 = ET.SubElement(acts, "id-00001")
            sub_typed(a1, "type", "string", "cast")
            if meta.get("time"):
                sub_typed(pnode, "castingtime", "string", meta["time"])
            if meta.get("ritual"):
                sub_typed(pnode, "ritual", "string", meta["ritual"])
            if meta.get("range"):
                sub_typed(pnode, "range", "string", meta["range"])
            if meta.get("duration"):
                sub_typed(pnode, "duration", "string", meta["duration"])
            sub_typed(pnode, "cml", "number", rit_ml)
            set_formattedtext(pnode, "description", fgu_desc)
            sub_typed(pnode, "group", "string", deity_name)
            sub_typed(pnode, "level", "number", circle)
            sub_typed(pnode, "misc", "number", 0)
            sub_typed(pnode, "name", "string", clean_name)
            sub_typed(pnode, "sb", "number", rit_sb)
            sub_typed(pnode, "school", "string", deity_name)
            sub_typed(pnode, "shortcut", "number", 0)
            sub_typed(pnode, "system", "string", "ritual")
            sub_typed(pnode, "total", "number", rit_ml - (circle * 5))


# ---------------------------------------------------------------------------
# Step 2.4: Build <npc> (4 Combat NPCs)
# ---------------------------------------------------------------------------

def format_aspects_text(b, e, p):
    parts = []
    if b > 0:
        parts.append(f"{b}B")
    if e > 0:
        parts.append(f"{e}E")
    if p > 0:
        parts.append(f"{p}P")
    return " ".join(parts) if parts else "1B"


def build_npc(root_npc, npc_id, actor_json, npc_name):
    sysd = actor_json["system"]
    is_creature = (actor_json.get("type") == "creature")
    items = actor_json.get("items", [])
    skills = [i for i in items if i["type"] == "skill"]
    armors = [i for i in items if i["type"] == "armorgear"]
    weapons = [i for i in items if i["type"] == "weapongear"]
    missiles = [i for i in items if i["type"] == "missilegear"]
    armor_locs = [i for i in items if i["type"] == "armorlocation"]

    npc = ET.SubElement(root_npc, npc_id)
    sub_typed(npc, "group", "string", "A Shower of Silver")
    sub_typed(npc, "locked", "number", 1)
    sub_typed(npc, "name", "string", npc_name)
    sub_typed(npc, "nonid_name", "string", "Black Bear" if is_creature else npc_name)
    sub_typed(npc, "size", "string", "Large" if is_creature else "Medium")
    sub_typed(npc, "type", "string", "Beast (Bear)" if is_creature else "Human")

    if is_creature:
        sub_typed(npc, "token", "token", "campaign/tokens/Black Bear Token.webp")
        sub_typed(npc, "picture", "token", "campaign/images/Black Bear Headshot.webp")
        sub_typed(npc, "token3Dflat", "token", "campaign/images/Black Bear.webp")
    else:
        letter = npc_name[0].lower()
        sub_typed(npc, "token", "token", f"tokens/Medium/{letter}.png@Letter Tokens")
        sub_typed(npc, "picture", "token", f"tokens/Medium/{letter}.png@Letter Tokens")

    # Abilities
    ab_src = sysd.get("abilities", {})
    str_v = int(ab_src.get("strength", {}).get("base", 10))
    sta_v = int(ab_src.get("stamina", {}).get("base", 10))
    wil_v = int(ab_src.get("will", {}).get("base", 10))
    end_v = int(sysd.get("endurance", {}).get("base", 0) or round((str_v + sta_v + wil_v) / 3.0))
    move_v = round(int(sysd.get("move", {}).get("base", 60)) / 5.0)
    swim_v = int(round((str_v + sta_v) / 2.0)) if is_creature else 8

    ab_node = ET.SubElement(npc, "abilities")
    for key, title in NPC_ABILITY_KEYS:
        if key == "endurance":
            val = end_v
        elif key == "move":
            val = move_v
        elif key == "fly":
            val = 0
        elif key == "swim":
            val = swim_v
        else:
            val = int(ab_src.get(key, {}).get("base", 10))
        el = ET.SubElement(ab_node, key)
        sub_typed(el, "name", "string", title)
        if val > 0 or key in ("move", "endurance"):
            sub_typed(el, "score", "number", val)

    sub_typed(npc, "hp", "number", end_v)
    init_ml = next((int(s["system"].get("masteryLevel", 50)) for s in skills if s["name"] == "Initiative"), 50)
    init_el = ET.SubElement(npc, "initiative")
    sub_typed(init_el, "total", "number", init_ml)

    # Map weapons to combat skills for NPC skill string & actions
    weapon_aspects_by_skill = {}
    for wpn in weapons:
        ws = wpn["system"]
        ask = ws.get("assocSkill", wpn["name"])
        asp = format_aspects_text(int(ws.get("blunt", 0) or 0), int(ws.get("edged", 0) or 0), int(ws.get("piercing", 0) or 0))
        weapon_aspects_by_skill[ask.lower()] = asp

    # Strictly follow .agent/rules/npc-and-modules.md skill ordering:
    # 1. Initiative, 2. Dodge, 3. Unarmed, 4. Combat skills alphabetically (with aspects), 5. Standard skills alphabetically
    init_entry = None
    dodge_entry = None
    unarmed_entry = None
    combat_entries = []
    standard_entries = []

    skill_ml_map = {}
    for sk in skills:
        sname = sk["name"].strip()
        _, _, sdisp = split_specialized_skill(sname)
        ml = int(sk["system"].get("masteryLevel", 0) or 0)
        skill_ml_map[sname.lower()] = ml
        skill_ml_map[sdisp.lower()] = ml
        stype = sk["system"].get("type", "Physical")
        low = sname.lower()

        if low == "initiative":
            init_entry = f"Initiative {ml}"
        elif low == "dodge":
            dodge_entry = f"Dodge {ml}"
        elif low == "unarmed":
            unarmed_entry = f"Unarmed {ml}"
        elif stype == "Combat" or low in weapon_aspects_by_skill:
            asp = weapon_aspects_by_skill.get(low, "")
            # Clean name like "Taburi (Dagger)" -> "Taburi" or "Falchion"
            short_sk = re.sub(r"\s*\([^)]+\)\s*$", "", sname).strip()
            entry = f"{short_sk} {ml} {asp}".strip() if asp else f"{short_sk} {ml}"
            combat_entries.append((short_sk.lower(), entry))
        else:
            standard_entries.append((sname.lower(), f"{sname} {ml}"))

    ordered_skills = []
    if init_entry:
        ordered_skills.append(init_entry)
    if dodge_entry:
        ordered_skills.append(dodge_entry)
    if unarmed_entry:
        ordered_skills.append(unarmed_entry)
    ordered_skills.extend(e for _, e in sorted(combat_entries, key=lambda x: x[0]))
    ordered_skills.extend(e for _, e in sorted(standard_entries, key=lambda x: x[0]))
    sub_typed(npc, "skills", "string", ", ".join(ordered_skills))

    # Actions (ONLY combat weapons / natural attacks, never Dodge/Weaponcraft)
    acts_el = ET.SubElement(npc, "actions")
    act_idx = 0
    missile_by_skill = {}
    for ms in missiles:
        missile_by_skill.setdefault(ms["system"].get("assocSkill", "").lower(), []).append(ms)

    for wpn in weapons:
        act_idx += 1
        ws = wpn["system"]
        ask = ws.get("assocSkill", wpn["name"])
        base_ml = skill_ml_map.get(ask.lower())
        if base_ml is None:
            _, _, disp = split_specialized_skill(ask)
            base_ml = skill_ml_map.get(disp.lower(), 50)
        aml = base_ml + int(ws.get("attack", 0) or 0)
        dml = base_ml + int(ws.get("defense", 0) or 0)
        asp = format_aspects_text(int(ws.get("blunt", 0) or 0), int(ws.get("edged", 0) or 0), int(ws.get("piercing", 0) or 0))
        desc_parts = [f"Melee AML: {aml}, DML: {dml}, Aspects: {asp}"]

        # Check matching missilegear (e.g., Jedes Guard Spear thrown) or Taburi thrown
        matched_ms = missile_by_skill.get(ask.lower(), [])
        if matched_ms:
            msys = matched_ms[0]["system"]
            r_imp = int(msys.get("impact", {}).get("short", 6) or 6)
            r_asp = (msys.get("weaponAspect", "P") or "P")[0].upper()
            desc_parts.append(f"Ranged AML: {base_ml}, Aspects: {r_imp}{r_asp}")
        elif wpn["name"].lower() == "taburi":
            desc_parts.append(f"Ranged AML: {aml}, Aspects: {asp}")

        an = ET.SubElement(acts_el, f"id-{act_idx:05d}")
        sub_typed(an, "name", "string", wpn["name"])
        sub_typed(an, "desc", "string", ", ".join(desc_parts))

    # Armor, Encumbrance & Hitlocations
    if is_creature:
        # Bear armorlocation values: B5 E2 P2 F4
        b_arm, e_arm, p_arm, f_arm = 5, 2, 2, 4
        if armor_locs:
            s0 = armor_locs[0]["system"]
            b_arm = int(s0.get("blunt", 5) or 5)
            e_arm = int(s0.get("edged", 2) or 2)
            p_arm = int(s0.get("piercing", 2) or 2)
            f_arm = int(s0.get("fire", 4) or 4)
        hl_el = ET.SubElement(npc, "hitlocations")
        sub_typed(hl_el, "armor_blunt", "number", b_arm)
        sub_typed(hl_el, "armor_edge", "number", e_arm)
        sub_typed(hl_el, "armor_fire", "number", f_arm)
        sub_typed(hl_el, "armor_point", "number", p_arm)
        trows = ET.SubElement(ET.SubElement(hl_el, "main"), "tablerows")
        for ridx, r in enumerate(QUADRUPED_HIT_ROWS, 1):
            row = ET.SubElement(trows, f"id-{ridx:05d}")
            sub_typed(row, "armor_blunt", "number", b_arm)
            sub_typed(row, "armor_edge", "number", e_arm)
            sub_typed(row, "armor_fire", "number", f_arm)
            sub_typed(row, "armor_point", "number", p_arm)
            sub_typed(row, "fromrange", "number", r["from"])
            sub_typed(row, "islateral", "number", r["lat"])
            sub_typed(row, "location", "string", r["loc"])
            sub_typed(row, "result", "string", r["res"])
            sub_typed(row, "torange", "number", r["to"])
    else:
        if armors:
            sub_typed(npc, "armor_worn", "string", ", ".join(sorted(a["name"] for a in armors)))
        eq_wt = 0.0
        inv_el = ET.SubElement(npc, "inventorylist")
        for aidx, arm in enumerate(armors, 1):
            asys = arm["system"]
            wt = float(asys.get("weight", 0) or 0)
            eq_wt += wt
            prot = asys.get("protection", {})
            inode = ET.SubElement(inv_el, f"id-{aidx:05d}")
            sub_typed(inode, "armor_blunt", "number", int(prot.get("blunt", 0) or 0))
            sub_typed(inode, "armor_coverage", "string", locations_to_coverage(asys.get("locations", [])))
            sub_typed(inode, "armor_edge", "number", int(prot.get("edged", 0) or 0))
            sub_typed(inode, "armor_fire", "number", int(prot.get("fire", 0) or 0))
            sub_typed(inode, "armor_point", "number", int(prot.get("piercing", 0) or 0))
            sub_typed(inode, "carried", "number", 2 if asys.get("isEquipped") else 1)
            sub_typed(inode, "count", "number", 1)
            sub_typed(inode, "locked", "number", 1)
            sub_typed(inode, "name", "string", arm["name"])
            sub_typed(inode, "nonid_name", "string", arm["name"])
            sub_typed(inode, "subtype", "string", asys.get("material", "Cloth"))
            sub_typed(inode, "type", "string", "Armor")
            sub_typed(inode, "weight", "number", round(wt, 2))
        for wpn in weapons:
            eq_wt += float(wpn["system"].get("weight", 0) or 0) * max(1, int(wpn["system"].get("quantity", 1) or 1))

        base_enc = round((str_v + sta_v + wil_v) / 3.0, 1)
        enc_lvl = int(eq_wt // base_enc) if base_enc > 0 else 0
        enc_el = ET.SubElement(npc, "encumbrance")
        sub_typed(enc_el, "equipped", "number", round(eq_wt, 1))
        sub_typed(enc_el, "level", "number", enc_lvl)
        sub_typed(enc_el, "load", "number", round(eq_wt, 1))
        sub_typed(enc_el, "penalty", "number", enc_lvl)
        sub_typed(enc_el, "state", "string", f"Penalty: -{enc_lvl * 5}%")

        zone_prot = compute_zone_protection(armors)
        hl_el = ET.SubElement(npc, "hitlocations")
        trows = ET.SubElement(ET.SubElement(hl_el, "main"), "tablerows")
        for ridx, r in enumerate(HUMANOID_HIT_ROWS, 1):
            zp = zone_prot.get(r["loc"], {"b": 0, "e": 0, "p": 0, "f": 0})
            row = ET.SubElement(trows, f"id-{ridx:05d}")
            sub_typed(row, "armor_blunt", "number", zp["b"])
            sub_typed(row, "armor_edge", "number", zp["e"])
            sub_typed(row, "armor_fire", "number", zp["f"])
            sub_typed(row, "armor_point", "number", zp["p"])
            sub_typed(row, "fromrange", "number", r["from"])
            if r["f_hi"] or r["t_hi"]:
                sub_typed(row, "fromrange_high", "number", r["f_hi"])
                sub_typed(row, "torange_high", "number", r["t_hi"])
            if r["f_lo"] or r["t_lo"]:
                sub_typed(row, "fromrange_low", "number", r["f_lo"])
                sub_typed(row, "torange_low", "number", r["t_lo"])
            if r["lat"]:
                sub_typed(row, "islateral", "number", 1)
            sub_typed(row, "location", "string", r["loc"])
            sub_typed(row, "result", "string", r["res"])
            sub_typed(row, "torange", "number", r["to"])

    # Formatted notes/description
    occ = (sysd.get("occupation") or "").strip()
    gender = (sysd.get("gender") or "").strip()
    sunsign = (sysd.get("sunsign") or "").strip()
    parts = []
    if occ or gender or sunsign:
        meta_bits = [x for x in [occ, gender, f"Sunsign: {sunsign}" if sunsign else ""] if x]
        parts.append(f"<p><b>Profile:</b> {escape_text(' | '.join(meta_bits))}</p>")
    bio_html = (sysd.get("biography") or "").strip()
    if bio_html:
        p_clean = FguHtmlSanitizer()
        p_clean.feed(bio_html)
        p_clean.close()
        parts.append(p_clean.get_fgu_xml())
    if not parts:
        parts.append(f"<p>{escape_text(npc_name)}</p>")
    set_formattedtext(npc, "text", "".join(parts))


# ---------------------------------------------------------------------------
# Reference Manual & Image Nodes
# ---------------------------------------------------------------------------

def add_image_record(image_root, img_id, title, filename, pins=None):
    node = ET.SubElement(image_root, img_id)
    sub_typed(node, "name", "string", title)
    sub_typed(node, "locked", "number", 1)
    img_el = sub_typed(node, "image", "image")
    ET.SubElement(img_el, "allowplayerdrawing").text = "on"
    layers_el = ET.SubElement(img_el, "layers")

    total_layers = 1 + (len(pins) if pins else 0)
    l0 = ET.SubElement(layers_el, "layer")
    ET.SubElement(l0, "name").text = filename
    ET.SubElement(l0, "id").text = "0"
    ET.SubElement(l0, "parentid").text = str(-total_layers)
    ET.SubElement(l0, "type").text = "image"
    ET.SubElement(l0, "bitmap").text = f"campaign/images/{filename}"

    if pins:
        for idx, pin in enumerate(pins, 1):
            lp = ET.SubElement(layers_el, "layer")
            ET.SubElement(lp, "name").text = pin["name"]
            ET.SubElement(lp, "id").text = str(idx)
            ET.SubElement(lp, "parentid").text = str(-(total_layers - idx))
            ET.SubElement(lp, "type").text = "shortcut"
            sc = ET.SubElement(lp, "shortcut")
            ET.SubElement(sc, "class").text = "referencemanualpage"
            ET.SubElement(sc, "record").text = pin["record"]
            ET.SubElement(lp, "matrix").text = f"1,0,0,0,0,1,0,0,0,0,1,0,{pin['x']},{pin['y']},0,1"


def add_embedded_image_block(blocks_el, block_id, caption, filename, recordname, order):
    b_el = ET.SubElement(blocks_el, block_id)
    sub_typed(b_el, "blocktype", "string", "image")
    sub_typed(b_el, "caption", "string", caption)
    sub_typed(b_el, "frame", "string", "picture")
    img_el = sub_typed(b_el, "image", "image")
    ET.SubElement(img_el, "allowplayerdrawing").text = "on"
    layers_el = ET.SubElement(img_el, "layers")
    l0 = ET.SubElement(layers_el, "layer")
    ET.SubElement(l0, "name").text = filename
    ET.SubElement(l0, "id").text = "0"
    ET.SubElement(l0, "parentid").text = "-1"
    ET.SubElement(l0, "type").text = "image"
    ET.SubElement(l0, "bitmap").text = f"campaign/images/{filename}"

    if recordname:
        link_el = sub_typed(b_el, "imagelink", "windowreference")
        ET.SubElement(link_el, "class").text = "imagewindow"
        ET.SubElement(link_el, "recordname").text = recordname

    sub_typed(b_el, "order", "number", order)


def add_singletext_block(blocks_el, block_id, fgu_xml, order):
    b_el = ET.SubElement(blocks_el, block_id)
    sub_typed(b_el, "blocktype", "string", "singletext")
    sub_typed(b_el, "order", "number", order)
    set_formattedtext(b_el, "text", fgu_xml)


def build_keywords(title, fgu_xml):
    plain = re.sub(r"<[^>]+>", " ", f"{title} {fgu_xml}")
    words = sorted({w.lower() for w in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]{3,}", plain)})
    return " ".join(words)


# ---------------------------------------------------------------------------
# Main Conversion Pipeline
# ---------------------------------------------------------------------------

def convert():
    copy_assets()

    root = ET.Element("root", {"version": "5.1", "dataversion": "20260124", "release": "8.1|CoreRPG:7"})

    # 1. Load upstream JSONs
    actor_jsons = {}
    for fn, name in [(fn, nm) for fn, _, nm in PREGEN_ACTORS] + NPC_ACTORS:
        with open(os.path.join(ACTORS_DIR, fn), encoding="utf-8") as f:
            data = json.load(f)
            actor_jsons[data["_id"]] = (data, name)

    journals = {}
    for jfn in os.listdir(JOURNALS_DIR):
        if jfn.endswith(".json"):
            with open(os.path.join(JOURNALS_DIR, jfn), encoding="utf-8") as f:
                jdata = json.load(f)
                journals[jdata["_id"]] = jdata

    with open(os.path.join(SCENES_DIR, "GM_Map_4giSA574KebG1aOy.json"), encoding="utf-8") as f:
        scene_json = json.load(f)

    # 2. Build <charsheet> and <npc>
    charsheet_root = ET.SubElement(root, "charsheet")
    foundry_actor_to_fgu = {}
    for idx, (fn, _, full_name) in enumerate(PREGEN_ACTORS, 1):
        with open(os.path.join(ACTORS_DIR, fn), encoding="utf-8") as f:
            adata = json.load(f)
        cid = f"id-{idx:05d}"
        foundry_actor_to_fgu[adata["_id"]] = ("charsheet", f"charsheet.{cid}", full_name)
        build_charsheet(charsheet_root, cid, adata, full_name)

    npc_root = ET.SubElement(root, "npc")
    for idx, (fn, npc_name) in enumerate(NPC_ACTORS, 1):
        with open(os.path.join(ACTORS_DIR, fn), encoding="utf-8") as f:
            adata = json.load(f)
        nid = f"id-{idx:05d}"
        foundry_actor_to_fgu[adata["_id"]] = ("npc", f"npc.{nid}", npc_name)
        build_npc(npc_root, nid, adata, npc_name)

    # 3. Assign IDs for <image> records and Reference Manual pages before resolving links
    image_specs = [
        ("id-00001", "Shower of Silver Map GM", "Shower of Silver Map GM.webp"),
        ("id-00002", "Letter to Sir Kodar", "Letter to Sir Kodar.webp"),
        ("id-00003", "The Prophecy", "The Prophecy.webp"),
        ("id-00004", "PreGen Characters", "PreGen Characters.webp"),
    ]
    next_img_idx = 5
    portrait_img_ids = {}
    for _, title in NPC_PORTRAITS:
        iid = f"id-{next_img_idx:05d}"
        image_specs.append((iid, title, f"{title}.webp"))
        portrait_img_ids[title.lower()] = iid
        next_img_idx += 1

    pregen_img_ids = {}
    for _, _, full_name in PREGEN_ACTORS:
        iid = f"id-{next_img_idx:05d}"
        image_specs.append((iid, full_name, f"{full_name}.webp"))
        pregen_img_ids[full_name] = iid
        next_img_idx += 1

    bear_img_id = f"id-{next_img_idx:05d}"
    image_specs.append((bear_img_id, "Black Bear", "Black Bear.webp"))

    # Map Reference Manual pages to deterministic refmanualdata IDs
    intro_journal = journals["09lMEwBLsvX886dD"]
    scen_journal = journals["In1njuaszlcNb9H3"]
    pregen_journal = journals["T0Zvm9e19175by6m"]

    intro_pages_by_id = {p["_id"]: p for p in intro_journal["pages"]}
    scen_pages_sorted = sorted(scen_journal["pages"], key=lambda p: p.get("sort", 0))
    pregen_pages_by_name = {p["name"]: p for p in pregen_journal["pages"] if p["type"] == "text"}

    intro_order = [
        ("5WQK6hq155mb93Da", "Overview", "id-00004", "PreGen Characters.webp"),
        ("znKIDLrOic2ODsAP", "HârnWorld Information", None, None),
        ("4xPTDOvsmY8I3XkB", "The Urnelt/Kyngen Feud", None, None),
        ("p1l74SksjeMWMvdg", "Yma the Goose Girl", None, None),
        ("DS1fVjBjyd08QoEq", "The Prophecy", "id-00003", "The Prophecy.webp"),
        ("i3XRucDuEhNmP03b", "Letter to Sir Kodar", "id-00002", "Letter to Sir Kodar.webp"),
        ("CPSs5khI9gpMFRZQ", "GM Map", "id-00001", "Shower of Silver Map GM.webp"),
        ("GNPwfGSz8Sx94i21", "Credits", None, None),
    ]

    foundry_page_to_fgu = {}
    ref_page_Counter = 0
    subchapter_defs = [
        ("Introduction & Background", []),
        ("Scenario", []),
        ("Pre-Generated Characters", []),
        ("NPCs & Cast", []),
    ]

    for pid, title, img_id, img_file in intro_order:
        ref_page_Counter += 1
        rid = f"id-{ref_page_Counter:05d}"
        foundry_page_to_fgu[f"JournalEntry.09lMEwBLsvX886dD.JournalEntryPage.{pid}"] = (
            "referencemanualpage", f"reference.refmanualdata.{rid}", title
        )
        pg = intro_pages_by_id[pid]
        raw_html = (pg.get("text") or {}).get("content") or ""
        if pid == "CPSs5khI9gpMFRZQ":
            raw_html = "<p>Interactive GM Map of Jedes Keep and surrounding territories. Click the embedded map to open the pinned FGU image window.</p>"
        subchapter_defs[0][1].append((rid, title, raw_html, img_id, img_file, None))

    for pg in scen_pages_sorted:
        ref_page_Counter += 1
        rid = f"id-{ref_page_Counter:05d}"
        foundry_page_to_fgu[f"JournalEntry.In1njuaszlcNb9H3.JournalEntryPage.{pg['_id']}"] = (
            "referencemanualpage", f"reference.refmanualdata.{rid}", pg["name"]
        )
        raw_html = (pg.get("text") or {}).get("content") or ""
        subchapter_defs[1][1].append((rid, pg["name"], raw_html, None, None, None))

    for fn, _, full_name in PREGEN_ACTORS:
        pg = pregen_pages_by_name[f"Character: {full_name}"]
        ref_page_Counter += 1
        rid = f"id-{ref_page_Counter:05d}"
        foundry_page_to_fgu[f"JournalEntry.T0Zvm9e19175by6m.JournalEntryPage.{pg['_id']}"] = (
            "referencemanualpage", f"reference.refmanualdata.{rid}", full_name
        )
        with open(os.path.join(ACTORS_DIR, fn), encoding="utf-8") as f:
            aid = json.load(f)["_id"]
        _, cs_rec, _ = foundry_actor_to_fgu[aid]
        extra = [("charsheet", cs_rec, f"Character Sheet: {full_name}")]
        raw_html = (pg.get("text") or {}).get("content") or ""
        subchapter_defs[2][1].append((rid, full_name, raw_html, pregen_img_ids[full_name], f"{full_name}.webp", extra))

    # Subchapter 4: NPCs & Cast
    ref_page_Counter += 1
    combat_npc_rid = f"id-{ref_page_Counter:05d}"
    npc_links = [foundry_actor_to_fgu[aid] for aid, (_, nm) in actor_jsons.items() if nm in ("Corik", "Jedes Guard", "Larith", "Larith's Bear")]
    combat_npc_html = (
        "<h2>Combat NPCs</h2>"
        "<p>Ready-to-run HM3.5E NPC records for combat encounters in <em>A Shower of Silver</em>. "
        "Open any linked NPC below to drag them onto the Combat Tracker.</p>"
    )
    subchapter_defs[3][1].append((combat_npc_rid, "Combat NPCs", combat_npc_html, bear_img_id, "Black Bear.webp", npc_links))

    ref_page_Counter += 1
    cast_rid = f"id-{ref_page_Counter:05d}"
    cast_html = (
        "<h2>Key Keep Officials &amp; Cast Portraits</h2>"
        "<p>Shareable portrait records for the officials of Jedes Keep and key adventure figures.</p>"
    )
    cast_links = [("imagewindow", f"image.{portrait_img_ids[title.lower()]}", title) for _, title in NPC_PORTRAITS]
    subchapter_defs[3][1].append((cast_rid, "Cast Portraits", cast_html, None, None, cast_links))

    # UUID resolver
    def uuid_resolver(target, label):
        if target.startswith("Actor."):
            aid = target.split(".", 1)[1]
            return foundry_actor_to_fgu.get(aid)
        if target in foundry_page_to_fgu:
            return foundry_page_to_fgu[target]
        # Match external Jedes Keep NPC portraits by name
        lbl_low = label.lower()
        for p_title_low, p_img_id in portrait_img_ids.items():
            # Handle minor spelling variance Sir Jassyff vs Sir Jasyff, Lady Helarn Poulty vs Poutry
            stem = p_title_low.split()[1] if len(p_title_low.split()) > 1 else p_title_low
            if p_title_low in lbl_low or (len(stem) >= 5 and stem in lbl_low):
                return ("imagewindow", f"image.{p_img_id}", label)
        return None

    # 4. Build <image> records (with GM Map pins)
    s_w = float(scene_json["width"])
    s_h = float(scene_json["height"])
    s_pad = float(scene_json.get("padding", 0.1))
    g_size = float(scene_json.get("grid", {}).get("size", 100))
    pad_x = math.ceil((s_w * s_pad) / g_size) * g_size
    pad_y = math.ceil((s_h * s_pad) / g_size) * g_size

    gm_pins = []
    for note in scene_json.get("notes", []):
        entry_key = f"JournalEntry.{note['entryId']}.JournalEntryPage.{note['pageId']}"
        resolved = foundry_page_to_fgu.get(entry_key)
        if not resolved:
            continue
        fx = round((float(note["x"]) - pad_x) - (s_w / 2.0))
        fy = round((s_h / 2.0) - (float(note["y"]) - pad_y))
        gm_pins.append({"name": note["text"], "record": resolved[1], "x": fx, "y": fy})

    image_root = ET.SubElement(root, "image")
    for iid, title, fname in image_specs:
        add_image_record(image_root, iid, title, fname, pins=gm_pins if iid == "id-00001" else None)

    # 5. Build <reference><refmanualindex> and <reference><refmanualdata>
    ref_root = ET.SubElement(root, "reference")
    rm_index = ET.SubElement(ref_root, "refmanualindex")
    chapters_el = ET.SubElement(rm_index, "chapters")
    chap1 = ET.SubElement(chapters_el, "id-00001")
    sub_typed(chap1, "name", "string", "A Shower of Silver")
    sub_typed(chap1, "order", "number", 1)
    subchapters_el = ET.SubElement(chap1, "subchapters")
    rm_data = ET.SubElement(ref_root, "refmanualdata")

    for sc_idx, (sc_title, pages) in enumerate(subchapter_defs, 1):
        sc_el = ET.SubElement(subchapters_el, f"id-{sc_idx:05d}")
        sub_typed(sc_el, "name", "string", sc_title)
        sub_typed(sc_el, "order", "number", sc_idx)
        refpages_el = ET.SubElement(sc_el, "refpages")

        for pg_idx, (rid, ptitle, raw_html, img_id, img_file, extra_links) in enumerate(pages, 1):
            fgu_xml = resolve_uuids_and_sanitize(raw_html, uuid_resolver, extra_links=extra_links)

            # Index entry
            rp = ET.SubElement(refpages_el, f"id-{pg_idx:05d}")
            sub_typed(rp, "keywords", "string", build_keywords(ptitle, fgu_xml))
            ll = sub_typed(rp, "listlink", "windowreference")
            ET.SubElement(ll, "class").text = "referencemanualpage"
            ET.SubElement(ll, "recordname").text = f"reference.refmanualdata.{rid}"
            sub_typed(rp, "name", "string", ptitle)
            sub_typed(rp, "order", "number", pg_idx)

            # Data entry
            data_pg = ET.SubElement(rm_data, rid)
            sub_typed(data_pg, "name", "string", ptitle)
            blocks_el = ET.SubElement(data_pg, "blocks")
            b_order = 0

            if img_id and img_file:
                b_order += 1
                add_embedded_image_block(
                    blocks_el, f"id-{b_order:05d}", ptitle, img_file, f"image.{img_id}", b_order
                )

            b_order += 1
            add_singletext_block(blocks_el, f"id-{b_order:05d}", fgu_xml, b_order)

            # On Cast Portraits page, embed all 6 NPC portraits cleanly
            if rid == cast_rid:
                for _, npc_p_title in NPC_PORTRAITS:
                    b_order += 1
                    pid_img = portrait_img_ids[npc_p_title.lower()]
                    add_embedded_image_block(
                        blocks_el, f"id-{b_order:05d}", npc_p_title, f"{npc_p_title}.webp", f"image.{pid_img}", b_order
                    )

    # 6. Write db.xml cleanly indented
    ET.indent(root, space="\t")
    tree = ET.ElementTree(root)
    tree.write(DB_PATH, encoding="utf-8", xml_declaration=True)
    print(f"Converted db.xml written to {DB_PATH}")
    print(f"  Charsheets: {len(charsheet_root)}")
    print(f"  NPCs      : {len(npc_root)}")
    print(f"  Images    : {len(image_root)} (GM Map pins: {len(gm_pins)})")
    print(f"  RefPages  : {len(rm_data)}")


def verify():
    """Validate generated db.xml and assets against FGU HM3.5E schema rules."""
    with open(DB_PATH, encoding="utf-8") as f:
        raw = f.read()
    for bad in ("@UUID", "@Compendium", "modules/hm-adv-sos"):
        assert bad not in raw, f"Found forbidden substring: {bad}"

    tree = ET.parse(DB_PATH)
    root = tree.getroot()

    charsheets = list(root.find("charsheet"))
    npcs = list(root.find("npc"))
    images = list(root.find("image"))
    ref_pages = list(root.find("reference/refmanualdata"))
    subchapters = root.findall(".//reference/refmanualindex/chapters/*//subchapters/*")
    assert len(charsheets) == 6, f"Expected 6 charsheets, got {len(charsheets)}"
    assert len(npcs) == 4, f"Expected 4 npcs, got {len(npcs)}"
    assert len(images) == 17, f"Expected 17 images, got {len(images)}"
    assert len(subchapters) == 4, f"Expected 4 subchapters, got {len(subchapters)}"
    assert len(ref_pages) == 23, f"Expected 23 refpages, got {len(ref_pages)}"

    for img_el in images:
        layers = img_el.findall(".//layers/layer")
        assert layers, f"{img_el.tag} has no layers"
        for layer in layers:
            ltype = layer.findtext("type")
            if ltype == "image":
                bmp = layer.findtext("bitmap", "")
                assert bmp.startswith("campaign/images/"), f"Bad bitmap: {bmp}"
                assert os.path.exists(os.path.join(ROOT_DIR, bmp[len("campaign/"):])), f"Missing file: {bmp}"
            elif ltype == "shortcut":
                rec = layer.findtext("shortcut/record", "")
                assert rec.startswith("reference.refmanualdata."), f"Bad shortcut record: {rec}"

    for cs in charsheets:
        assert cs.find("holder") is None, f"Found <holder> on {cs.tag}"
        assert cs.findtext("chardbversion") == "2", f"Missing chardbversion=2 on {cs.tag}"
        cname = cs.findtext("name")
        for wsc in cs.findall("weaponlist/*/shortcut/recordname"):
            iid = (wsc.text or "").split(".")[-1]
            assert cs.find(f"inventorylist/{iid}") is not None, f"{cname}: missing inventorylist/{iid}"
        sk_names = {s.findtext("name_displayed", "").lower() for s in cs.findall("skilllist/*")} | {
            s.findtext("name", "").lower() for s in cs.findall("skilllist/*")
        }
        for wact in cs.findall("weaponlist/*/actionlist/*"):
            wsk = (wact.findtext("skill") or "").lower()
            assert wsk in sk_names, f"{cname}: weapon skill '{wsk}' not in skilllist"
        print(
            f"  PC OK : {cname} | skills={len(cs.findall('skilllist/*'))} "
            f"| inv={len(cs.findall('inventorylist/*'))} | wpns={len(cs.findall('weaponlist/*'))} "
            f"| powers={len(cs.findall('powers/*'))}"
        )

    gm_pins = [l for l in root.findall("image/id-00001//layers/layer") if l.findtext("type") == "shortcut"]
    assert len(gm_pins) == 6, f"Expected 6 GM map pins, got {len(gm_pins)}"
    for p in gm_pins:
        print(f"  Pin OK: {p.findtext('name')} -> {p.findtext('shortcut/record')} | {p.findtext('matrix')}")

    for el in root.iter():
        if el.text and (el.text.startswith("campaign/images/") or el.text.startswith("campaign/tokens/")):
            rel = el.text[len("campaign/"):]
            assert os.path.exists(os.path.join(ROOT_DIR, rel)), f"Missing referenced file: {rel}"

    def resolve_path(path):
        cur = root
        for part in path.split("."):
            cur = cur.find(part)
            if cur is None:
                return False
        return True

    for el in root.findall(".//link"):
        rec = el.attrib.get("recordname", "")
        assert resolve_path(rec), f"Unresolved <link recordname={rec}>"
    for el in root.findall(".//imagelink/recordname"):
        assert resolve_path(el.text or ""), f"Unresolved <imagelink recordname={el.text}>"
    for el in root.findall(".//layer/shortcut"):
        rec = el.findtext("record") or ""
        assert resolve_path(rec), f"Unresolved <layer/shortcut record={rec}>"

    forbidden_tags = {
        "h1", "h2", "h3", "div", "span", "section", "br", "img", "a",
        "dl", "dt", "dd", "thead", "tbody", "caption", "blockquote", "strong", "em",
    }
    for el in root.iter():
        if el.attrib.get("type") == "formattedtext":
            for sub in el.iter():
                assert sub.tag.lower() not in forbidden_tags, f"Forbidden tag <{sub.tag}> in formattedtext"

    for npc in npcs:
        nname = npc.findtext("name")
        sk = npc.findtext("skills", "")
        parts = [p.strip() for p in sk.split(",")]
        assert parts[0].startswith("Initiative "), f"{nname} skill[0] not Initiative: {parts[0]}"
        assert parts[1].startswith("Dodge "), f"{nname} skill[1] not Dodge: {parts[1]}"
        assert parts[2].startswith("Unarmed ") or nname == "Larith's Bear", f"{nname} skill[2] unexpected: {parts[2]}"
        acts = [a.findtext("name") for a in npc.findall("actions/*")]
        assert "Dodge" not in acts and "Initiative" not in acts, f"{nname} invalid action in {acts}"
        print(f"  NPC OK: {nname} | actions={acts}")

    print("Verification passed: 0 errors.")


if __name__ == "__main__":
    convert()
    if "--verify" in sys.argv:
        verify()
