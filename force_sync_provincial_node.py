import sqlite3


def main():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE project_node_status
        SET current_status = '已晋级',
            updated_at = CURRENT_TIMESTAMP
        WHERE node_name = '省赛'
          AND project_id IN (
            SELECT id
            FROM projects
            WHERE COALESCE(TRIM(provincial_status), '') IN ('已晋级', '已获奖')
               OR (COALESCE(TRIM(provincial_award_level), '') != '' AND COALESCE(TRIM(provincial_award_level), '') != 'none')
               OR COALESCE(provincial_advance_national, 0) = 1
          )
        """
    )
    updated_to_pass = cur.rowcount

    cur.execute(
        """
        UPDATE project_node_status
        SET current_status = '待评审',
            updated_at = CURRENT_TIMESTAMP
        WHERE node_name = '省赛'
          AND COALESCE(TRIM(current_status), '') IN ('', '未晋级', '待评审')
          AND project_id IN (
            SELECT id
            FROM projects
            WHERE COALESCE(TRIM(provincial_status), '') != '未晋级'
              AND (
                COALESCE(TRIM(school_review_result), '') = 'approved'
                OR COALESCE(TRIM(current_level), '') = 'provincial'
                OR COALESCE(TRIM(review_stage), '') = 'provincial'
                OR COALESCE(TRIM(status), '') IN ('provincial_review', 'provincial')
              )
          )
        """
    )
    updated_to_pending = cur.rowcount

    conn.commit()
    conn.close()

    print('set_prov_to_pass', updated_to_pass)
    print('set_prov_to_pending', updated_to_pending)


if __name__ == '__main__':
    main()

