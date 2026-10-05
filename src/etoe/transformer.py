"""Lark Transformer for converting parse trees into the ÆToE AST."""

from __future__ import annotations

import json
from typing import Any

from lark import Transformer

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
    ScienceContext,
    SourceComment,
    Structure,
    Notation,
)


class EToETransformer(Transformer):
    """Transform a Lark CST into typed AST nodes."""

    def ether_file(self, items):
        return EToEFile(tuple(items))

    def statement(self, items):
        return items[0]

    def e_full_object(self, items):
        level = int(items[0])
        class_name = str(items[1])
        context, instance, structure = _tail(items[2:])
        return EFullObject(level, class_name, context, instance, structure)

    def e_compact_object(self, items):
        class_name = str(items[0])
        context, instance, structure = _tail(items[1:])
        return ECompactObject(class_name, context, instance, structure)

    def e_ether(self, items):
        role = subrole = None
        rest = items
        if rest and isinstance(rest[0], tuple) and len(rest[0]) == 3 and rest[0][0] == "qualifier":
            _, role, subrole = rest[0]
            rest = rest[1:]
        context, instance, structure = _tail(rest)
        return EEther(role, subrole, instance, structure)

    def e_etheron(self, items):
        role = subrole = None
        rest = items
        if rest and isinstance(rest[0], tuple) and len(rest[0]) == 3 and rest[0][0] == "qualifier":
            _, role, subrole = rest[0]
            rest = rest[1:]
        context, instance, structure = _tail(rest)
        return EEtheron(role, subrole, instance, structure)

    def e_level(self, items):
        return ELevel(int(items[0]))

    def e_unit(self, items):
        return EUnit(str(items[0]))

    def etheron_qualifier(self, items):
        if len(items) == 1:
            return ("qualifier", str(items[0]), None)
        return ("qualifier", str(items[0]), str(items[1]))

    def object_context(self, items):
        return ObjectContext(str(items[0]), str(items[1]) if len(items) >= 2 else None, str(items[2]) if len(items) >= 3 else None)

    def instance(self, items):
        pairs = items[0] if items else []
        return Instance(tuple(pairs))

    def pair_list(self, items):
        return list(items)

    def pair(self, items):
        return (str(items[0]), items[1])

    def structure(self, items):
        objects = tuple(items[0][0]) if items else ()
        separators = tuple(items[0][1]) if items else ()
        return Structure(objects, separators)

    def object_list(self, items):
        return _objects_and_separators(items)

    def chemical_object_list(self, items):
        return _objects_and_separators(items)

    def separator(self, items):
        sep = str(items[0])
        if len(items) == 1:
            return (sep, None)
        return (sep, items[1])

    def ATOMIC_MASS(self, token):
        return int(str(token))

    def chemical_structure(self, items):
        if not items:
            return Structure(())
        payload = items[0]
        if isinstance(payload, tuple):
            objects, separators = payload
            return Structure(tuple(objects), tuple(separators))
        return Structure(tuple(items), ())

    def chemical_full(self, items):
        symbol = str(items[0])
        subsort = None
        atomic_mass = None
        structure = None
        for item in items[1:]:
            if isinstance(item, int):
                atomic_mass = item
            elif isinstance(item, Structure):
                structure = item
            else:
                subsort = str(item)
        kind = "element" if symbol in _ELEMENT_SYMBOLS else "molecule"
        return ChemicalNotation(kind, symbol, subsort, atomic_mass, structure)

    def chemical_mass_only(self, items):
        return ChemicalNotation("mass", atomic_mass=int(items[0]))

    def PROTIUM_CORE(self, token):
        return ChemicalNotation("protium_core")

    def PROTON(self, token):
        return ChemicalNotation("proton")

    def NEUTRON(self, token):
        return ChemicalNotation("neutron")

    def constant_expression(self, items):
        return items[0]

    def quantity_expression(self, items):
        quantity = str(items[0])
        rest = list(items[1:])
        science = None
        if rest and isinstance(rest[0], ScienceContext):
            science = rest.pop(0)
        while any(isinstance(x, list) for x in rest):
            flattened = []
            for x in rest:
                flattened.extend(x if isinstance(x, list) else [x])
            rest = flattened
        aspects = tuple(x for x in rest if isinstance(x, Aspect))
        character = None
        obj = None
        for x in rest:
            if isinstance(x, Notation):
                obj = x
            elif isinstance(x, str) and character is None:
                character = str(x)
        if obj is None and items and isinstance(items[-1], Notation):
            obj = items[-1]
        return QuantityExpression(quantity, science, aspects, character, obj)

    def quantity_tail(self, items):
        return items

    def SCIENCE_PREFIX(self, token):
        parts = str(token)[1:].split(".")
        return ScienceContext(parts[0], tuple(parts[1:]))

    def aspect_expression(self, items):
        out = []
        for token in items:
            value = str(token)
            if value in {"dimension", "D", "space", "S", "time", "T", "history", "H"}:
                kind = "dimension"
            elif value in {"kinematic", "ka", "inertnic", "ia", "collisional", "ca"}:
                kind = "dynamic"
            elif value in {"substance_field", "sf", "hyperobject_medium", "hm"}:
                kind = "relation"
            elif value.startswith("state") or value in {"s1", "s2", "s3", "s4", "rest", "interaction", "departure", "arrival", "jump", "jmp", "s3s4", "free_cycle", "freec", "s1s3s4", "collision_cycle", "collc", "s1s2s3s4"}:
                kind = "state"
            else:
                kind = "delay"
            out.append(Aspect(kind, value))
        return out

    def const_full(self, items):
        return ConstantExpression("full", "", str(items[0]), str(items[1]), items[2])

    def const_compact_letter(self, items):
        return ConstantExpression("compact_letter", str(items[0]))

    def const_compact_at(self, items):
        return ConstantExpression("compact_at", str(items[0]))

    def measurement_expression(self, items):
        raw = str(items[0])
        value = float(raw) if "." in raw else int(raw)
        return MeasurementExpression(value, items[1])

    def STRING(self, token):
        return json.loads(str(token))

    def NUMBER(self, token):
        raw = str(token)
        return float(raw) if "." in raw else int(raw)


_ELEMENT_SYMBOLS = {
    "H","D","T","Ht","He","Li","Be","B","C","N","O","F","Ne","Na","Mg","Al","Si","P","S","Cl","Ar","K","Ca","Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn","Ga","Ge","As","Se","Br","Kr","Rb","Sr","Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd","In","Sn","Sb","Te","I","Xe","Cs","Ba","La","Ce","Pr","Nd","Pm","Sm","Eu","Gd","Tb","Dy","Ho","Er","Tm","Yb","Lu","Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg","Tl","Pb","Bi","Po","At","Rn","Fr","Ra","Ac","Th","Pa","U","Np","Pu","Am","Cm","Bk","Cf","Es","Fm","Md","No","Lr","Rf","Db","Sg","Bh","Hs","Mt","Ds","Rg","Cn"
}


def _tail(items):
    context = None
    instance = None
    structure = None
    for item in items:
        if isinstance(item, ObjectContext):
            context = item
        elif isinstance(item, Instance):
            instance = item
        elif isinstance(item, Structure):
            structure = item
    return context, instance, structure


def _objects_and_separators(items):
    objects = []
    separators = []
    for item in items:
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) and item[0] in {"|","!","$","*","'","^","&","~"}:
            separators.append(item[0])
        else:
            objects.append(item)
    return (objects, separators)
