"""Cryptographic Hash Chain for Pre-SOL Task Framing.

Inspired by belov-fiber-sdk immutable log verification:
Provides tamper-evident local truth protection across diagnostic phases,
preventing retroactive modification of extracted statements, observed facts,
or safety barrier states.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import json
import time


class ChainIntegrityError(Exception):
    """Raised when hash chain tampering or verification failure occurs."""
    pass


@dataclass
class DiagnosticBlock:
    """An individual block in the diagnostic hash chain."""
    index: int
    timestamp: float
    step_name: str
    prev_hash: str
    payload: Dict[str, Any]
    block_hash: str = ""

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 over canonical block components."""
        canonical_payload = json.dumps(
            self.payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        )
        canonical_repr = (
            f"{self.index}|"
            f"{self.timestamp:.6f}|"
            f"{self.step_name}|"
            f"{self.prev_hash}|"
            f"{canonical_payload}"
        )
        return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "step_name": self.step_name,
            "prev_hash": self.prev_hash,
            "payload": self.payload,
            "block_hash": self.block_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiagnosticBlock":
        return cls(
            index=int(data["index"]),
            timestamp=float(data["timestamp"]),
            step_name=str(data["step_name"]),
            prev_hash=str(data["prev_hash"]),
            payload=dict(data.get("payload", {})),
            block_hash=str(data.get("block_hash", "")),
        )


class DiagnosticHashChain:
    """Tamper-evident sequential hash chain for Pre-SOL diagnostic stages.
    
    Guarantees:
    - Every diagnostic step is sealed with a SHA-256 pointer to the previous step.
    - Retroactive alteration of any premise, raw query, or barrier state breaks the chain.
    - The head hash (tip of the chain) can be bound to kernel EvidenceRecords as payload_hash.
    """
    GENESIS_PREV_HASH = "0" * 64

    def __init__(self, blocks: Optional[List[DiagnosticBlock]] = None):
        self.blocks: List[DiagnosticBlock] = []
        if blocks:
            for b in blocks:
                self.blocks.append(b)

    @property
    def head_hash(self) -> str:
        """Returns the hash of the latest block, or genesis hash if empty."""
        if not self.blocks:
            return self.GENESIS_PREV_HASH
        return self.blocks[-1].block_hash

    @property
    def length(self) -> int:
        return len(self.blocks)

    def append(
        self,
        step_name: str,
        payload: Dict[str, Any],
        timestamp: Optional[float] = None
    ) -> DiagnosticBlock:
        """Appends a new diagnostic step block to the chain."""
        index = len(self.blocks)
        ts = timestamp if timestamp is not None else time.time()
        prev_hash = self.head_hash

        block = DiagnosticBlock(
            index=index,
            timestamp=ts,
            step_name=step_name,
            prev_hash=prev_hash,
            payload=payload,
        )
        block.block_hash = block.compute_hash()
        self.blocks.append(block)
        return block

    def verify_integrity(self) -> Tuple[bool, Optional[int], Optional[str]]:
        """Verifies integrity of the entire chain from genesis to head.
        
        Returns:
            (True, None, None) if valid.
            (False, corrupted_index, reason) if corrupted.
        """
        expected_prev = self.GENESIS_PREV_HASH
        for idx, block in enumerate(self.blocks):
            if block.index != idx:
                return False, idx, f"Index mismatch at block {idx}: expected {idx}, got {block.index}"
            
            if block.prev_hash != expected_prev:
                return (
                    False,
                    idx,
                    f"Previous hash broken at block {idx}: expected {expected_prev}, got {block.prev_hash}"
                )
            
            recomputed = block.compute_hash()
            if block.block_hash != recomputed:
                return (
                    False,
                    idx,
                    f"Block hash corrupted at block {idx}: expected {recomputed}, got {block.block_hash}"
                )
            
            expected_prev = block.block_hash

        return True, None, None

    def export_audit_trail(self) -> List[Dict[str, Any]]:
        """Exports raw serializable list of block dictionaries."""
        return [b.to_dict() for b in self.blocks]

    @classmethod
    def from_audit_trail(cls, trail: List[Dict[str, Any]]) -> "DiagnosticHashChain":
        """Reconstructs and verifies a hash chain from an audit trail list."""
        chain = cls([DiagnosticBlock.from_dict(d) for d in trail])
        is_valid, bad_idx, err = chain.verify_integrity()
        if not is_valid:
            raise ChainIntegrityError(f"Audit trail integrity verification failed at block {bad_idx}: {err}")
        return chain
