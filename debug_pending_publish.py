import sqlite3
from collections import defaultdict


def main():
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    try:
        comps = cur.execute("SELECT id, name FROM competitions").fetchall()
    except Exception:
        comps = []

    comp_name = {c["id"]: c["name"] for c in comps}

    school_q = """
    SELECT id, title, competition_id, status, current_level, review_stage
    FROM projects
    WHERE competition_id IS NOT NULL
      AND status NOT IN ('finished','finished_national_award','college_failed','school_failed','provincial_award')
      AND (current_level='school' OR review_stage='school' OR status IN ('college_recommended','school_review','pending_school_recommendation'))
      AND (school_avg_score IS NULL OR school_avg_score='')
    ORDER BY competition_id, id
    """
    school_rows = cur.execute(school_q).fetchall()

    college_q = """
    SELECT id, title, competition_id, status, current_level, review_stage
    FROM projects
    WHERE competition_id IS NOT NULL
      AND status NOT IN ('finished','finished_national_award','college_failed','school_failed','provincial_award')
      AND (current_level='college' OR review_stage='college' OR status IN ('pending','under_review','pending_college','reviewing','pending_college_recommendation'))
      AND (college_avg_score IS NULL OR college_avg_score='')
    ORDER BY competition_id, id
    """
    college_rows = cur.execute(college_q).fetchall()

    def dump(title, rows):
        by = defaultdict(list)
        for r in rows:
            by[r["competition_id"]].append(r)
        print(title)
        if not by:
            print("  (none)")
        for cid, items in by.items():
            print(f"  competition {cid} {comp_name.get(cid,'')}: {len(items)}")
            for r in items[:50]:
                print(
                    f"    - {r['id']} {r['title']} | {r['status']} | {r['current_level']} | {r['review_stage']}"
                )

    dump("Pending school avg_score candidates:", school_rows)
    print()
    dump("Pending college avg_score candidates:", college_rows)


if __name__ == "__main__":
    main()

