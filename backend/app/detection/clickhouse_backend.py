"""ClickHouse query compiler for Sigma rules.

Compiles a standard SigmaRule structure (including selections, modifier suffixes,
logical conditions, timeframe, and aggregation filters) into a secure, parameterized
ClickHouse SQL SELECT statement.
"""

from __future__ import annotations

import re
from typing import Any

from app.detection.sigma_loader import SigmaRule

# Known columns in the ClickHouse `events` table (Phase 1 schema)
KNOWN_COLUMNS = {
    "event_kind",
    "event_category",
    "event_type",
    "event_action",
    "event_severity",
    "event_outcome",
    "event_dataset",
    "message",
    "host_name",
    "host_ip",
    "observer_vendor",
    "observer_product",
    "source_ip",
    "source_port",
    "source_geo_country_iso_code",
    "destination_ip",
    "destination_port",
    "network_protocol",
    "network_transport",
    "network_bytes",
    "user_name",
    "user_id",
    "user_domain",
    "process_name",
    "process_pid",
    "process_command_line",
    "process_executable",
    "file_path",
    "file_name",
    "file_hash_sha256",
    "log_level",
    "log_logger",
    "threat_tactic_name",
    "threat_technique_id",
    "threat_technique_name",
    "labels",
    "tags",
    "raw",
}

# Standard field name mappings from Windows/Sysmon/generic logs to ECS-lite fields
FIELD_MAPPING = {
    "image": "process_executable",
    "process_name": "process_name",
    "processname": "process_name",
    "commandline": "process_command_line",
    "command_line": "process_command_line",
    "parentimage": "process_executable",
    "parentprocessname": "process_name",
    "username": "user_name",
    "user": "user_name",
    "src_ip": "source_ip",
    "sourceip": "source_ip",
    "dst_ip": "destination_ip",
    "destip": "destination_ip",
    "src_port": "source_port",
    "dst_port": "destination_port",
    "eventcategory": "event_category",
    "eventoutcome": "event_outcome",
    "eventaction": "event_action",
    "file": "file_path",
    "filename": "file_name",
    "filepath": "file_path",
    "hash": "file_hash_sha256",
}

OP_MAP = {
    "gte": ">=",
    "gt": ">",
    "lte": "<=",
    "lt": "<",
    "eq": "=",
    "ne": "!=",
}


def compile_field_to_sql(
    field_name_with_modifiers: str, value: Any, params: dict[str, Any]
) -> str:
    """Compile a single selection key-value pair with modifiers to ClickHouse SQL."""
    parts = field_name_with_modifiers.split("|")
    base_field = parts[0]
    modifiers = [m.lower() for m in parts[1:]]

    # Map base field to column
    column = FIELD_MAPPING.get(base_field.lower(), base_field.lower())
    if column not in KNOWN_COLUMNS:
        # Compile as Map index for custom/extra fields
        column = f"labels['{base_field}']"

    is_array = column in ("host_ip", "tags")
    values_list = value if isinstance(value, list) else [value]

    joiner = " AND " if "all" in modifiers else " OR "
    value_sqls = []

    for val in values_list:
        p_name = f"p_{len(params)}"
        if isinstance(val, int):
            p_type = "Int64"
        elif isinstance(val, float):
            p_type = "Float64"
        elif isinstance(val, bool):
            p_type = "UInt8"
            val = 1 if val else 0
        else:
            p_type = "String"
            val = str(val)

        params[p_name] = val
        placeholder = f"{{{p_name}:{p_type}}}"

        # Standardize modifiers
        # e.g., endswith, startswith, contains, re
        if not modifiers or (len(modifiers) == 1 and modifiers[0] == "all"):
            if is_array:
                value_sqls.append(f"has({column}, {placeholder})")
            else:
                value_sqls.append(f"{column} = {placeholder}")
        else:
            primary_modifier = next(m for m in modifiers if m != "all")
            if primary_modifier == "contains":
                value_sqls.append(f"positionCaseInsensitive({column}, {placeholder}) > 0")
            elif primary_modifier == "startswith":
                value_sqls.append(f"startsWith({column}, {placeholder})")
            elif primary_modifier == "endswith":
                value_sqls.append(f"endsWith({column}, {placeholder})")
            elif primary_modifier == "re":
                value_sqls.append(f"match({column}, {placeholder})")
            else:
                # Default exact match fallback
                if is_array:
                    value_sqls.append(f"has({column}, {placeholder})")
                else:
                    value_sqls.append(f"{column} = {placeholder}")

    if len(value_sqls) == 1:
        return value_sqls[0]
    return f"({joiner.join(value_sqls)})"


def compile_selection_to_sql(selection_dict: dict[str, Any], params: dict[str, Any]) -> str:
    """Compile a complete selection dictionary (joined by AND)."""
    field_sqls = []
    for k, v in selection_dict.items():
        field_sqls.append(compile_field_to_sql(k, v, params))
    if not field_sqls:
        return "1=1"
    if len(field_sqls) == 1:
        return field_sqls[0]
    return "(" + " AND ".join(field_sqls) + ")"


