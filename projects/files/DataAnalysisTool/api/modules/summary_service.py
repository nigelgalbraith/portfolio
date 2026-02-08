"""Summary query planning and execution helpers.

Routes should remain thin; this module contains the helpers used by the
summary endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from modules.db import fetch_all
from modules.validators import require_ident, qident
from modules.table_meta import fetch_table_meta


class SummaryConfigError(Exception):
    """Raised when the summary configuration is invalid."""


def field_alias(table: str, col: str) -> str:
    """Return a safe JSON key alias."""
    return f"{table}__{col}"



def field_token_field(table: str, col: str) -> str:
    """Return a stable token for UI mapping."""
    return f"field:{table}.{col}"



def field_token_list(field: str) -> str:
    """Return a stable token for list outputs."""
    return f"list:{field}"



def get_table_columns(db: str, table_name: str) -> set[str]:
    """Return the column names for a table."""
    rows = fetch_all(
        db,
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        [table_name],
    )
    return {r["column_name"] for r in rows}



def get_all_tables(db: str) -> set[str]:
    """Return all base table names in public schema."""
    rows = fetch_all(
        db,
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        """,
        [],
    )
    return {r["table_name"] for r in rows}



def get_fk_edges(db: str) -> list[dict[str, str]]:
    """Return FK edges as a list of dicts (table/column -> ref_table/ref_column)."""
    rows = fetch_all(
        db,
        """
        SELECT
          tc.table_name        AS table_name,
          kcu.column_name      AS column_name,
          ccu.table_name       AS ref_table_name,
          ccu.column_name      AS ref_column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
        """,
        [],
    )
    return [
        {
            "table": r["table_name"],
            "column": r["column_name"],
            "ref_table": r["ref_table_name"],
            "ref_column": r["ref_column_name"],
        }
        for r in rows
    ]



def pick_order_col(child_cols: set[str]) -> str | None:
    """Pick a best-effort ordering column for list aggregations."""
    candidates = ["item_index", "idx", "sort_order", "position", "order", "id"]
    for c in candidates:
        if c in child_cols:
            return c
    return None



def find_edge(edges: list[dict[str, str]], table: str, ref_table: str) -> dict[str, str] | None:
    """Return the first edge between a table and a referenced table."""
    for e in edges:
        if e["table"] == table and e["ref_table"] == ref_table:
            return e
    return None



def find_edge_between(edges: list[dict[str, str]], a: str, b: str) -> dict[str, str] | None:
    """Return an edge between two tables regardless of direction."""
    return find_edge(edges, a, b) or find_edge(edges, b, a)



def join_condition_sql(left: str, right: str, edge: dict[str, str]) -> str:
    """Return a JOIN predicate for the provided edge and tables."""
    if edge["table"] == left and edge["ref_table"] == right:
        return (
            f"{qident(left)}.{qident(edge['column'])} = "
            f"{qident(right)}.{qident(edge['ref_column'])}"
        )
    if edge["table"] == right and edge["ref_table"] == left:
        return (
            f"{qident(right)}.{qident(edge['column'])} = "
            f"{qident(left)}.{qident(edge['ref_column'])}"
        )
    raise SummaryConfigError("Invalid join edge for provided tables")



def normalize_field_item(item: Any) -> dict[str, Any]:
    """Normalize strict v2 field/list config items."""
    if not isinstance(item, dict):
        raise SummaryConfigError(
            "Config v1 strings are not supported. Re-save configs as v2 objects."
        )
    kind = item.get("kind")
    if kind == "list":
        field = require_ident(item.get("field", ""), "field")
        return {"kind": "list", "field": field}
    table = require_ident(item.get("table", ""), "table")
    col = require_ident(item.get("column", ""), "column")
    alias = item.get("as")
    if alias is not None:
        alias = require_ident(str(alias), "alias")
    return {"kind": "field", "table": table, "column": col, "as": alias}


@dataclass
class SummaryPlan:
    """A planned summary query."""
    sql: str
    alias_map: dict[str, str]



