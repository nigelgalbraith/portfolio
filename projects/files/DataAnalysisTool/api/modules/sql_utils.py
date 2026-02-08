def safe_fk_name(table, col, ref_table, ref_col):
    """Return a deterministic, length-limited FK constraint name."""
    return f"fk_{table}_{col}_{ref_table}_{ref_col}"[:63]


def split_sql_statements(sql_text: str):
    """Split SQL text into statements, respecting quoted semicolons."""
    stmts, buf = [], []
    in_single = in_double = False
    for ch in sql_text:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if ch == ";" and not (in_single or in_double):
            stmt = "".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts
