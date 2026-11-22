"""
Quick check of sql/queries.sql WITHOUT a MySQL server.

Loads data/processed/*.csv into an in-memory SQLite database, translates the few
MySQL-only bits (DATEDIFF, DATE_ADD, DATE 'literal'), runs every query and prints the result.
This is only a smoke test - the real deliverable runs on MySQL 8 (see README).

    python sql/check_queries_sqlite.py
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
con = sqlite3.connect(":memory:")
for f in sorted((ROOT / "data" / "processed").glob("*.csv")):
    pd.read_csv(f).to_sql(f.stem, con, index=False)

sql = (ROOT / "sql" / "queries.sql").read_text(encoding="utf-8")
sql = re.sub(r"^USE .*?;", "", sql, flags=re.M)


def to_sqlite(q):
    q = re.sub(r"DATE '(\d{4}-\d{2}-\d{2})'", r"'\1'", q)
    q = re.sub(r"DATEDIFF\(([^,]+),\s*([^)]+)\)", r"CAST(julianday(\1) - julianday(\2) AS INT)", q)
    q = re.sub(r"DATE_ADD\(([^,]+),\s*INTERVAL (\d+) DAY\)", r"date(\1, '+\2 day')", q)
    return q


blocks = re.split(r"\n(?=-- Q\d)", sql)
ok = 0
for b in blocks:
    m = re.match(r"-- (Q\d+)[^\n]*", b.strip())
    if not m:
        continue
    q = to_sqlite(b.strip())
    try:
        res = pd.read_sql_query(q, con)
        ok += 1
        print(f"\n=== {m.group(0)}\n{res.head(12).to_string(index=False)}\n({len(res)} rows)")
    except Exception as e:
        print(f"\n=== {m.group(0)}\nFAILED: {e}")
print(f"\n{ok} queries ran OK")
