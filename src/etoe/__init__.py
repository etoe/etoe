"""Reference Python implementation of ÆToE.

This package implements the specification layer; it is not itself the standard.
"""

from .ast import (
    Aspect,
    ChemicalNotation,
    ConstantExpression,
    ECompactObject,
    EFullObject,
    EEther,
    EEtheron,
    ELevel,
    EUnit,
    EToEFile,
    Instance,
    MeasurementExpression,
    ObjectContext,
    QuantityExpression,
    SourceComment,
    Statement,
    Structure,
)
from .parser import EToEParser, parse_file, parse_statement
from .serialization import decode_identifier, encode_identifier, encode_base64url_identifier, decode_base64url_identifier
from .units import EtherUnit, UNIT_BY_SUFFIX
from .validation import ValidationError, ValidationResult, validate

__version__ = "0.1.48"

__all__ = [
    "Aspect",
    "ChemicalNotation",
    "ConstantExpression",
    "ECompactObject",
    "EFullObject",
    "EEther",
    "EEtheron",
    "ELevel",
    "EUnit",
    "EToEFile",
    "Instance",
    "MeasurementExpression",
    "ObjectContext",
    "QuantityExpression",
    "SourceComment",
    "Statement",
    "Structure",
    "EToEParser",
    "parse_file",
    "parse_statement",
    "encode_identifier",
    "decode_identifier",
    "encode_base64url_identifier",
    "decode_base64url_identifier",
    "EtherUnit",
    "UNIT_BY_SUFFIX",
    "ValidationError",
    "ValidationResult",
    "validate",
]
