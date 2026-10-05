"""Semantic validation for ÆToE AST nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .ast import (
    ChemicalNotation,
    ECompactObject,
    EFullObject,
    ELevel,
    EEther,
    EEtheron,
    EToEFile,
    Notation,
    Structure,
)
from .matter import CLASS_LEVELS


class ValidationError(ValueError):
    """Raised for strict validation mode."""


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.issues

    def raise_for_errors(self) -> None:
        if self.issues:
            raise ValidationError("; ".join(i.message for i in self.issues))


def validate(node: Notation | EToEFile, *, strict: bool = False) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if isinstance(node, EToEFile):
        for idx, stmt in enumerate(node.statements):
            _validate_node(stmt, issues, (f"statement[{idx}]",), parent_level=None)
    else:
        _validate_node(node, issues, (), parent_level=None)
    result = ValidationResult(tuple(issues))
    if strict:
        result.raise_for_errors()
    return result


def _validate_node(node: Notation, issues: list[ValidationIssue], path: tuple[str, ...], parent_level: int | None):
    current_level = None
    if isinstance(node, ELevel):
        if not 1 <= node.level <= 8:
            issues.append(ValidationIssue("level-range", f"Invalid matter level {node.level}.", path))
    elif isinstance(node, EFullObject):
        current_level = node.level
        expected = CLASS_LEVELS.get(node.class_name)
        if expected is not None and expected != node.level:
            issues.append(ValidationIssue(
                "class-level-mismatch",
                f"{node.to_canonical()}: class '{node.class_name}' is registered for level {expected}, not {node.level}.",
                path,
            ))
        if parent_level is not None and node.level > parent_level:
            issues.append(ValidationIssue(
                "upward-nesting",
                f"{node.to_canonical()}: a level-{node.level} subobject cannot be nested in a level-{parent_level} object.",
                path,
            ))
        if node.structure:
            for idx, child in enumerate(node.structure.objects):
                _validate_node(child, issues, path + ("structure", str(idx)), node.level)
    elif isinstance(node, ECompactObject):
        expected = CLASS_LEVELS.get(node.class_name)
        if expected is None:
            issues.append(ValidationIssue(
                "unknown-class",
                f"Unknown ÆToE object class '{node.class_name}'.",
                path,
            ))
        if node.structure:
            for idx, child in enumerate(node.structure.objects):
                _validate_node(child, issues, path + ("structure", str(idx)), expected)
    elif isinstance(node, (EEther, EEtheron)):
        if node.role == "m" and node.subrole is not None:
            issues.append(ValidationIssue("role-subrole", "Medium ether cannot use a role subrole.", path))
        if node.structure:
            for idx, child in enumerate(node.structure.objects):
                _validate_node(child, issues, path + ("structure", str(idx)), parent_level)
