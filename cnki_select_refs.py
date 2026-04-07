import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
CNKI_XLS = ROOT / "CNKI全.xls"


@dataclass(frozen=True)
class Row:
    src_db: str
    title: str
    author: str
    organ: str
    source: str
    keyword: str
    summary: str
    pub_time: str
    year: str
    volume: str
    period: str
    pages: str
    issn: str
    url: str
    doi: str


_COL_MAP = {
    "SrcDatabase-来源库": "src_db",
    "Title-题名": "title",
    "Author-作者": "author",
    "Organ-单位": "organ",
    "Source-文献来源": "source",
    "Keyword-关键词": "keyword",
    "Summary-摘要": "summary",
    "PubTime-发表时间": "pub_time",
    "Year-年": "year",
    "Volume-卷": "volume",
    "Period-期": "period",
    "PageCount-页码": "pages",
    "ISSN-国际标准刊号": "issn",
    "URL-网址": "url",
    "DOI-DOI": "doi",
}


def _s(x: Any) -> str:
    if x is None:
        return ""
    s = str(x)
    s = re.sub(r"\s+", " ", s).strip()
    if s.lower() in {"nan", "none"}:
        return ""
    return s


def _norm_title(t: str) -> str:
    t = _s(t)
    t = re.sub(r"\s+", "", t)
    t = t.replace("：", ":").replace("（", "(").replace("）", ")")
    return t


IRRELEVANT_RE = re.compile(
    r"(胎儿|超声|医院|护理|患者|临床|肿瘤|药|手术|影像|MRI|CT|疾病|康复|儿科|产科|"
    r"煤矿|选矿|地质|钻井|发动机|雷达|电网|配电|水晶成像|岛叶)",
    re.IGNORECASE,
)

CORE_RE = re.compile(r"(创新创业|双创|创业)")
SCOPE_RE = re.compile(r"(大学生|高校|高等院校|训练计划|创新大赛|创新创业大赛|本科)")


MANAGEMENT_TERMS = [
    ("创新创业", 8),
    ("双创", 6),
    ("大学生", 6),
    ("高校", 6),
    ("项目管理", 6),
    ("管理体系", 4),
    ("管理机制", 4),
    ("治理", 3),
    ("评价体系", 3),
    ("绩效", 3),
    ("孵化", 3),
    ("创业教育", 4),
    ("实践教学", 3),
    ("协同", 2),
]

PLATFORM_TERMS = [
    ("管理系统", 4),
    ("信息化", 4),
    ("平台", 4),
    ("数字化", 4),
    ("工作流", 3),
    ("审批", 3),
    ("流程", 2),
    ("数据", 2),
]

TECH_TERMS = [
    ("Vue", 2),
    ("Django", 2),
    ("RBAC", 2),
    ("权限", 2),
    ("算法", 2),
    ("排名", 2),
    ("日志", 1),
]


def _score(row: Row) -> int:
    blob = " ".join([row.title, row.keyword, row.summary, row.source])
    if IRRELEVANT_RE.search(blob):
        return -999
    if not CORE_RE.search(blob):
        return -999
    if not SCOPE_RE.search(blob):
        return -50

    score = 0
    for term, w in MANAGEMENT_TERMS:
        if term in blob:
            score += w
    for term, w in PLATFORM_TERMS:
        if term in blob:
            score += w
    for term, w in TECH_TERMS:
        if term in blob:
            score += w

    if "期刊" in row.src_db:
        score += 2
    if row.doi:
        score += 1
    if row.pages:
        score += 1
    if row.year and re.fullmatch(r"\d{4}", row.year):
        y = int(row.year)
        if y >= 2020:
            score += 1
    return score


def _bucket(row: Row) -> str:
    blob = " ".join([row.title, row.keyword, row.summary])
    if any(t in blob for t in ["Vue", "Django", "RBAC"]):
        return "tech"
    if any(t in blob for t in ["评审", "评价", "排名", "指标体系", "绩效评价"]):
        return "eval"
    if any(t in blob for t in ["系统", "平台", "信息化", "数字化", "流程", "审批", "工作流"]):
        return "platform"
    return "management"


