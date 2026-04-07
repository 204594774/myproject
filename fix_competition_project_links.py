import sqlite3


def infer_type_from_title(title: str) -> str:
    t = (title or "").strip()
    if "挑战杯" in t and "课外学术科技作品竞赛" in t:
        return "challenge_cup"
    if "挑战杯" in t and "创业计划" in t:
        return "youth_challenge"
    if "电子商务" in t and "实战赛" in t:
        return "three_creativity_practical"
    if "电子商务" in t and ("常规赛" in t or "挑战赛" in t):
        return "three_creativity_regular"
    if "创新大赛" in t or "互联网+" in t:
        return "internet_plus"
    return ""


def main():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    competitions = [dict(r) for r in cur.execute("SELECT id, title, template_type FROM competitions").fetchall()]
    comp_by_id = {c["id"]: c for c in competitions}

    projects = [dict(r) for r in cur.execute(
        "SELECT id, title, competition_id, project_type, template_type FROM projects WHERE competition_id IS NOT NULL"
    ).fetchall()]

    fixed_links = 0
    fixed_types = 0

    for p in projects:
        pid = p["id"]
        cid = p["competition_id"]
        comp = comp_by_id.get(cid)

        if comp is None:
            match = None
            for c in competitions:
                if c.get("title") and (c["title"] in (p.get("title") or "") or (p.get("title") or "") in c["title"]):
                    match = c
                    break
            if match is not None:
                cur.execute("UPDATE projects SET competition_id = ? WHERE id = ?", (match["id"], pid))
                comp = match
                fixed_links += 1

        if comp is None:
            continue

        inferred = infer_type_from_title(comp.get("title"))
        if not inferred:
            continue

        if p.get("template_type") in ("competition", "default", None, ""):
            cur.execute(
                "UPDATE projects SET template_type = ? WHERE id = ?",
                (inferred, pid)
            )
            fixed_types += 1

        if p.get("project_type") in ("innovation", None, ""):
            cur.execute(
                "UPDATE projects SET project_type = ? WHERE id = ?",
                (inferred, pid)
            )
            fixed_types += 1

    conn.commit()
    conn.close()
    print({"fixed_links": fixed_links, "fixed_types": fixed_types})


if __name__ == "__main__":
    main()

