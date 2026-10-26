from pathlib import Path

import pytest

from etoe import (
    HyperatomTranslator,
    StyleElement,
    StyleSheet,
    configure_styles,
    get_style_directory,
    get_style_settings,
    hyperatom_map_to_dot,
    hyperatom_tree_to_dot,
    load_stylesheet,
    periodic_map_to_dot,
    normalize_source,
    reset_styles,
    resolve_style,
    selector_specificity,
)


DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "atom" / "element"


@pytest.fixture(scope="module")
def registry():
    return HyperatomTranslator().translate_directory(DATA_ROOT)


@pytest.fixture(autouse=True)
def restore_global_styles():
    previous = get_style_settings()
    yield
    configure_styles(mode=previous.mode, target=previous.target, source=previous.source)


def test_every_bundled_stylesheet_has_light_and_dark_modes():
    for name in ("graphviz", "3d", "latex", "manim", "books", "articles", "web"):
        sheet = load_stylesheet(name)
        assert "Light" in sheet.data["themes"]
        assert "Dark" in sheet.data["themes"]


def test_semantic_palette_is_shared_across_renderers():
    graphviz = load_stylesheet("graphviz")
    web = load_stylesheet("web")
    assert graphviz.data["themes"]["Light"]["palette"] == web.data["themes"]["Light"]["palette"]
    assert graphviz.data["themes"]["Dark"]["palette"] == web.data["themes"]["Dark"]["palette"]


def test_selector_specificity_uses_css_tuple_order():
    assert selector_specificity("node#critical.category-halogen") == (1, 1, 1)
    assert selector_specificity("node.category-halogen") == (0, 1, 1)
    assert selector_specificity("*") == (0, 0, 0)


def test_cascade_specificity_precedes_source_order_and_inline_is_last():
    sheet = StyleSheet("test", {
        "themes": {
            "Light": {
                "node": {"fontname": "Default", "fontcolor": "#111111", "shape": "ellipse"},
                "palette": {},
            },
            "Dark": {
                "node": {"fontname": "Default Dark", "fontcolor": "#eeeeee", "shape": "ellipse"},
                "palette": {},
            },
        },
        "rules": [
            {"selector": "node#critical", "properties": {"fillcolor": "red"}},
            {"selector": "node.hyperatom", "properties": {"fillcolor": "blue"}},
            {"selector": "node.hyperatom", "properties": {"penwidth": 2}},
        ],
    })
    element = StyleElement.create("node", classes={"hyperatom"}, element_id="critical")
    resolved = sheet.resolve(element)
    assert resolved["fillcolor"] == "red"  # ID specificity beats a later class selector.
    assert resolved["penwidth"] == 2       # Later source order wins equal specificity.
    assert resolved["shape"] == "ellipse"
    resolved_inline = sheet.resolve(element, inline={"fillcolor": "green"})
    assert resolved_inline["fillcolor"] == "green"


def test_descendant_and_direct_child_selectors_match_the_tree_context():
    sheet = StyleSheet("test", {
        "themes": {"Light": {"node": {}, "palette": {}}, "Dark": {"node": {}, "palette": {}}},
        "rules": [
            {"selector": ".panel .special", "properties": {"background": "descendant"}},
            {"selector": ".panel > node.special", "properties": {"background": "direct"}},
        ],
    })
    panel = StyleElement.create("container", classes={"panel"})
    nested = StyleElement.create("node", classes={"special"}, ancestors=(panel,))
    assert sheet.resolve(nested)["background"] == "direct"

    inner = StyleElement.create("container", classes={"inner"})
    deep = StyleElement.create("node", classes={"special"}, ancestors=(panel, inner))
    assert sheet.resolve(deep)["background"] == "descendant"


def test_inheritable_properties_flow_from_parent_to_child():
    sheet = StyleSheet("test", {
        "themes": {
            "Light": {"node": {"fontname": "Default", "fontcolor": "#111111", "fillcolor": "white"}, "palette": {}},
            "Dark": {"node": {"fontname": "Default Dark", "fontcolor": "#eeeeee", "fillcolor": "black"}, "palette": {}},
        },
        "rules": [],
    })
    resolved = sheet.resolve(
        StyleElement.create("node", classes={"child"}),
        parent={"fontname": "Parent Font", "fontcolor": "#abcdef", "fillcolor": "red"},
    )
    assert resolved["fontname"] == "Parent Font"
    assert resolved["fontcolor"] == "#abcdef"
    assert resolved["fillcolor"] == "white"  # Fill is not in the inherited-property set.


def test_global_mode_and_target_are_normalized_and_can_be_overridden():
    settings = configure_styles(Mode="dark", Target="LaTeX")
    assert settings.mode == "Dark"
    assert settings.target == "LaTeX"
    assert get_style_settings() == settings
    assert reset_styles().mode in {"Light", "Dark"}


def test_target_overlay_selects_graphviz_typography():
    web_style = resolve_style("graphviz", "node", classes=["hyperatom"], target="Web")
    latex_style = resolve_style("graphviz", "node", classes=["hyperatom"], target="LaTeX")
    assert web_style["fontname"] == "Inter"
    assert latex_style["fontname"] == "CMU Serif"
    assert web_style["margin"] == "0.12,0.08"
    assert latex_style["margin"] == "0.10,0.06"