def expand_condition_strings(condition_str: str, selection_keys: list[str]) -> str:
    """Expand Sigma operators like 'all of...', 'any of...' and 'them' to explicit selections."""
    cond = condition_str.strip()

    # Expand "all of them" and "any/1 of them"
    if cond.lower() == "all of them":
        return " ( " + " and ".join(selection_keys) + " ) "
    if cond.lower() in ("any of them", "1 of them"):
        return " ( " + " or ".join(selection_keys) + " ) "

    # Expand "all of selection*" or "any/1 of selection*"
    def replace_match(match: re.Match[str]) -> str:
        op = match.group(1).lower()
        pattern = match.group(2)

        if pattern.endswith("*"):
            prefix = pattern[:-1]
            matching_keys = [k for k in selection_keys if k.startswith(prefix)]
        else:
            matching_keys = [k for k in selection_keys if k == pattern]

        if not matching_keys:
            raise ValueError(f"No selection keys matched pattern: {pattern}")

        joiner = " and " if op == "all" else " or "
        return " ( " + joiner.join(matching_keys) + " ) "

    cond = re.sub(
        r"\b(all|any|1)\s+of\s+([a-zA-Z0-9_\*]+)",
        replace_match,
        cond,
        flags=re.IGNORECASE,
    )
    return cond


def compile_condition_to_sql(
    condition_str: str, selection_sqls: dict[str, str], selection_keys: list[str]
) -> str:
    """Compile condition expression (including parentheses, and, or, not) into SQL logic."""
    expanded = expand_condition_strings(condition_str, selection_keys)
    tokens = re.split(r"(\s+|\(|\))", expanded)
    compiled_tokens = []

    for token in tokens:
        token_strip = token.strip()
        tok_lower = token_strip.lower()

        if not token_strip:
            compiled_tokens.append(token)  # Keep whitespace
        elif token_strip in ("(", ")"):
            compiled_tokens.append(token_strip)
        elif tok_lower == "and":
            compiled_tokens.append("AND")
        elif tok_lower == "or":
            compiled_tokens.append("OR")
        elif tok_lower == "not":
            compiled_tokens.append("NOT")
        elif token_strip in selection_sqls:
            compiled_tokens.append(f"({selection_sqls[token_strip]})")
        else:
            raise ValueError(
                f"Unrecognized identifier or syntax in Sigma condition: '{token_strip}'"
            )

    return "".join(compiled_tokens)


def compile_sigma_rule(
    rule: SigmaRule,
) -> tuple[str, dict[str, Any]]:
    """Compile a SigmaRule into a ClickHouse SELECT query and its parameters.

    Returns:
        A tuple of (sql_query, params_dict)
    """
    params: dict[str, Any] = {}

    # 1. Compile each selection block
    selection_sqls = {}
    for name, sel in rule.detection.selections.items():
        if isinstance(sel, dict):
            selection_sqls[name] = compile_selection_to_sql(sel, params)
        else:
            # Simple rules can sometimes define selection directly as list/value
            selection_sqls[name] = compile_field_to_sql(name, sel, params)

    # 2. Compile condition to SQL logic
    where_clause = compile_condition_to_sql(
        rule.detection.condition, selection_sqls, list(rule.detection.selections.keys())
    )

    # 3. Base time boundary parameter placeholders
    # We prefix time parameters to avoid collision with rule parameters
    time_filters = (
        "`@timestamp` >= {start_time:DateTime64} "
        "AND `@timestamp` < {end_time:DateTime64}"
    )

    # 4. Aggregation query or Individual events query
    if rule.detection.count:
        count_field = rule.detection.count.get("field")
        count_op = rule.detection.count.get("op", "gte")
        count_val = rule.detection.count.get("value")

        op_sql = OP_MAP.get(str(count_op).lower(), ">=")

        if count_field:
            group_col = FIELD_MAPPING.get(count_field.lower(), count_field.lower())
            if group_col not in KNOWN_COLUMNS:
                group_col = f"labels['{count_field}']"
            group_select = f"{group_col} AS entity_val"
            group_by = "GROUP BY entity_val"
        else:
            # Grouping globally if no group field
            group_select = "'' AS entity_val"
            group_by = "GROUP BY entity_val"

        # Parameterize aggregation count value
        params["count_threshold"] = int(count_val) if count_val is not None else 1

        sql = f"""SELECT
    {group_select},
    count() AS cnt,
    groupArray(10)(tuple(
        `@timestamp`, message, host_name, user_name,
        source_ip, destination_ip, event_category, event_outcome
    )) as samples
FROM events
WHERE {time_filters} AND ({where_clause})
{group_by}
HAVING cnt {op_sql} {{count_threshold:Int64}}
ORDER BY cnt DESC
LIMIT 1000"""  # noqa: S608

    else:
        # Simple match query: returns matching rows
        sql = f"""SELECT
    `@timestamp`,
    message,
    host_name,
    user_name,
    source_ip,
    destination_ip,
    event_category,
    event_outcome
FROM events
WHERE {time_filters} AND ({where_clause})
ORDER BY `@timestamp` DESC
LIMIT 1000"""  # noqa: S608

    return sql, params
