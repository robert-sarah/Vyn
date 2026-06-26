"""Ownership Vyn — own / ref / move à l'exécution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


class OwnershipError(RuntimeError):
    """Violation des règles own/ref (use-after-move, etc.)."""


@dataclass
class OwnedValue:
    """Enveloppe runtime avec métadonnées ownership."""
    data: Any
    vtype: str
    is_mut: bool = False
    is_own: bool = False
    is_ref: bool = False
    moved: bool = False
    borrow_count: int = 0

    def check_read(self, name: str = "") -> None:
        if self.moved:
            raise OwnershipError(f"use after move: {name or 'value'}")

    def move_out(self, name: str = "") -> Any:
        self.check_read(name)
        if self.is_own:
            self.moved = True
        return self.data

    def borrow(self) -> None:
        if self.moved:
            raise OwnershipError("borrow after move")
        self.borrow_count += 1

    def release_borrow(self) -> None:
        self.borrow_count = max(0, self.borrow_count - 1)


def from_type_node(typ, data: Any, is_mut: bool) -> OwnedValue:
    is_own = bool(typ and getattr(typ, "is_own", False))
    is_ref = bool(typ and getattr(typ, "is_ref", False))
    vtype = typ.name if typ else "i32"
    return OwnedValue(data, vtype, is_mut or is_ref, is_own, is_ref)
