import argparse
import sqlite3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="database.db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cols = [r[1] for r in cur.execute("pragma table_info(review_tasks)").fetchall()]
    if "review_level" not in cols:
        raise SystemExit("review_tasks 表缺少 review_level 字段")

    rows = cur.execute(
        """
        SELECT p.id, p.title, p.status, p.current_level, p.review_stage,
               COALESCE(p.college_result_locked, 0) as college_locked,
               COALESCE(p.school_result_locked, 0) as school_locked,
               SUM(CASE WHEN rt.review_level='school' THEN 1 ELSE 0 END) as school_tasks
        FROM projects p
        JOIN review_tasks rt ON rt.project_id = p.id
        WHERE p.status IN ('rejected', 'college_failed', 'school_failed')
        GROUP BY p.id
        HAVING school_tasks > 0
        ORDER BY p.id
        """
    ).fetchall()

    if not rows:
        print("No stale school tasks found.")
        return

    for r in rows:
        print(
            f"- {r['id']} {r['title']} | status={r['status']} | level={r['current_level']}/{r['review_stage']} | "
            f"college_locked={int(r['college_locked'])} school_locked={int(r['school_locked'])} | school_tasks={int(r['school_tasks'])}"
        )

    if not args.apply:
        print("\nDry run. Re-run with --apply to delete stale school tasks and reset level to college when appropriate.")
        return

    con.execute("BEGIN")
    changed = 0
    for r in rows:
        pid = int(r["id"])
        cur.execute("DELETE FROM review_tasks WHERE project_id=? AND review_level='school'", (pid,))
        if int(r["school_locked"] or 0) == 0 and str(r["status"] or "").strip() in ("rejected", "college_failed"):
            cur.execute(
                "UPDATE projects SET current_level='college', review_stage='college' WHERE id=?",
                (pid,),
            )
        changed += 1
    con.commit()
    print(f"\nApplied to {changed} projects.")


if __name__ == "__main__":
    main()

