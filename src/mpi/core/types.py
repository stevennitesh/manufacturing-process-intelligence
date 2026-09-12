"""Shared semantic identifier types."""

from typing import NewType

UnitId = NewType("UnitId", str)
BatchId = NewType("BatchId", str)
OperationId = NewType("OperationId", str)
