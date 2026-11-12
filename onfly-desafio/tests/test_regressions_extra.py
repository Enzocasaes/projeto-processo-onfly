"""Testes adicionais de regressão para os defeitos corrigidos e regras do README."""

from __future__ import annotations

import csv
import os
import re
import subprocess
import sys

from helpers import PROJECT_ROOT, SRC_DIR, run_cli

MONEY = re.compile(r"^-?\d+\.\d{2}$")


def test_reads_all_rows_beyond_200(tmp_path):
    """D1: o leitor não pode truncar o arquivo."""
    rows = [{"reservation_id": f"R-{i}"} for i in range(250)]
    report = run_cli(tmp_path, rows)
    assert report["summary"]["total_reservations"] == 250
    assert report["summary"]["confirmed_reservations"] == 250
    assert report["summary"]["total_room_nights"] == 250


def test_validation_sample_matches_readme(tmp_path):
    """Amostra de validação completa: summary, by_month e top_hotels."""
    with (PROJECT_ROOT / "data" / "exemplo-validacao.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    report = run_cli(tmp_path, rows)

    assert report["report_version"] == "1.0"
    assert report["summary"] == {
        "total_reservations": 12,
        "confirmed_reservations": 9,
        "cancelled_reservations": 2,
        "no_show_reservations": 1,
        "total_room_nights": 28,
        "total_amount_brl": "7566.00",
        "average_nightly_rate_brl": "270.21",
    }
    assert report["by_month"] == [
        {"month": "2025-01", "reservations": 8, "room_nights": 25, "total_brl": "6684.00"},
        {"month": "2025-02", "reservations": 1, "room_nights": 3, "total_brl": "882.00"},
    ]
    assert report["top_hotels"] == [
        {"hotel_id": "H01", "hotel_name": "Hotel Aurora Paulista", "room_nights": 3, "total_brl": "1200.00"},
        {"hotel_id": "H02", "hotel_name": "Hotel Mirante", "room_nights": 2, "total_brl": "1084.00"},
        {"hotel_id": "H12", "hotel_name": "Hotel Miami Beach", "room_nights": 1, "total_brl": "1000.00"},
        {"hotel_id": "H10", "hotel_name": "Hotel Madrid, Gran Vía", "room_nights": 4, "total_brl": "900.00"},
        {"hotel_id": "H09", "hotel_name": "Hotel Lisboa, Centro", "room_nights": 3, "total_brl": "882.00"},
    ]


def test_nights_across_year_boundary_and_full_month(tmp_path):
    """D3: virada de ano com vários quartos e estadia de exatamente um mês."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "checkin_date": "2024-12-30", "checkout_date": "2025-01-02", "rooms": "2"},
            {"reservation_id": "R-2", "checkin_date": "2025-01-15", "checkout_date": "2025-02-15", "rooms": "1"},
        ],
    )
    assert report["summary"]["total_room_nights"] == 6 + 31
    assert [(m["month"], m["room_nights"]) for m in report["by_month"]] == [("2024-12", 6), ("2025-01", 31)]


def test_eur_conversion_multiplies_rate(tmp_path):
    """D4: EUR também é multiplicado pela taxa."""
    report = run_cli(tmp_path, [{"currency": "EUR", "amount": "150.00"}])
    assert report["summary"]["total_amount_brl"] == "882.00"


def test_non_confirmed_excluded_from_breakdowns(tmp_path):
    """D2: CANCELLED, NO_SHOW e status desconhecido não entram em by_month nem top_hotels."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H01", "status": "CONFIRMED", "amount": "100.00"},
            {
                "reservation_id": "R-2",
                "hotel_id": "H02",
                "status": "NO_SHOW",
                "amount": "900.00",
                "checkin_date": "2025-03-01",
                "checkout_date": "2025-03-02",
            },
            {"reservation_id": "R-3", "hotel_id": "H03", "status": "CANCELLED", "amount": "800.00"},
            {"reservation_id": "R-4", "hotel_id": "H04", "status": "PENDING", "amount": "700.00"},
        ],
    )
    assert report["summary"]["total_reservations"] == 4
    assert report["summary"]["total_amount_brl"] == "100.00"
    assert [m["month"] for m in report["by_month"]] == ["2025-01"]
    assert report["by_month"][0]["reservations"] == 1
    assert [h["hotel_id"] for h in report["top_hotels"]] == ["H01"]


def test_top_hotels_tie_break_by_hotel_id_ascending(tmp_path):
    """D5: empate em total_brl é desempatado por hotel_id ascendente."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "hotel_id": "H03", "amount": "500.00"},
            {"reservation_id": "R-2", "hotel_id": "H01", "amount": "900.00"},
            {"reservation_id": "R-3", "hotel_id": "H02", "amount": "500.00"},
            {"reservation_id": "R-4", "hotel_id": "H04", "amount": "100.00"},
        ],
        top=3,
    )
    assert [h["hotel_id"] for h in report["top_hotels"]] == ["H01", "H02", "H03"]


def test_top_returns_fewer_when_not_enough_hotels(tmp_path):
    report = run_cli(tmp_path, [{"hotel_id": "H01"}], top=5)
    assert len(report["top_hotels"]) == 1


def test_rounding_happens_only_on_serialization(tmp_path):
    """Soma valores exatos e arredonda só no final: 0.005 + 0.005 = 0.01 (não 0.02)."""
    report = run_cli(
        tmp_path,
        [
            {"reservation_id": "R-1", "amount": "0.005"},
            {"reservation_id": "R-2", "amount": "0.005"},
        ],
    )
    assert report["summary"]["total_amount_brl"] == "0.01"


def test_rounding_is_half_up(tmp_path):
    """0.125 vira 0.13 (half-up), não 0.12 (half-even)."""
    report = run_cli(tmp_path, [{"amount": "0.125"}])
    assert report["summary"]["total_amount_brl"] == "0.13"


def test_average_without_nights_is_zero(tmp_path):
    report = run_cli(tmp_path, [{"status": "CANCELLED"}])
    assert report["summary"]["total_room_nights"] == 0
    assert report["summary"]["average_nightly_rate_brl"] == "0.00"
    assert report["by_month"] == []
    assert report["top_hotels"] == []


def test_report_schema_and_money_format(tmp_path):
    report = run_cli(tmp_path, [{"currency": "USD", "amount": "1234.57", "rooms": "3"}])
    assert set(report) == {"report_version", "generated_at", "summary", "by_month", "top_hotels"}
    assert report["generated_at"].endswith("-03:00")
    assert set(report["by_month"][0]) == {"month", "reservations", "room_nights", "total_brl"}
    assert set(report["top_hotels"][0]) == {"hotel_id", "hotel_name", "room_nights", "total_brl"}
    for key in ("total_amount_brl", "average_nightly_rate_brl"):
        assert MONEY.match(report["summary"][key])
    assert report["summary"]["total_amount_brl"] == "6691.37"


def _run_raw(*args: str) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "onfly_report", *args],
        cwd=str(PROJECT_ROOT),
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_exit_code_2_for_invalid_top(tmp_path):
    result = _run_raw(
        "--input", "data/exemplo-validacao.csv", "--rates", "data/taxas_cambio.csv",
        "--output", str(tmp_path / "r.json"), "--top", "0",
    )
    assert result.returncode == 2


def test_exit_code_2_for_missing_input(tmp_path):
    result = _run_raw(
        "--input", str(tmp_path / "nao-existe.csv"), "--rates", "data/taxas_cambio.csv",
        "--output", str(tmp_path / "r.json"),
    )
    assert result.returncode == 2
