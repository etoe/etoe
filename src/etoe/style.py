"""Declarative, cascading styles for ÆToE visualizations.

The style engine is renderer-neutral. Adapters may resolve selectors against an
element context and then translate the resulting properties to Graphviz, CSS,
LaTeX, Manim, or another backend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import sys
import sysconfig
import tomllib
from functools import lru_cache
from typing import Any, Mapping, Sequence


MODES = ("Light", "Dark")
TARGETS = ("GraphViz", "3D", "LaTeX", "Manim", "Books", "Articles", "Web")
TARGET_ALIASES = {
    "graphviz": "GraphViz", "dot": "GraphViz", "gv": "GraphViz",
    "3d": "3D", "three-d": "3D", "three_d": "3D",
    "latex": "LaTeX", "tex": "LaTeX",
    "manim": "Manim", "book": "Books", "books": "Books",
    "article": "Articles", "articles": "Articles",
    "web": "Web", "html": "Web", "website": "Web",
}
INHERITED_PROPERTIES = frozenset({
    "fontname", "fontcolor", "fontsize", "fontweight", "fontstyle",
    "color", "textcolor", "opacity", "lineheight", "letterspacing",
})
STYLE_NAMES = ("graphviz", "3d", "latex", "manim", "books", "articles", "web")
SOURCES = TARGETS
SOURCE_ALIASES = TARGET_ALIASES


class StyleError(ValueError):
    """Raised when a style mode, target, selector, or stylesheet is invalid."""


def normalize_mode(value: str | None, *, default: str = "Light") -> str:
    value = default if value is None else str(value)
    canonical = {mode.casefold(): mode for mode in MODES}
    try:
        return canonical[value.strip().casefold()]
    except KeyError as exc:
        raise StyleError(f"Unknown style mode {value!r}; expected Light or Dark.") from exc


def normalize_target(value: str | None, *, default: str = "GraphViz") -> str:
    value = default if value is None else str(value)
    key = value.strip().casefold()
    if key in TARGET_ALIASES:
        return TARGET_ALIASES[key]
    for target in TARGETS:
        if key == target.casefold():
            return target
    raise StyleError(f"Unknown style target {value!r}; expected one of {', '.join(TARGETS)}.")


def normalize_source(value: str | None, *, default: str = "GraphViz") -> str:
    """Normalize the source visualization environment name."""
    value = default if value is None else str(value)
    key = value.strip().casefold()
    if key in SOURCE_ALIASES:
        return SOURCE_ALIASES[key]
    for source in SOURCES:
        if key == source.casefold():
            return source
    raise StyleError(f"Unknown style source {value!r}; expected one of {', '.join(SOURCES)}.")


@dataclass(frozen=True, slots=True)
class StyleSettings:
    """Global defaults for theme, target renderer, and source environment."""

    mode: str = "Light"
    target: str = "GraphViz"
    source: str = "GraphViz"

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", normalize_mode(self.mode))
        object.__setattr__(self, "target", normalize_target(self.target))
        object.__setattr__(self, "source", normalize_source(self.source))


_ENV_MODE = os.getenv("ETOE_STYLE_MODE", "Light")
_ENV_TARGET = os.getenv("ETOE_STYLE_TARGET", "GraphViz")
_ENV_SOURCE = os.getenv("ETOE_STYLE_SOURCE", "GraphViz")
_SETTINGS = StyleSettings(_ENV_MODE, _ENV_TARGET, _ENV_SOURCE)


def get_style_settings() -> StyleSettings:
    """Return the current process-wide style settings."""
    return _SETTINGS


def configure_styles(
    *,
    mode: str | None = None,
    target: str | None = None,
    source: str | None = None,
    Mode: str | None = None,
    Target: str | None = None,
    Source: str | None = None,
) -> StyleSettings:
    """Set process-wide Mode, Target, and Source defaults.

    Lowercase arguments take precedence over their capitalized aliases. The
    capitalized spellings are accepted to match ÆToE design terminology.
    """
    global _SETTINGS
    chosen_mode = mode if mode is not None else Mode
    chosen_target = target if target is not None else Target
    chosen_source = source if source is not None else Source
    _SETTINGS = StyleSettings(
        mode=normalize_mode(chosen_mode, default=_SETTINGS.mode),
        target=normalize_target(chosen_target, default=_SETTINGS.target),
        source=normalize_source(chosen_source, default=_SETTINGS.source),
    )
    return _SETTINGS


def reset_styles() -> StyleSettings:
    """Reset global settings to environment-derived defaults."""
    global _SETTINGS
    _SETTINGS = StyleSettings(_ENV_MODE, _ENV_TARGET, _ENV_SOURCE)
    return _SETTINGS


@dataclass(frozen=True, slots=True)
class StyleElement:
    """Selector-match context for one visual object."""

    tag: str = "*"
    classes: frozenset[str] = frozenset()
    element_id: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)
    ancestors: tuple["StyleElement", ...] = ()

    @classmethod
    def create(
        cls,
        tag: str = "*",
        *,
        classes: Sequence[str] | set[str] | frozenset[str] = (),
        element_id: str | None = None,
        attributes: Mapping[str, Any] | None = None,
        ancestors: Sequence["StyleElement"] = (),
    ) -> "StyleElement":
        return cls(
            tag=tag,
            classes=frozenset(classes),
            element_id=element_id,
            attributes=dict(attributes or {}),
            ancestors=tuple(ancestors),
        )


@dataclass(frozen=True, slots=True)
class _Rule:
    selector: str
    properties: Mapping[str, Any]
    order: int
    important: bool = False
    modes: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()


def _split_compound(selector: str) -> tuple[str | None, str | None, list[str], list[tuple[str, str, str]]]:
    """Parse a deliberately small CSS-like compound selector."""
    token = selector.strip()
    tag_match = re.match(r"^[A-Za-z_*][\w-]*", token)
    tag = tag_match.group(0) if tag_match else None
    if tag == "*":
        tag = None
    element_id = None
    ids = re.findall(r"#([\w-]+)", token)
    if ids:
        element_id = ids[-1]
    classes = re.findall(r"\.([\w-]+)", token)
    attrs = []
    for match in re.finditer(r"\[\s*([\w-]+)\s*(=|~=|\^=|\$=|\*=)\s*['\"]?([^'\"\]]+)['\"]?\s*\]", token):
        attrs.append((match.group(1), match.group(2), match.group(3).strip()))
    return tag, element_id, classes, attrs


def _compound_matches(compound: str, element: StyleElement) -> bool:
    tag, element_id, classes, attrs = _split_compound(compound)
    if tag and element.tag.casefold() != tag.casefold():
        return False
    if element_id is not None and element.element_id != element_id:
        return False
    if any(class_name not in element.classes for class_name in classes):
        return False
    for key, operator, expected in attrs:
        actual = element.attributes.get(key)
        if actual is None:
            return False
        actual_text = str(actual)
        if operator == "=" and actual_text != expected:
            return False
        if operator == "~=" and expected not in actual_text.split():
            return False
        if operator == "^=" and not actual_text.startswith(expected):
            return False
        if operator == "$=" and not actual_text.endswith(expected):
            return False
        if operator == "*=" and expected not in actual_text:
            return False
    return True


def _selector_matches(selector: str, element: StyleElement) -> bool:
    """Match compound selectors with descendant and direct-child combinators."""
    tokens = re.findall(r"[^\s>]+|>", selector.strip())
    if not tokens:
        return False
    compounds: list[str] = []
    relations: list[str] = []
    pending_relation = " "  # descendant by default
    for token in tokens:
        if token == ">":
            pending_relation = ">"
            continue
        if compounds:
            relations.append(pending_relation)
        compounds.append(token)
        pending_relation = " "
    if not _compound_matches(compounds[-1], element):
        return False

    # `ancestors` are provided root-to-parent; match from the parent outward.
    ancestors = list(reversed(element.ancestors))
    ancestor_index = 0
    for index in range(len(compounds) - 2, -1, -1):
        relation = relations[index]
        if relation == ">":
            if (
                ancestor_index >= len(ancestors)
                or not _compound_matches(compounds[index], ancestors[ancestor_index])
            ):
                return False
            ancestor_index += 1
        else:
            while (
                ancestor_index < len(ancestors)
                and not _compound_matches(compounds[index], ancestors[ancestor_index])
            ):
                ancestor_index += 1
            if ancestor_index >= len(ancestors):
                return False
            ancestor_index += 1
    return True


def selector_specificity(selector: str) -> tuple[int, int, int]:
    """Return CSS-style (IDs, classes/attributes, type selectors) specificity."""
    ids = classes = types = 0
    for compound in re.findall(r"[^\s>]+", selector.strip()):
        tag, _element_id, cls, attrs = _split_compound(compound)
        ids += len(re.findall(r"#([\w-]+)", compound))
        classes += len(cls) + len(attrs)
        if tag is not None:
            types += 1
    return ids, classes, types


def _resolve_variables(value: Any, palette: Mapping[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$palette."):
        current: Any = palette
        for part in value[len("$palette."):].split("."):
            if not isinstance(current, Mapping) or part not in current:
                raise StyleError(f"Undefined style variable {value!r}.")
            current = current[part]
        return current
    if isinstance(value, dict):
        return {key: _resolve_variables(item, palette) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_variables(item, palette) for item in value]
    return value


class StyleSheet:
    """Loaded stylesheet with deterministic cascade and inheritance semantics."""

    def __init__(self, name: str, data: Mapping[str, Any]) -> None:
        self.name = name
        self.data = dict(data)
        self.rules: tuple[_Rule, ...] = tuple(
            _Rule(
                selector=str(row["selector"]),
                properties=dict(row.get("properties", {})),
                order=index,
                important=bool(row.get("important", False)),
                modes=tuple(row.get("modes", ())),
                targets=tuple(normalize_target(t) for t in row.get("targets", ())),
            )
            for index, row in enumerate(self.data.get("rules", ()))
        )

    def resolve(
        self,
        element: StyleElement | str,
        *,
        mode: str | None = None,
        target: str | None = None,
        parent: Mapping[str, Any] | None = None,
        inline: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve properties for a selector context.

        Cascade order, from weakest to strongest:
        theme defaults; target defaults; inherited properties; matching rules
        ordered by importance then specificity then source order; inline values.
        """
        settings = get_style_settings()
        selected_mode = normalize_mode(mode, default=settings.mode)
        selected_target = normalize_target(target, default=settings.target)
        if isinstance(element, str):
            element = StyleElement.create_from_selector(element) if hasattr(StyleElement, "create_from_selector") else _element_from_selector(element)
        theme = self.data.get("themes", {}).get(selected_mode, {})
        target_theme = (
            self.data.get("target_themes", {})
            .get(selected_target, {})
            .get(selected_mode, {})
        )
        tag = element.tag
        result: dict[str, Any] = dict(theme.get(tag, {}))
        result.update(target_theme.get(tag, {}))
        target_defaults = (
            self.data.get("target_overrides", {})
            .get(selected_target, {})
            .get(tag, {})
        )
        result.update(target_defaults)
        if parent:
            for key in INHERITED_PROPERTIES:
                if key in parent:
                    result[key] = parent[key]
        palette = _deep_merge(
            dict(theme.get("palette", {})),
            target_theme.get("palette", {}) if isinstance(target_theme, Mapping) else {},
        )
        matching: list[tuple[tuple[int, int, int, int, int], _Rule]] = []
        for rule in self.rules:
            if rule.modes and selected_mode not in rule.modes:
                continue
            if rule.targets and selected_target not in rule.targets:
                continue
            if _selector_matches(rule.selector, element):
                specificity = selector_specificity(rule.selector)
                # !important is evaluated before specificity; later source
                # order wins when importance and specificity are equal.
                priority = (int(rule.important), *specificity, rule.order)
                matching.append((priority, rule))
        for _priority, rule in sorted(matching, key=lambda item: item[0]):
            result.update(_resolve_variables(rule.properties, palette))
        if inline:
            result.update(inline)
        return result


