import json
import sqlite3


def main():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tpl = cur.execute("SELECT id FROM process_templates WHERE template_name = '大挑'").fetchone()
    if not tpl:
        print('template_not_found')
        return
    tid = int(tpl['id'])

    row = cur.execute(
        "SELECT status_options FROM process_node_status WHERE template_id = ? AND node_name = '省赛'",
        (tid,)
    ).fetchone()
    if not row:
        print('node_not_found')
        return

    try:
        opts = json.loads(row['status_options'] or '[]')
    except Exception:
        opts = []
    if not isinstance(opts, list):
        opts = []

    if '已获奖' not in opts:
        insert_after = '待评审'
        if insert_after in opts:
            idx = opts.index(insert_after) + 1
            opts.insert(idx, '已获奖')
        else:
            opts.append('已获奖')

        cur.execute(
            "UPDATE process_node_status SET status_options = ? WHERE template_id = ? AND node_name = '省赛'",
            (json.dumps(opts, ensure_ascii=False), tid)
        )
        conn.commit()
        print('updated', opts)
    else:
        print('noop', opts)

    conn.close()


if __name__ == '__main__':
    main()

