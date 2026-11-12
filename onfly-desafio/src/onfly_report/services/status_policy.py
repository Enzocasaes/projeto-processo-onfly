"""Política de status das reservas."""

from __future__ import annotations

BILLABLE_STATUS = "CONFIRMED"


def is_billable(status: str) -> bool:
    """Indica se a reserva entra nos totais financeiros e de noites.

    Lista de inclusão: apenas CONFIRMED é faturável. CANCELLED, NO_SHOW e qualquer status
    desconhecido ficam fora de noites, valores, by_month e top_hotels.
    """
    return status == BILLABLE_STATUS