def _element_from_selector(selector: str) -> StyleElement:
    tag, element_id, classes, attrs = _split_compound(selector)
    return StyleElement.create(tag or "*", classes=classes, element_id=element_id,
                               attributes={key: value for key, _op, value in attrs})


def _style_directory_candidates() -> list[Path]:
    """Return likely locations for repository-level or installed style assets."""
    configured = os.getenv("ETOE_STYLE_DIR")
    if configured:
        return [Path(configured).expanduser().resolve()]
    module_path = Path(__file__).resolve()
    candidates = [
        module_path.parents[2] / "style",  # source checkout: project_root/style
        module_path.parents[1] / "style",  # custom --target installs
        Path(sys.prefix) / "style",       # wheel-installed data files
        Path(sysconfig.get_path("data")) / "style",
        Path.cwd() / "style",
    ]
    result: list[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved not in result:
            result.append(resolved)
    return result


def get_style_directory() -> Path:
    """Locate the global ``style/`` asset directory.

    Set ``ETOE_STYLE_DIR`` to use a project-specific style directory. In a
    source checkout assets are read from the repository root; installed wheels
    install them under ``sys.prefix/style``.
    """
    candidates = _style_directory_candidates()
    for path in candidates:
        if (path / "shared" / "tokens.toml").is_file():
            return path
    tried = ", ".join(str(path) for path in candidates)
    raise StyleError(
        "Cannot locate global style assets (expected shared/tokens.toml). "
        f"Checked: {tried}. Set ETOE_STYLE_DIR to the style directory."
    )


def _deep_merge(base: dict[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Merge mappings recursively, replacing scalar/list values in overlay order."""
    for key, value in overlay.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), Mapping):
            base[key] = _deep_merge(dict(base[key]), value)
        elif isinstance(value, Mapping):
            base[key] = _deep_merge({}, value)
        elif isinstance(value, list):
            base[key] = list(value)
        else:
            base[key] = value
    return base


def _invalidate_stylesheet_cache() -> None:
    """Discard compiled stylesheets so edited TOML resources are re-read.

    The incremental visualization writer calls this before regenerating an
    artifact after a dependency change.
    """
    _load_stylesheet_for_source.cache_clear()


@lru_cache(maxsize=None)
def _load_stylesheet_for_source(canonical_source: str) -> StyleSheet:
    """Compile the source base stylesheet and its target-specific overlays."""
    style_root = get_style_directory()
    source_dir_name = canonical_source.casefold().replace(" ", "")
    source_dir = style_root / source_dir_name
    base_path = source_dir / "stylesheet.toml"
    tokens_path = style_root / "shared" / "tokens.toml"
    if not base_path.is_file():
        raise StyleError(
            f"Source stylesheet {str(base_path)!r} is missing; every source needs "
            "a stylesheet.toml file."
        )
    if not tokens_path.is_file():
        raise StyleError(f"Shared style tokens file {str(tokens_path)!r} is missing.")

    try:
        data = tomllib.loads(base_path.read_text(encoding="utf-8"))
        shared_tokens = tomllib.loads(tokens_path.read_text(encoding="utf-8"))
        # Apply every target overlay at compile time. Each overlay's target key
        # remains explicit, so StyleSheet.resolve still chooses by Target.
        for overlay_path in sorted(source_dir.glob("*.toml")):
            if overlay_path.name == "stylesheet.toml":
                continue
            try:
                overlay_target = normalize_target(overlay_path.stem)
            except StyleError as exc:
                raise StyleError(
                    f"Unexpected TOML file {str(overlay_path)!r}; target overlays "
                    "must be named after a target environment."
                ) from exc
            overlay = tomllib.loads(overlay_path.read_text(encoding="utf-8"))
            # A target overlay can use ordinary [themes.Light.node] tables;
            # those are stored separately and only applied for this filename's
            # target. Explicit target_overrides remain supported as well.
            if "themes" in overlay:
                target_themes = data.setdefault("target_themes", {}).setdefault(overlay_target, {})
                _deep_merge(target_themes, overlay["themes"])
            _deep_merge(data, {
                k: v for k, v in overlay.items()
                if k not in {"description", "schema_version", "rules", "themes"}
            })
            for row in overlay.get("rules", ()):
                target_row = dict(row)
                targets = list(target_row.get("targets", ()))
                if not targets:
                    targets = [overlay_target]
                elif overlay_target not in [normalize_target(item) for item in targets]:
                    targets.append(overlay_target)
                target_row["targets"] = targets
                data.setdefault("rules", []).append(target_row)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise StyleError(f"Unable to read style resources for source {canonical_source!r}: {exc}") from exc

    # Merge shared semantic category tokens into the palette for all modes.
    for selected_mode in MODES:
        theme = dict(data.get("themes", {}).get(selected_mode, {}))
        local_palette = dict(theme.get("palette", {}))
        shared_palette = shared_tokens.get("themes", {}).get(selected_mode, {}).get("palette", {})
        theme["palette"] = _deep_merge(dict(shared_palette), local_palette)
        data.setdefault("themes", {})[selected_mode] = theme
    return StyleSheet(canonical_source.casefold(), data)


def load_stylesheet(name: str | None = None, *, source: str | None = None) -> StyleSheet:
    """Load the base stylesheet for a source environment plus its target overlays.

    ``name`` remains as a backwards-compatible positional alias for ``source``.
    When both are omitted, the global ``Source`` setting (or ETOE_STYLE_SOURCE)
    chooses the source environment.
    """
    settings = get_style_settings()
    selected_source = source if source is not None else name
    canonical_source = normalize_source(selected_source, default=settings.source)
    return _load_stylesheet_for_source(canonical_source)


def resolve_style(
    stylesheet: str | None = None,
    selector: str = "*",
    *,
    classes: Sequence[str] = (),
    attributes: Mapping[str, Any] | None = None,
    element_id: str | None = None,
    ancestors: Sequence[StyleElement] = (),
    mode: str | None = None,
    target: str | None = None,
    source: str | None = None,
    parent: Mapping[str, Any] | None = None,
    inline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a selector in a source environment using the shared cascade."""
    parsed = _element_from_selector(selector)
    element = StyleElement.create(
        parsed.tag,
        classes=set(parsed.classes) | set(classes),
        attributes={**dict(parsed.attributes), **dict(attributes or {})},
        element_id=element_id or parsed.element_id,
        ancestors=ancestors,
    )
    selected_source = source if source is not None else stylesheet
    return load_stylesheet(selected_source).resolve(
        element, mode=mode, target=target, parent=parent, inline=inline,
    )


def chemical_category_slug(symbol: str | None, element_catalog: Any | None = None) -> str:
    """Return an element's declared category, falling back to the built-in map.

    ``element_catalog`` is optional to preserve the original public API. When
    supplied, the category slug in the element's TOML metadata takes priority
    over the package's default periodic-table classification. This also works
    before a :class:`ChemicalCategoryCatalog` has linked runtime category objects.
    """
    if not symbol:
        return "unknowns"

    if element_catalog is not None:
        element = element_catalog.get(symbol)
        declared_slug = getattr(element, "declared_chemical_category", None)
        if declared_slug:
            return declared_slug

    try:
        # Lazy import avoids a module cycle: selections builds on the semantic
        # translator, while Graphviz calls this only after module initialization.
        from .selections import _CATEGORY_BY_SYMBOL
        return _CATEGORY_BY_SYMBOL.get(symbol, "unknowns")
    except ImportError:
        return "unknowns"
