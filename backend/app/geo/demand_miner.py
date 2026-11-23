"""
Zero-Key Search Demand Miner (Google Autocomplete + optional Baidu Suggest).

Adapted from GeoLook's MIT-licensed `scripts/expand.py`:
- Expands brand, competitor, and category roots with buyer-intent modifiers
- Filters out navigational noise (login/download/app store) and prefix drift
- Classifies queries into buyer/educate/probe intent groups
- Converts raw suggest terms into natural AI-assistant questions
- Diffs snapshots against `previous_terms` to flag rising (`is_new=True`) demand
  without mutating longitudinal visibility metrics.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field


_UA_HEADER = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}

MODIFIERS: Dict[str, Dict[str, List[str]]] = {
    "global": {
        "brand": ["", " review", " alternative", " vs", " pricing"],
        "competitor": ["", " review", " alternative", " vs"],
        "category": ["", " best", " comparison", " pricing"],
    },
    "cn": {
        "brand": ["", " 怎么样", " 靠谱吗", " 替代", " 对比", " 价格"],
        "competitor": ["", " 怎么样", " 替代", " 对比", " 缺点"],
        "category": ["", " 推荐", " 哪个好", " 对比", " 价格"],
    },
}

_GROUP_CUES: List[tuple[str, List[str]]] = [
    ("ALTERNATIVE", ["alternative", "instead of", "replace", "替代", "平替"]),
    ("COMPARE", [" vs", "versus", "compare", "comparison", "对比", "比较", "哪个好"]),
    ("PRICING", ["pricing", "price", "cost", "free", "价格", "多少钱", "收费"]),
    ("RISK", ["scam", "safe", "problem", "issue", "downside", "靠谱", "缺点", "投诉"]),
    ("BRAND_VERIFY", ["review", "worth it", "legit", "怎么样", "评测", "好用吗"]),
    ("RECOMMEND", ["best", "top", "recommend", "推荐", "排行", "哪家"]),
]

_TEMPLATES: Dict[str, Dict[str, str]] = {
    "global": {
        "RECOMMEND": "What are the best options for {t}?",
        "COMPARE": "How should I compare options for {t}?",
        "ALTERNATIVE": "What are the best alternatives for {t}?",
        "PRICING": "How much does {t} cost and is it worth it?",
        "RISK": "What drawbacks or risks should I watch out for with {t}?",
        "BRAND_VERIFY": "Is {t} reliable and worth using in practice?",
        "SCENARIO": "How does {t} work in real-world use?",
    },
    "cn": {
        "RECOMMEND": "{t}，有值得推荐的吗？",
        "COMPARE": "{t}，到底该怎么选？",
        "ALTERNATIVE": "{t}，有哪些替代方案？",
        "PRICING": "{t}大概是什么价位？值不值？",
        "RISK": "{t}，有什么要避的坑吗？",
        "BRAND_VERIFY": "{t}？实际用起来怎么样？",
        "SCENARIO": "{t}，具体场景下怎么用？",
    },
}

_NAV_NOISE_RE = re.compile(
    r"\b(?:download|install|login|log in|sign ?in|sign ?up|register|app store|apk|crack)\b|"
    r"下载|官网|官方网站|安装|登录|注册|入口|客户端|手机版|破解|激活",
    re.I,
)


class DemandCandidate(BaseModel):
    term: str
    root: str
    root_kind: str  # brand | competitor | category
    market: str = "global"
    intent_group: str
    question: str
    first_seen: str
    is_new: bool = True
    approved_for_bank: bool = False


class DemandMiningSnapshot(BaseModel):
    generated_at: str
    market: str
    total_calls: int
    candidates: List[DemandCandidate] = Field(default_factory=list)
    new_count: int = 0


def is_relevant_suggestion(term: str, root: str) -> bool:
    """Reject navigational noise and prefix-drifted suggestions unrelated to `root`."""
    t = (term or "").strip()
    r = (root or "").strip()
    if not t or not r or t.lower() == r.lower():
        return False
    if _NAV_NOISE_RE.search(t):
        return False
    tl = t.lower().replace(" ", "")
    latin_tokens = re.findall(r"[a-z]{3,}", r.lower())
    if latin_tokens:
        return any(tok in tl for tok in latin_tokens)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", r)
    if not cjk_chars:
        return False
    hits = sum(1 for ch in set(cjk_chars) if ch in t)
    return hits * 2 >= len(set(cjk_chars))


def classify_intent_group(term: str, root_kind: str) -> str:
    low = (term or "").lower()
    for grp, cues in _GROUP_CUES:
        if any(c in low for c in cues):
            if grp == "BRAND_VERIFY" and root_kind == "category":
                return "RECOMMEND"
            return grp
    return "SCENARIO"


def to_natural_question(term: str, intent_group: str, market: str = "global") -> str:
    st = (term or "").strip()
    if re.search(r"[?？]$", st):
        return st
    if re.search(r"^(?:how|what|which|is|are|can|should|does)\b|是什么|怎么|如何|哪个|哪些|多少钱|吗$", st, re.I):
        return st + ("？" if market == "cn" else "?")
    tmpl = _TEMPLATES.get(market, _TEMPLATES["global"]).get(intent_group, _TEMPLATES["global"]["SCENARIO"])
    return tmpl.format(t=st)


async def fetch_google_suggest(query: str, hl: str = "en", timeout: float = 6.0) -> List[str]:
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&hl={hl}&q={quote(query)}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, headers=_UA_HEADER)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [s for s in (data[1] if isinstance(data, list) and len(data) > 1 else []) if isinstance(s, str)]


async def fetch_baidu_suggest(query: str, timeout: float = 6.0) -> List[str]:
    url = f"https://suggestion.baidu.com/su?wd={quote(query)}&ie=utf-8&oe=utf-8"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, headers=_UA_HEADER)
        if resp.status_code != 200:
            return []
        m = re.search(r"s:(\[.*?\])", resp.text)
        return json.loads(m.group(1)) if m else []


async def mine_search_demand(
    *,
    brand_name: str,
    category: str = "",
    competitors: Sequence[str] = (),
    market: str = "global",
    previous_first_seen: Optional[Dict[str, str]] = None,
    max_candidates: int = 120,
    delay: float = 0.15,
    fetcher: Optional[Callable[[str, str], Any]] = None,
) -> DemandMiningSnapshot:
    """Mine real autocomplete suggestions and snapshot-diff against `previous_first_seen`."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prev = {k.strip().lower(): v for k, v in (previous_first_seen or {}).items()}
    mk = "cn" if market == "cn" else "global"

    roots: List[tuple[str, str]] = []
    if brand_name.strip():
        roots.append((brand_name.strip(), "brand"))
    for c in list(competitors)[:6]:
        if c and c.strip():
            roots.append((c.strip(), "competitor"))
    if category.strip():
        roots.append((category.strip(), "category"))

    seen: set[str] = set()
    candidates: List[DemandCandidate] = []
    calls = 0

    for root, kind in roots:
        for mod in MODIFIERS[mk][kind]:
            q = root + mod
            try:
                if fetcher is not None:
                    sugs = await fetcher(q, mk)
                elif mk == "cn":
                    sugs = await fetch_baidu_suggest(q)
                else:
                    sugs = await fetch_google_suggest(q)
            except Exception:
                sugs = []
            calls += 1
            if delay > 0 and fetcher is None:
                await asyncio.sleep(delay)

            for s in (sugs or [])[:10]:
                st = s.strip()
                key = st.lower()
                if key in seen or not is_relevant_suggestion(st, root):
                    continue
                if len(candidates) >= max_candidates:
                    break
                seen.add(key)
                grp = classify_intent_group(st, kind)
                qtext = to_natural_question(st, grp, market=mk)
                is_new = key not in prev
                candidates.append(
                    DemandCandidate(
                        term=st,
                        root=root,
                        root_kind=kind,
                        market=mk,
                        intent_group=grp,
                        question=qtext,
                        first_seen=prev.get(key, today),
                        is_new=is_new,
                        approved_for_bank=False,
                    )
                )

    return DemandMiningSnapshot(
        generated_at=today,
        market=mk,
        total_calls=calls,
        candidates=candidates,
        new_count=sum(1 for c in candidates if c.is_new),
    )
