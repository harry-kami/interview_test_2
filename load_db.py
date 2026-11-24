"""Build bincom.db (SQLite) from the MySQL dump bincom_test.sql."""
import os, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def build(src=os.path.join(HERE, "bincom_test.sql"), dest=os.path.join(HERE, "bincom.db")):
    sql = open(src, encoding="latin-1").read()
    if os.path.exists(dest):
        os.remove(dest)
    con = sqlite3.connect(dest)
    cur = con.cursor()
    for name, body in re.findall(r"CREATE TABLE IF NOT EXISTS `(\w+)` \((.*?)\) ENGINE", sql, re.S):
        cols = re.findall(r"^\s*`(\w+)`\s+(\w+)", body, re.M)
        defs = []
        for i, (c, t) in enumerate(cols):
            kind = "INTEGER" if t.lower() in ("int", "tinyint") else "TEXT"
            defs.append(f"`{c}` {kind}" + (" PRIMARY KEY" if i == 0 and kind == "INTEGER" else ""))
        cur.execute(f"CREATE TABLE {name} ({', '.join(defs)})")
    for stmt in re.findall(r"INSERT INTO .*?;\s*\n", sql, re.S):
        cur.execute(stmt.replace("\\'", "''"))
    con.commit()
    con.close()


if __name__ == "__main__":
    build(*(sys.argv[1:2] or []))
    print("bincom.db built")
