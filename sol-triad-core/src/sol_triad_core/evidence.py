"""
Интерфейс и реализации реестра авторитетных свидетельств (Evidence Registry).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from .errors import EpistemicStatus


@dataclass(frozen=True)
class EvidenceRecord:
    """Запись в авторитетном реестре свидетельств хоста."""
    evidence_id: str
    domain: str
    epistemic_status: EpistemicStatus
    timestamp_sec: float
    payload_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EvidenceRegistryOracle(ABC):
    """Абстрактный интерфейс авторитетного оракула/реестра свидетельств."""

    @abstractmethod
    def lookup(self, evidence_id: str) -> Optional[EvidenceRecord]:
        """Возвращает доверенную запись свидетельства или None при её отсутствии."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Проверяет доступность источника свидетельств."""
        pass


class InMemoryEvidenceRegistry(EvidenceRegistryOracle):
    """
    Потокобезопасная базовая реализация реестра в оперативной памяти хоста.
    Используется в тестах и автономных хост-контурах.
    """

    def __init__(self, available: bool = True):
        self._records: Dict[str, EvidenceRecord] = {}
        self._available = available

    def register(self, record: EvidenceRecord) -> None:
        """Регистрирует доверенную запись в реестре хоста."""
        self._records[record.evidence_id] = record

    def lookup(self, evidence_id: str) -> Optional[EvidenceRecord]:
        if not self._available:
            return None
        return self._records.get(evidence_id)

    def is_available(self) -> bool:
        return self._available

    def set_availability(self, available: bool) -> None:
        self._available = available