def load_rows() -> list[Row]:
    if not CNKI_XLS.exists():
        raise FileNotFoundError(str(CNKI_XLS))

    tables = pd.read_html(str(CNKI_XLS), encoding="utf-8")
    if not tables:
        return []
    df = tables[0]
    if all(isinstance(c, int) for c in df.columns) and len(df) > 1:
        first = [str(x).strip() for x in df.iloc[0].tolist()]
        if "Title-题名" in first and "Author-作者" in first:
            df.columns = first
            df = df.iloc[1:].reset_index(drop=True)

    rows: list[Row] = []
    for _, r in df.iterrows():
        data = {k: _s(r.get(k, "")) for k in _COL_MAP.keys()}
        row = Row(
            src_db=data["SrcDatabase-来源库"],
            title=data["Title-题名"],
            author=data["Author-作者"],
            organ=data["Organ-单位"],
            source=data["Source-文献来源"],
            keyword=data["Keyword-关键词"],
            summary=data["Summary-摘要"],
            pub_time=data["PubTime-发表时间"],
            year=data["Year-年"],
            volume=data["Volume-卷"],
            period=data["Period-期"],
            pages=data["PageCount-页码"],
            issn=data["ISSN-国际标准刊号"],
            url=data["URL-网址"],
            doi=data["DOI-DOI"],
        )
        if not row.title:
            continue
        rows.append(row)
    return rows


def select_candidates(rows: list[Row]) -> list[tuple[int, str, Row]]:
    seen: set[str] = set()
    scored: list[tuple[int, str, Row]] = []
    for row in rows:
        if "期刊" not in row.src_db:
            continue
        key = _norm_title(row.title)
        if key in seen:
            continue
        seen.add(key)
        s = _score(row)
        if s <= 0:
            continue
        scored.append((s, _bucket(row), row))
    scored.sort(key=lambda x: (x[0], x[2].year), reverse=True)
    return scored


def pick_16(scored: list[tuple[int, str, Row]]) -> list[Row]:
    picked: list[Row] = []
    counts = {"management": 0, "platform": 0, "eval": 0, "tech": 0}
    limits = {"management": 12, "platform": 4, "eval": 2, "tech": 2}

    for _, bucket, row in scored:
        if len(picked) >= 16:
            break
        if counts[bucket] >= limits[bucket]:
            continue
        picked.append(row)
        counts[bucket] += 1

    if len(picked) < 16:
        for _, _, row in scored:
            if len(picked) >= 16:
                break
            if row in picked:
                continue
            picked.append(row)
    return picked[:16]


def to_apa_journal(row: Row) -> str:
    authors = _s(row.author).replace(";", "；")
    y = row.year or (row.pub_time[:4] if row.pub_time[:4].isdigit() else "")
    title = _s(row.title)
    journal = _s(row.source)
    vol = _s(row.volume)
    no = _s(row.period)
    pages = _s(row.pages)
    doi = _s(row.doi)

    parts = [f"{authors}. ({y}). {title}. {journal}"]
    volno = ""
    if vol and no:
        volno = f"{vol}({no})"
    elif vol:
        volno = vol
    elif no:
        volno = f"({no})"
    if volno:
        parts[-1] += f", {volno}"
    if pages:
        parts[-1] += f", {pages}"
    parts[-1] += "."
    if doi:
        doi = doi.strip()
        if doi.lower().startswith("http"):
            parts.append(doi)
        else:
            parts.append(f"https://doi.org/{doi}")
    return " ".join(parts)


def main():
    rows = load_rows()
    scored = select_candidates(rows)
    picked = pick_16(scored)

    print(f"总行数: {len(rows)}")
    print(f"候选(去重+过滤后): {len(scored)}")
    print("=== 推荐16条（用于替换[4]~[19]） ===")
    for i, row in enumerate(picked, start=4):
        print(f"[{i}] {to_apa_journal(row)}")
        if row.url:
            print(f"     URL: {row.url}")

    print("=== Top 40 候选（含打分/类别，便于手工微调） ===")
    for rank, (s, b, r) in enumerate(scored[:40], start=1):
        print(f"{rank:02d}. score={s:02d} bucket={b:<10} year={r.year:<4} {r.title} / {r.source}")

    mgmt = [(s, r) for (s, b, r) in scored if b == "management"]
    print("=== Management 类 Top 40（更偏治理/机制/管理研究） ===")
    for rank, (s, r) in enumerate(mgmt[:40], start=1):
        print(f"{rank:02d}. score={s:02d} year={r.year:<4} {r.title} / {r.source}")

    print("=== 全部候选（共61条，按分数降序） ===")
    for rank, (s, b, r) in enumerate(scored, start=1):
        print(f"{rank:02d}. score={s:02d} bucket={b:<10} year={r.year:<4} {r.title} / {r.source}")


if __name__ == "__main__":
    main()
