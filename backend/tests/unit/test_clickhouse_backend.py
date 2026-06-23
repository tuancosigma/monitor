"""Unit tests for the ClickHouse Sigma Rule SQL Compiler."""

from __future__ import annotations

from app.detection.clickhouse_backend import compile_sigma_rule
from app.detection.sigma_loader import parse_sigma_rule


def test_compile_simple_match_rule() -> None:
    rule_yaml = """
    id: 11111111-2222-3333-4444-555555555555
    title: Mimikatz Execution
    severity: critical
    status: stable
    detection:
      selection:
        process_name: mimikatz.exe
        event_category: process
      condition: selection
    """
    rule = parse_sigma_rule(rule_yaml)
    sql, params = compile_sigma_rule(rule)

    assert "WHERE `@timestamp` >= {start_time:DateTime64}" in sql
    # The fields can be in any order, so check them individually
    assert "process_name = {p_0:String}" in sql or "process_name = {p_1:String}" in sql
    assert "event_category = {p_0:String}" in sql or "event_category = {p_1:String}" in sql
    assert set(params.values()) == {"mimikatz.exe", "process"}


def test_compile_modifiers() -> None:
    rule_yaml = """
    id: 22222222-3333-4444-5555-666666666666
    title: Suspect Web Request
    severity: medium
    detection:
      selection:
        process_executable|endswith: cmd.exe
        process_command_line|contains: powershell
        user_name|startswith: adm
      condition: selection
    """
    rule = parse_sigma_rule(rule_yaml)
    sql, params = compile_sigma_rule(rule)

    assert "endsWith(process_executable, {p_0:String})" in sql
    assert "positionCaseInsensitive(process_command_line, {p_1:String}) > 0" in sql
    assert "startsWith(user_name, {p_2:String})" in sql
    assert params["p_0"] == "cmd.exe"
    assert params["p_1"] == "powershell"
    assert params["p_2"] == "adm"


def test_compile_list_modifiers() -> None:
    rule_yaml = """
    id: 33333333-4444-5555-6666-777777777777
    title: Suspect Web Request Lists
    severity: low
    detection:
      selection:
        process_executable|endswith:
          - cmd.exe
          - powershell.exe
      condition: selection
    """
    rule = parse_sigma_rule(rule_yaml)
    sql, params = compile_sigma_rule(rule)

    expected = (
        "(endsWith(process_executable, {p_0:String})"
        " OR endsWith(process_executable, {p_1:String}))"
    )
    assert expected in sql
    assert params["p_0"] == "cmd.exe"
    assert params["p_1"] == "powershell.exe"


def test_compile_condition_expansion() -> None:
    rule_yaml = """
    id: 44444444-5555-6666-7777-888888888888
    title: Multiple Selections Condition
    severity: low
    detection:
      sel1:
        event_category: authentication
      sel2:
        event_outcome: failure
      condition: sel1 and not sel2
    """
    rule = parse_sigma_rule(rule_yaml)
    sql, _params = compile_sigma_rule(rule)

    # sel1 should compile to (event_category = {p_0:String})
    # and sel2 to (event_outcome = {p_1:String})
    # Then combined as (sel1) AND NOT (sel2)
    assert "event_category = {p_0:String}" in sql or "event_category = {p_1:String}" in sql
    assert "event_outcome = {p_0:String}" in sql or "event_outcome = {p_1:String}" in sql
    assert "AND NOT" in sql


def test_compile_condition_all_any_expansion() -> None:
    rule_yaml = """
    id: 55555555-6666-7777-8888-999999999999
    title: Condition Expansions
    severity: low
    detection:
      selection1:
        event_category: authentication
      selection2:
        event_outcome: failure
      condition: any of selection*
    """
    rule = parse_sigma_rule(rule_yaml)
    sql, _params = compile_sigma_rule(rule)

    # should expand to selection1 or selection2
    assert "OR" in sql
    assert "event_category = {p_0:String}" in sql or "event_category = {p_1:String}" in sql
    assert "event_outcome = {p_0:String}" in sql or "event_outcome = {p_1:String}" in sql


def test_compile_count_aggregation() -> None:
    rule_yaml = """
    id: 5a8a478b-302a-4db5-b82b-8a8b13c7dbba
    title: SSH Brute Force
    severity: high
    detection:
      selection:
        event_category: authentication
        event_outcome: failure
      condition: selection
      timeframe: 1m
      count:
        field: source_ip
        op: gte
        value: 5
    """
    rule = parse_sigma_rule(rule_yaml)
    sql, params = compile_sigma_rule(rule)

    assert "SELECT" in sql
    assert "source_ip AS entity_val" in sql
    assert "GROUP BY entity_val" in sql
    assert "HAVING cnt >= {count_threshold:Int64}" in sql
    assert params["count_threshold"] == 5
