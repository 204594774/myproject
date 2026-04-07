import sqlite3


def infer_level_from_name(name: str):
    s = str(name or '').strip()
    if not s:
        return None
    if '金奖' in s:
        return 'gold'
    if '银奖' in s:
        return 'silver'
    if '铜奖' in s:
        return 'bronze'
    if '特等奖' in s or '特等' in s:
        return 'special'
    if '一等奖' in s or '一等' in s:
        return 'first'
    if '二等奖' in s or '二等' in s:
        return 'second'
    if '三等奖' in s or '三等' in s:
        return 'third'
    if '优秀奖' in s or '优秀' in s:
        return 'excellent'
    return None


def level_label(code: str):
    m = {
        'gold': '金奖',
        'silver': '银奖',
        'bronze': '铜奖',
        'special': '特等奖',
        'first': '一等奖',
        'second': '二等奖',
        'third': '三等奖',
        'excellent': '优秀奖',
    }
    return m.get(str(code or '').strip().lower(), '')


def main():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT id, project_id, stage, award_level, award_name
        FROM project_awards
        WHERE stage IN ('provincial', 'national')
          AND COALESCE(TRIM(award_level), '') IN ('', 'none')
        ORDER BY id
        """
    ).fetchall()

    fixed_awards = 0
    synced_projects = set()

    for r in rows:
        inferred = infer_level_from_name(r['award_name'])
        if not inferred:
            continue
        cur.execute(
            "UPDATE project_awards SET award_level = ? WHERE id = ?",
            (inferred, r['id'])
        )
        fixed_awards += cur.rowcount
        synced_projects.add(int(r['project_id']))

        pid = int(r['project_id'])
        if r['stage'] == 'provincial':
            cur.execute(
                """
                UPDATE projects
                SET provincial_status = '已获奖',
                    provincial_award_level = ?,
                    provincial_advance_national = 1,
                    national_status = COALESCE(NULLIF(national_status, ''), '未参赛'),
                    national_award_level = COALESCE(NULLIF(national_award_level, ''), 'none'),
                    current_level = 'national',
                    review_stage = 'national'
                WHERE id = ?
                """,
                (inferred, pid)
            )
            cur.execute(
                """
                INSERT INTO project_node_status
                (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                VALUES (?, '省赛', '已晋级', '', ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(project_id, node_name) DO UPDATE SET
                    current_status = excluded.current_status,
                    award_level = excluded.award_level,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (pid, level_label(inferred))
            )
        else:
            cur.execute(
                """
                UPDATE projects
                SET national_status = '已获奖',
                    national_award_level = ?,
                    status = 'finished_national_award',
                    level = '国赛获奖'
                WHERE id = ?
                """,
                (inferred, pid)
            )
            cur.execute(
                """
                INSERT INTO project_node_status
                (project_id, node_name, current_status, comment, award_level, updated_by, updated_at)
                VALUES (?, '国赛', '已获奖', '', ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(project_id, node_name) DO UPDATE SET
                    current_status = excluded.current_status,
                    award_level = excluded.award_level,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (pid, level_label(inferred))
            )

    conn.commit()
    conn.close()

    print('fixed_awards', fixed_awards)
    print('synced_projects', len(synced_projects))
    if synced_projects:
        print('project_ids', sorted(synced_projects))


if __name__ == '__main__':
    main()

