"""Conversão de valores para BRL."""

from __future__ import annotations

from decimal import Decimal


def convert_to_brl(amount: Decimal, currency: str, rates: dict[str, Decimal]) -> Decimal:
    """Converte um valor na moeda informada para BRL: ``amount * rate_to_brl``.

    A operação é feita inteiramente em Decimal e sem arredondamento; o arredondamento ocorre
    apenas na serialização do relatório.
    """
    rate = rates[currency]
    return amount * rate
