"""Cálculo de noites ocupadas."""

from __future__ import annotations

from datetime import date


def calculate_room_nights(checkin: date, checkout: date, rooms: int) -> int:
    """Calcula noites de quarto: diferença de dias (não inclusiva) vezes quartos.

    Subtrai as datas inteiras (timedelta), não o dia do mês, para valer também na virada de
    mês e de ano.
    """
    return (checkout - checkin).days * rooms