def test_periodic_hydrogen_is_round_and_purple_in_both_modes(registry):
    light = periodic_map_to_dot(registry, symbols=["H"], mode="Light")
    dark = periodic_map_to_dot(registry, symbols=["H"], mode="Dark")
    light_h = next(line for line in light.splitlines() if 'label="H"' in line)
    dark_h = next(line for line in dark.splitlines() if 'label="H"' in line)
    assert 'shape="circle"' in light_h
    assert 'fillcolor="#F3E8FF"' in light_h
    assert 'shape="circle"' in dark_h
    assert 'fillcolor="#4C1D95"' in dark_h
    assert 'bgcolor="#111827"' in dark


def test_hyperatom_map_hydrogen_is_round_and_purple(registry):
    dot = hyperatom_map_to_dot(registry, symbols=["H"])
    h = next(line for line in dot.splitlines() if 'label="H-1-1"' in line)
    assert 'shape="circle"' in h
    assert 'fillcolor="#F3E8FF"' in h
    assert 'fixedsize=true' in h


def test_tree_hydrogen_roles_follow_subatom_position_and_mode(registry):
    light = hyperatom_tree_to_dot(registry, "He-5-(4'1)", mode="Light")
    dark = hyperatom_tree_to_dot(registry, "He-5-(4'1)", mode="Dark")
    light_h = [line for line in light.splitlines() if 'label="H-1-1"' in line]
    dark_h = [line for line in dark.splitlines() if 'label="H-1-1"' in line]
    assert len(light_h) == len(dark_h) == 5
    assert all('shape="circle"' in line for line in light_h + dark_h)
    assert sum('fillcolor="#DBEAFE"' in line for line in light_h) == 2
    assert sum('fillcolor="#FEE2E2"' in line for line in light_h) == 3
    assert sum('fillcolor="#1E3A8A"' in line for line in dark_h) == 2
    assert sum('fillcolor="#7F1D1D"' in line for line in dark_h) == 3


def test_root_protium_in_a_tree_uses_single_protium_colour(registry):
    dot = hyperatom_tree_to_dot(registry, "H-1-1")
    h = next(line for line in dot.splitlines() if 'label="H-1-1"' in line)
    assert 'shape="circle"' in h
    assert 'fillcolor="#F3E8FF"' in h


def test_hyperatom_fill_uses_chemical_category_palette(registry):
    dot = hyperatom_map_to_dot(registry, symbols=["He"])
    helium = next(line for line in dot.splitlines() if "label=\"He:1-4-(2'2)\"" in line)
    assert 'fillcolor="#F3E8FF"' in helium  # noble gases; an explicit visual convention
    dark = hyperatom_map_to_dot(registry, symbols=["He"], mode="Dark")
    helium_dark = next(line for line in dark.splitlines() if "label=\"He:1-4-(2'2)\"" in line)
    assert 'fillcolor="#3B1C58"' in helium_dark


def test_dot_output_can_target_latex_without_changing_graph_semantics(registry):
    dot = periodic_map_to_dot(registry, symbols=["He"], mode="Light", target="LaTeX")
    assert 'fontname="CMU Serif"' in dot
    assert "digraph periodic_map" in dot
    assert "shape=" in dot


def test_style_assets_live_in_the_project_level_directory():
    style_root = get_style_directory()
    assert style_root.name == "style"
    assert (style_root / "shared" / "tokens.toml").is_file()
    assert (style_root / "graphviz" / "stylesheet.toml").is_file()
    assert (style_root / "graphviz" / "latex.toml").is_file()
    assert (style_root / "latex" / "book.tex").is_file()
    assert (style_root / "latex" / "article.tex").is_file()


def test_global_source_setting_and_source_environment_default():
    settings = configure_styles(Mode="Dark", Source="LaTeX", Target="Web")
    assert settings.mode == "Dark"
    assert settings.source == "LaTeX"
    assert settings.target == "Web"
    assert normalize_source("tex") == "LaTeX"
    # No explicit sheet selects the profile designated by global Source.
    assert load_stylesheet().name == "latex"
    assert "page" in load_stylesheet().data["themes"]["Dark"]


def test_graphviz_latex_overlay_is_separate_and_cascades_with_base():
    style_root = get_style_directory()
    overlay_text = (style_root / "graphviz" / "latex.toml").read_text(encoding="utf-8")
    assert "[target_overrides.LaTeX.node]" in overlay_text
    sheet = load_stylesheet("graphviz")
    web = sheet.resolve(StyleElement.create("node"), target="Web")
    latex = sheet.resolve(StyleElement.create("node"), target="LaTeX")
    assert web["fontname"] == "Inter"
    assert latex["fontname"] == "CMU Serif"
    # Source defaults and semantic rules remain inherited from the base sheet.
    helium = resolve_style("graphviz", "node", classes=["hyperatom", "category-noble-gases"], target="LaTeX")
    assert helium["shape"] == "box"
    assert helium["fillcolor"] == "#F3E8FF"


def test_source_names_are_canonicalized():
    settings = configure_styles(source="dot")
    assert settings.source == "GraphViz"
    settings = configure_styles(source="html")
    assert settings.source == "Web"


def test_target_theme_tables_are_scoped_to_overlay_target():
    sheet = StyleSheet("graphviz", {
        "themes": {
            "Light": {"node": {"fontname": "Inter"}, "palette": {}},
            "Dark": {"node": {"fontname": "Inter"}, "palette": {}},
        },
        "target_themes": {
            "LaTeX": {
                "Light": {"node": {"fontname": "CMU Serif"}},
                "Dark": {"node": {"fontname": "CMU Serif"}},
            },
        },
        "rules": [],
    })
    assert sheet.resolve("node", target="LaTeX")["fontname"] == "CMU Serif"
    assert sheet.resolve("node", target="Web")["fontname"] == "Inter"
