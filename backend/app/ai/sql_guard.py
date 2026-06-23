"""NL->SQL safety guard (sqlglot AST allowlist).

Mandatory checks before any AI-generated SQL is shown to the user or executed:
- exactly one statement (no multi-statement)
- the statement is a SELECT (no INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/ATTACH/etc.)
- no dangerous/SYSTEM constructs
- a LIMIT is enforced (appended if missing)

Execution additionally happens under a ClickHouse read-only role with user approval.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

DEFAULT_LIMIT = 1000

# Disallowed top-level / nested statement node types.
_FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
    exp.TruncateTable, exp.Command,  # Command covers ATTACH/SYSTEM/OPTIMIZE/etc. in ClickHouse
)


class UnsafeSqlError(Exception):
    """The AI-generated SQL violated the read-only SELECT allowlist."""


def guard_select(sql: str, limit: int = DEFAULT_LIMIT) -> str:
    """Validate and normalize a single read-only SELECT. Returns SQL with LIMIT enforced.

    Raises UnsafeSqlError on any violation.
    """
    sql = sql.strip().rstrip(";").strip()
    if not sql:
        raise UnsafeSqlError("empty query")

    try:
        statements = sqlglot.parse(sql, read="clickhouse")
    except Exception as err:  # parse failure = reject
        raise UnsafeSqlError(f"unparseable SQL: {err}") from err

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise UnsafeSqlError("exactly one statement is allowed")

    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        raise UnsafeSqlError(f"only SELECT is allowed, got {type(stmt).__name__}")

    # Reject any forbidden node anywhere in the tree (e.g. subquery DML, CTE writes).
    for node in stmt.walk():
        expr = node[0] if isinstance(node, tuple) else node
        if isinstance(expr, _FORBIDDEN):
            raise UnsafeSqlError(f"forbidden construct: {type(expr).__name__}")

    # Enforce LIMIT.
    if stmt.args.get("limit") is None:
        stmt = stmt.limit(limit)

    return stmt.sql(dialect="clickhouse")
