"""Testes unitários do parser de offsets Kafka e entradas da medição."""
import pytest

from scripts.benchmark_ingestion import parse_group_lag


def test_parse_group_lag_sums_multiple_partitions():
    output = """GROUP TOPIC PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG CONSUMER-ID HOST CLIENT-ID
enade-indexer enade-questions 0 10 35 25 - - -
enade-indexer enade-questions 1 20 40 20 - - -
outro-grupo enade-questions 0 0 500 500 - - -
"""
    parsed = parse_group_lag(output)
    assert parsed["total"] == 45
    assert parsed["partitions"][0]["committed"] == 10
    assert parsed["partitions"][1]["end"] == 40


def test_parse_group_lag_empty_group_is_invalid():
    with pytest.raises(ValueError, match="Nenhum offset"):
        parse_group_lag("Consumer group 'enade-indexer' has no active members.")


def test_parse_group_lag_detects_inconsistent_offsets():
    output = "enade-indexer enade-questions 0 15 20 1 - - -"
    with pytest.raises(ValueError, match="inconsistente"):
        parse_group_lag(output)


def test_parse_group_lag_requires_committed_offset():
    output = "enade-indexer enade-questions 0 - 20 20 - - -"
    with pytest.raises(ValueError, match="Nenhum offset"):
        parse_group_lag(output)