def build_summary_plan(db: str, main: str, fields: list[dict[str, Any]]) -> SummaryPlan:
    """Build a SQL query and alias map for the provided normalized fields."""
    all_tables = get_all_tables(db)
    if main not in all_tables:
        raise SummaryConfigError(f"Unknown main table '{main}'")
    main_cols = get_table_columns(db, main)
    # list tables convention: <main>_<field>_list
    list_tables = fetch_all(
        db,
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name LIKE %s
        """,
        [f"{main}\\_%\\_list"],
    )
    list_fields: dict[str, str] = {}
    prefix = f"{main}_"
    suffix = "_list"
    for r in list_tables:
        tname = r["table_name"]
        if tname.startswith(prefix) and tname.endswith(suffix):
            field = tname[len(prefix) : -len(suffix)]
            if field:
                list_fields[field] = tname
    fk_edges = get_fk_edges(db)
    table_meta = fetch_table_meta(db)
    junction_tables = {
        t for t, meta in (table_meta or {}).items() if meta.get("tableType") == "junction"
    }
    outgoing_from_main = [e for e in fk_edges if e["table"] == main]
    incoming_to_main = [e for e in fk_edges if e["ref_table"] == main]
    join_parts: list[str] = []
    join_alias_by_table: dict[str, str] = {}
    def ensure_join(ref_table: str, edge: dict[str, str]) -> str:
        if ref_table in join_alias_by_table:
            return join_alias_by_table[ref_table]
        alias = f"j_{ref_table}"
        join_alias_by_table[ref_table] = alias
        join_parts.append(
            f"LEFT JOIN {qident(ref_table)} AS {qident(alias)} "
            f"ON {qident(main)}.{qident(edge['column'])} = {qident(alias)}.{qident(edge['ref_column'])}"
        )
        return alias
    select_parts: list[str] = []
    alias_map: dict[str, str] = {}
    # Always include main.id once
    id_alias = field_alias(main, "id")
    select_parts.append(f"{qident(main)}.{qident('id')} AS {qident(id_alias)}")
    alias_map[field_token_field(main, "id")] = id_alias
    for item in fields:
        tok = item["_token"]
        if item["kind"] == "list":
            field = item["field"]
            if field not in list_fields:
                raise SummaryConfigError(f"Unknown list field '{field}'")
            child = list_fields[field]
            child_cols = get_table_columns(db, child)
            parent_col = "parent_id"
            if parent_col not in child_cols:
                raise SummaryConfigError(
                    f"List table '{child}' missing required column '{parent_col}'"
                )
            value_candidates = [
                "item_value",
                "value",
                "name",
                "label",
                field,
                "text",
                "description",
                "description",
            ]
            value_col = next((c for c in value_candidates if c in child_cols), None)
            if value_col is None:
                ignore = {
                    parent_col,
                    "id",
                    "item_index",
                    "idx",
                    "sort_order",
                    "position",
                    "order",
                    "created_at",
                    "updated_at",
                }
                remaining = [c for c in child_cols if c not in ignore]
                if not remaining:
                    raise SummaryConfigError(
                        f"List table '{child}' has no usable value column"
                    )
                value_col = sorted(remaining)[0]
            order_col = pick_order_col(child_cols)
            order_sql = f" ORDER BY {qident(order_col)}" if order_col else ""
            out_alias = require_ident(field, "alias")
            alias_map[tok] = out_alias
            select_parts.append(
                (
                    "(\n"
                    "  SELECT COALESCE(\n"
                    f"    json_agg({qident(value_col)}{order_sql}),\n"
                    "    '[]'::json\n"
                    "  )\n"
                    f"  FROM {qident(child)}\n"
                    f"  WHERE {qident(parent_col)} = {qident(main)}.{qident('id')}\n"
                    f") AS {qident(out_alias)}"
                )
            )
            continue
        # normal field
        t = item["table"]
        c = item["column"]
        out_alias = item["as"] or field_alias(t, c)
        alias_map[tok] = out_alias
        if t == main:
            if c not in main_cols:
                raise SummaryConfigError(f"Unknown field '{t}.{c}'")
            select_parts.append(
                f"{qident(main)}.{qident(c)} AS {qident(out_alias)}"
            )
            continue
        if t not in all_tables:
            raise SummaryConfigError(f"Unknown linked table '{t}'")
        outgoing_edge = next(
            (e for e in outgoing_from_main if e["ref_table"] == t), None
        )
        if outgoing_edge:
            ref_cols = get_table_columns(db, t)
            if c not in ref_cols:
                raise SummaryConfigError(f"Unknown field '{t}.{c}'")
            alias = ensure_join(t, outgoing_edge)
            select_parts.append(f"{qident(alias)}.{qident(c)} AS {qident(out_alias)}")
            continue
        incoming_edge = next(
            (e for e in incoming_to_main if e["table"] == t), None
        )
        if incoming_edge:
            child_cols = get_table_columns(db, t)
            if c not in child_cols:
                raise SummaryConfigError(f"Unknown field '{t}.{c}'")
            fk_col = incoming_edge["column"]
            main_ref_col = incoming_edge["ref_column"]
            order_col = pick_order_col(child_cols)
            order_sql = f" ORDER BY {qident(order_col)}" if order_col else ""
            select_parts.append(
                (
                    "(\n"
                    "  SELECT COALESCE(\n"
                    f"    json_agg({qident(c)}{order_sql}),\n"
                    "    '[]'::json\n"
                    "  )\n"
                    f"  FROM {qident(t)}\n"
                    f"  WHERE {qident(t)}.{qident(fk_col)} = {qident(main)}.{qident(main_ref_col)}\n"
                    f") AS {qident(out_alias)}"
                )
            )
            continue
        # Junction-aware: main <-> junction <-> far (aggregate list)
        junction_edge = None
        far_edge = None
        junction_table = None
        for jt in junction_tables:
            if jt == main:
                continue
            if t == jt:
                edge_to_main = find_edge_between(fk_edges, main, jt)
                if edge_to_main:
                    junction_table = jt
                    junction_edge = edge_to_main
                    far_edge = None
                    break
                continue
            edge_to_main = find_edge_between(fk_edges, main, jt)
            if not edge_to_main:
                continue
            edge_to_far = find_edge_between(fk_edges, jt, t)
            if not edge_to_far:
                continue
            junction_table = jt
            junction_edge = edge_to_main
            far_edge = edge_to_far
            break
        if junction_table and junction_edge:
            if t not in all_tables:
                raise SummaryConfigError(f"Unknown linked table '{t}'")
            if far_edge is None:
                j_cols = get_table_columns(db, junction_table)
                if c not in j_cols:
                    raise SummaryConfigError(f"Unknown field '{t}.{c}'")
                order_col = pick_order_col(j_cols)
                order_sql = f" ORDER BY {qident(order_col)}" if order_col else ""
                join_to_main = join_condition_sql(main, junction_table, junction_edge)
                select_parts.append(
                    (
                        "(\n"
                        "  SELECT COALESCE(\n"
                        f"    json_agg({qident(junction_table)}.{qident(c)}{order_sql}),\n"
                        "    '[]'::json\n"
                        "  )\n"
                        f"  FROM {qident(junction_table)}\n"
                        f"  WHERE {join_to_main}\n"
                        f") AS {qident(out_alias)}"
                    )
                )
                continue
            far_cols = get_table_columns(db, t)
            if c not in far_cols:
                raise SummaryConfigError(f"Unknown field '{t}.{c}'")
            order_col = pick_order_col(far_cols)
            order_sql = f" ORDER BY {qident(order_col)}" if order_col else ""
            join_to_main = join_condition_sql(main, junction_table, junction_edge)
            join_to_far = join_condition_sql(junction_table, t, far_edge)
            select_parts.append(
                (
                    "(\n"
                    "  SELECT COALESCE(\n"
                    f"    json_agg({qident(t)}.{qident(c)}{order_sql}),\n"
                    "    '[]'::json\n"
                    "  )\n"
                    f"  FROM {qident(junction_table)}\n"
                    f"  JOIN {qident(t)} ON {join_to_far}\n"
                    f"  WHERE {join_to_main}\n"
                    f") AS {qident(out_alias)}"
                )
            )
            continue
        raise SummaryConfigError(
            f"Linked field '{t}.{c}' not supported (no direct FK relationship found)."
        )
    sql = (
        "SELECT\n"
        f"  {', '.join(select_parts)}\n"
        f"FROM {qident(main)}\n"
        f"{' '.join(join_parts)}\n"
        "LIMIT 200"
    )
    return SummaryPlan(sql=sql, alias_map=alias_map)



def run_summary(db: str, main: str, summary_fields: list[Any], detail_fields: list[Any]) -> dict[str, Any]:
    """Validate config, plan SQL, execute, and return rows + alias map."""
    if not isinstance(summary_fields, list) or not isinstance(detail_fields, list):
        raise SummaryConfigError("summaryFields/detailFields must be arrays")
    requested: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in (summary_fields + detail_fields):
        norm = normalize_field_item(item)
        if norm["kind"] == "list":
            tok = field_token_list(norm["field"])
        else:
            tok = field_token_field(norm["table"], norm["column"])
        if tok in seen:
            continue
        seen.add(tok)
        norm["_token"] = tok
        requested.append(norm)
    if not requested:
        raise SummaryConfigError("No fields selected")
    plan = build_summary_plan(db, main, requested)
    rows = fetch_all(db, plan.sql)
    return {"rows": rows, "aliasMap": plan.alias_map}
