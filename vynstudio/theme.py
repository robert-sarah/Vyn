"""VynStudio IDE Themes — Dark, Light, High Contrast, Dracula, Solarized."""
from __future__ import annotations
from typing import Dict, Any


# ─── Type alias ──────────────────────────────────────────────────────────────

Theme = Dict[str, str]


# ═══════════════════════════════════════════════════════════════════════════════
#  VS Code Light  (default)
# ═══════════════════════════════════════════════════════════════════════════════

LIGHT: Theme = {
    "name":              "VS Code Light",
    "bg":                "#FFFFFF",
    "sidebar":           "#F3F3F3",
    "activity":          "#2C2C2C",
    "border":            "#E5E5E5",
    "accent":            "#007ACC",
    "accent_hover":      "#005A9E",
    "accent_fg":         "#FFFFFF",
    "tab_active":        "#FFFFFF",
    "tab_inactive":      "#ECECEC",
    "tab_text":          "#333333",
    "tab_text_muted":    "#616161",
    "text":              "#333333",
    "text_secondary":    "#6E6E6E",
    "muted":             "#6E6E6E",
    "editor_bg":         "#FFFFFF",
    "editor_text":       "#000000",
    "editor_selection":  "#ADD6FF",
    "editor_cursor":     "#000000",
    "editor_line_hl":    "#F5F5F5",
    "line_number":       "#237893",
    "line_number_bg":    "#FFFFFF",
    "line_number_active":"#0B216F",
    "current_line":      "#F5F5F5",
    "selection":         "#ADD6FF",
    "match_highlight":   "#A8AC94",
    "breadcrumb":        "#F3F3F3",
    "breadcrumb_text":   "#6E6E6E",
    "panel_bg":          "#F3F3F3",
    "panel_border":      "#E5E5E5",
    "statusbar":         "#007ACC",
    "statusbar_text":    "#FFFFFF",
    "statusbar_item_hover": "#005A9E",
    "tree_selected":     "#0060C0",
    "tree_selected_fg":  "#FFFFFF",
    "tree_hover":        "#E8E8E8",
    "tree_text":         "#333333",
    "scrollbar":         "#C5C5C5",
    "scrollbar_hover":   "#A8A8A8",
    "input_bg":          "#FFFFFF",
    "input_border":      "#BEBEBE",
    "input_text":        "#333333",
    "input_placeholder": "#AAAAAA",
    "button_bg":         "#007ACC",
    "button_text":       "#FFFFFF",
    "button_hover":      "#005A9E",
    "button_secondary":  "#E7E7E7",
    "button_secondary_text": "#333333",
    "dropdown_bg":       "#FFFFFF",
    "dropdown_border":   "#BEBEBE",
    "dropdown_text":     "#333333",
    "popup_bg":          "#FFFFFF",
    "popup_border":      "#C8C8C8",
    "popup_shadow":      "rgba(0,0,0,0.2)",
    "popup_selected":    "#0060C0",
    "popup_selected_fg": "#FFFFFF",
    "popup_hover":       "#E8E8E8",
    "completion_bg":     "#F8F8F8",
    "completion_border": "#C8C8C8",
    "completion_text":   "#333333",
    "completion_match":  "#0066BF",
    "completion_detail": "#6E6E6E",
    "error":             "#E51400",
    "error_bg":          "#FFF0F0",
    "warning":           "#BF8803",
    "warning_bg":        "#FFFBF0",
    "info":              "#007ACC",
    "info_bg":           "#F0F8FF",
    "hint":              "#6E6E6E",
    "success":           "#16825D",
    "success_bg":        "#F0FFF4",
    "minimap_bg":        "#F3F3F3",
    "minimap_slider":    "#99999933",
    "indent_guide":      "#D3D3D3",
    "indent_guide_active":"#939393",
    "bracket_match":     "#0064001A",
    "bracket_match_border":"#006400",
    "find_bg":           "#FFFFFF",
    "find_border":       "#007ACC",
    "find_match":        "#FFFF00",
    "find_match_border": "#FF8000",
    "terminal_bg":       "#FFFFFF",
    "terminal_text":     "#333333",
    "terminal_cursor":   "#000000",
    "terminal_selection":"#ADD6FF",
    "gutter_add":        "#2EA043",
    "gutter_change":     "#D29922",
    "gutter_delete":     "#F85149",
    # Syntax highlighting
    "syn_keyword":       "#0000FF",
    "syn_type":          "#267F99",
    "syn_string":        "#A31515",
    "syn_number":        "#098658",
    "syn_comment":       "#008000",
    "syn_comment_doc":   "#005000",
    "syn_ident":         "#001080",
    "syn_struct":        "#267F99",
    "syn_enum":          "#267F99",
    "syn_fn":            "#795E26",
    "syn_macro":         "#AF00DB",
    "syn_attribute":     "#4EC9B0",
    "syn_hot":           "#E51400",
    "syn_operator":      "#000000",
    "syn_punctuation":   "#000000",
    "syn_lifetime":      "#AF00DB",
    "syn_self":          "#0000FF",
    "syn_constant":      "#0070C1",
    "syn_variable":      "#001080",
    "syn_parameter":     "#001080",
    "syn_property":      "#001080",
    "syn_label":         "#717171",
    "syn_escape":        "#EE0000",
    "syn_format":        "#0000FF",
    "syn_bool":          "#0000FF",
    "syn_none":          "#0000FF",
    "syn_regex":         "#811F3F",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  VS Code Dark  (Dark+)
# ═══════════════════════════════════════════════════════════════════════════════

DARK: Theme = {
    "name":              "VS Code Dark",
    "bg":                "#1E1E1E",
    "sidebar":           "#252526",
    "activity":          "#333333",
    "border":            "#474747",
    "accent":            "#007ACC",
    "accent_hover":      "#1A8AD4",
    "accent_fg":         "#FFFFFF",
    "tab_active":        "#1E1E1E",
    "tab_inactive":      "#2D2D2D",
    "tab_text":          "#FFFFFF",
    "tab_text_muted":    "#969696",
    "text":              "#CCCCCC",
    "text_secondary":    "#969696",
    "muted":             "#969696",
    "editor_bg":         "#1E1E1E",
    "editor_text":       "#D4D4D4",
    "editor_selection":  "#264F78",
    "editor_cursor":     "#AEAFAD",
    "editor_line_hl":    "#2A2D2E",
    "line_number":       "#858585",
    "line_number_bg":    "#1E1E1E",
    "line_number_active":"#C6C6C6",
    "current_line":      "#2A2D2E",
    "selection":         "#264F78",
    "match_highlight":   "#515C6A",
    "breadcrumb":        "#1E1E1E",
    "breadcrumb_text":   "#CCCCCC",
    "panel_bg":          "#1E1E1E",
    "panel_border":      "#474747",
    "statusbar":         "#007ACC",
    "statusbar_text":    "#FFFFFF",
    "statusbar_item_hover": "#1A8AD4",
    "tree_selected":     "#094771",
    "tree_selected_fg":  "#FFFFFF",
    "tree_hover":        "#2A2D2E",
    "tree_text":         "#CCCCCC",
    "scrollbar":         "#424242",
    "scrollbar_hover":   "#686868",
    "input_bg":          "#3C3C3C",
    "input_border":      "#555555",
    "input_text":        "#CCCCCC",
    "input_placeholder": "#777777",
    "button_bg":         "#0E639C",
    "button_text":       "#FFFFFF",
    "button_hover":      "#1177BB",
    "button_secondary":  "#3A3D41",
    "button_secondary_text": "#CCCCCC",
    "dropdown_bg":       "#3C3C3C",
    "dropdown_border":   "#555555",
    "dropdown_text":     "#CCCCCC",
    "popup_bg":          "#252526",
    "popup_border":      "#454545",
    "popup_shadow":      "rgba(0,0,0,0.5)",
    "popup_selected":    "#094771",
    "popup_selected_fg": "#FFFFFF",
    "popup_hover":       "#2A2D2E",
    "completion_bg":     "#252526",
    "completion_border": "#454545",
    "completion_text":   "#CCCCCC",
    "completion_match":  "#18A3FF",
    "completion_detail": "#969696",
    "error":             "#F14C4C",
    "error_bg":          "#3D1A1A",
    "warning":           "#CCA700",
    "warning_bg":        "#3D3200",
    "info":              "#3794FF",
    "info_bg":           "#1A2D3D",
    "hint":              "#969696",
    "success":           "#89D185",
    "success_bg":        "#1A3D1A",
    "minimap_bg":        "#252526",
    "minimap_slider":    "#79797966",
    "indent_guide":      "#404040",
    "indent_guide_active":"#707070",
    "bracket_match":     "#0064001A",
    "bracket_match_border":"#888888",
    "find_bg":           "#252526",
    "find_border":       "#007ACC",
    "find_match":        "#515C6A",
    "find_match_border": "#EA5C00",
    "terminal_bg":       "#1E1E1E",
    "terminal_text":     "#CCCCCC",
    "terminal_cursor":   "#AEAFAD",
    "terminal_selection":"#264F78",
    "gutter_add":        "#2EA043",
    "gutter_change":     "#D29922",
    "gutter_delete":     "#F85149",
    # Syntax highlighting
    "syn_keyword":       "#C586C0",
    "syn_type":          "#4EC9B0",
    "syn_string":        "#CE9178",
    "syn_number":        "#B5CEA8",
    "syn_comment":       "#6A9955",
    "syn_comment_doc":   "#608B4E",
    "syn_ident":         "#9CDCFE",
    "syn_struct":        "#4EC9B0",
    "syn_enum":          "#4EC9B0",
    "syn_fn":            "#DCDCAA",
    "syn_macro":         "#C586C0",
    "syn_attribute":     "#4FC1FF",
    "syn_hot":           "#FF6B35",
    "syn_operator":      "#D4D4D4",
    "syn_punctuation":   "#D4D4D4",
    "syn_lifetime":      "#C586C0",
    "syn_self":          "#569CD6",
    "syn_constant":      "#4FC1FF",
    "syn_variable":      "#9CDCFE",
    "syn_parameter":     "#9CDCFE",
    "syn_property":      "#9CDCFE",
    "syn_label":         "#C8C8C8",
    "syn_escape":        "#D7BA7D",
    "syn_format":        "#569CD6",
    "syn_bool":          "#569CD6",
    "syn_none":          "#569CD6",
    "syn_regex":         "#D16969",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  High Contrast  (accessibility)
# ═══════════════════════════════════════════════════════════════════════════════

HIGH_CONTRAST: Theme = {
    "name":              "High Contrast",
    "bg":                "#000000",
    "sidebar":           "#000000",
    "activity":          "#000000",
    "border":            "#6FC3DF",
    "accent":            "#3794FF",
    "accent_hover":      "#1AABFF",
    "accent_fg":         "#000000",
    "tab_active":        "#000000",
    "tab_inactive":      "#000000",
    "tab_text":          "#FFFFFF",
    "tab_text_muted":    "#AAAAAA",
    "text":              "#FFFFFF",
    "text_secondary":    "#CCCCCC",
    "muted":             "#AAAAAA",
    "editor_bg":         "#000000",
    "editor_text":       "#FFFFFF",
    "editor_selection":  "#0078D4",
    "editor_cursor":     "#FFFFFF",
    "editor_line_hl":    "#0A0A0A",
    "line_number":       "#7CA668",
    "line_number_bg":    "#000000",
    "line_number_active":"#FFFFFF",
    "current_line":      "#0A0A0A",
    "selection":         "#0078D4",
    "match_highlight":   "#4B5320",
    "breadcrumb":        "#000000",
    "breadcrumb_text":   "#FFFFFF",
    "panel_bg":          "#000000",
    "panel_border":      "#6FC3DF",
    "statusbar":         "#0078D4",
    "statusbar_text":    "#FFFFFF",
    "statusbar_item_hover": "#1A8AD4",
    "tree_selected":     "#0078D4",
    "tree_selected_fg":  "#FFFFFF",
    "tree_hover":        "#111111",
    "tree_text":         "#FFFFFF",
    "scrollbar":         "#6FC3DF",
    "scrollbar_hover":   "#3794FF",
    "input_bg":          "#000000",
    "input_border":      "#6FC3DF",
    "input_text":        "#FFFFFF",
    "input_placeholder": "#888888",
    "button_bg":         "#0078D4",
    "button_text":       "#FFFFFF",
    "button_hover":      "#1A8AD4",
    "button_secondary":  "#000000",
    "button_secondary_text": "#FFFFFF",
    "dropdown_bg":       "#000000",
    "dropdown_border":   "#6FC3DF",
    "dropdown_text":     "#FFFFFF",
    "popup_bg":          "#000000",
    "popup_border":      "#6FC3DF",
    "popup_shadow":      "rgba(255,255,255,0.1)",
    "popup_selected":    "#0078D4",
    "popup_selected_fg": "#FFFFFF",
    "popup_hover":       "#111111",
    "completion_bg":     "#000000",
    "completion_border": "#6FC3DF",
    "completion_text":   "#FFFFFF",
    "completion_match":  "#18A3FF",
    "completion_detail": "#AAAAAA",
    "error":             "#FF0000",
    "error_bg":          "#200000",
    "warning":           "#FFFF00",
    "warning_bg":        "#202000",
    "info":              "#3794FF",
    "info_bg":           "#001A3D",
    "hint":              "#AAAAAA",
    "success":           "#00FF00",
    "success_bg":        "#002000",
    "minimap_bg":        "#000000",
    "minimap_slider":    "#6FC3DF33",
    "indent_guide":      "#6FC3DF44",
    "indent_guide_active":"#6FC3DF",
    "bracket_match":     "#FFFFFF33",
    "bracket_match_border":"#FFFFFF",
    "find_bg":           "#000000",
    "find_border":       "#3794FF",
    "find_match":        "#4B5320",
    "find_match_border": "#FFFF00",
    "terminal_bg":       "#000000",
    "terminal_text":     "#FFFFFF",
    "terminal_cursor":   "#FFFFFF",
    "terminal_selection":"#0078D4",
    "gutter_add":        "#00FF00",
    "gutter_change":     "#FFFF00",
    "gutter_delete":     "#FF0000",
    # Syntax highlighting
    "syn_keyword":       "#FF79C6",
    "syn_type":          "#8BE9FD",
    "syn_string":        "#F1FA8C",
    "syn_number":        "#BD93F9",
    "syn_comment":       "#6272A4",
    "syn_comment_doc":   "#7282B4",
    "syn_ident":         "#FFFFFF",
    "syn_struct":        "#8BE9FD",
    "syn_enum":          "#8BE9FD",
    "syn_fn":            "#50FA7B",
    "syn_macro":         "#FF79C6",
    "syn_attribute":     "#8BE9FD",
    "syn_hot":           "#FF5555",
    "syn_operator":      "#FFFFFF",
    "syn_punctuation":   "#FFFFFF",
    "syn_lifetime":      "#FF79C6",
    "syn_self":          "#8BE9FD",
    "syn_constant":      "#BD93F9",
    "syn_variable":      "#FFFFFF",
    "syn_parameter":     "#FFB86C",
    "syn_property":      "#FFFFFF",
    "syn_label":         "#AAAAAA",
    "syn_escape":        "#FF79C6",
    "syn_format":        "#8BE9FD",
    "syn_bool":          "#BD93F9",
    "syn_none":          "#BD93F9",
    "syn_regex":         "#F1FA8C",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Dracula
# ═══════════════════════════════════════════════════════════════════════════════

DRACULA: Theme = {
    "name":              "Dracula",
    "bg":                "#282A36",
    "sidebar":           "#21222C",
    "activity":          "#191A21",
    "border":            "#44475A",
    "accent":            "#BD93F9",
    "accent_hover":      "#A075F7",
    "accent_fg":         "#282A36",
    "tab_active":        "#282A36",
    "tab_inactive":      "#21222C",
    "tab_text":          "#F8F8F2",
    "tab_text_muted":    "#6272A4",
    "text":              "#F8F8F2",
    "text_secondary":    "#6272A4",
    "muted":             "#6272A4",
    "editor_bg":         "#282A36",
    "editor_text":       "#F8F8F2",
    "editor_selection":  "#44475A",
    "editor_cursor":     "#F8F8F2",
    "editor_line_hl":    "#44475A44",
    "line_number":       "#6272A4",
    "line_number_bg":    "#282A36",
    "line_number_active":"#F8F8F2",
    "current_line":      "#44475A44",
    "selection":         "#44475A",
    "match_highlight":   "#FFB86C44",
    "breadcrumb":        "#21222C",
    "breadcrumb_text":   "#6272A4",
    "panel_bg":          "#21222C",
    "panel_border":      "#44475A",
    "statusbar":         "#191A21",
    "statusbar_text":    "#F8F8F2",
    "statusbar_item_hover": "#44475A",
    "tree_selected":     "#44475A",
    "tree_selected_fg":  "#F8F8F2",
    "tree_hover":        "#44475A88",
    "tree_text":         "#F8F8F2",
    "scrollbar":         "#44475A",
    "scrollbar_hover":   "#6272A4",
    "input_bg":          "#21222C",
    "input_border":      "#44475A",
    "input_text":        "#F8F8F2",
    "input_placeholder": "#6272A4",
    "button_bg":         "#BD93F9",
    "button_text":       "#282A36",
    "button_hover":      "#A075F7",
    "button_secondary":  "#44475A",
    "button_secondary_text": "#F8F8F2",
    "dropdown_bg":       "#21222C",
    "dropdown_border":   "#44475A",
    "dropdown_text":     "#F8F8F2",
    "popup_bg":          "#21222C",
    "popup_border":      "#44475A",
    "popup_shadow":      "rgba(0,0,0,0.5)",
    "popup_selected":    "#44475A",
    "popup_selected_fg": "#F8F8F2",
    "popup_hover":       "#44475A88",
    "completion_bg":     "#21222C",
    "completion_border": "#44475A",
    "completion_text":   "#F8F8F2",
    "completion_match":  "#BD93F9",
    "completion_detail": "#6272A4",
    "error":             "#FF5555",
    "error_bg":          "#3D1A1A",
    "warning":           "#FFB86C",
    "warning_bg":        "#3D2A00",
    "info":              "#8BE9FD",
    "info_bg":           "#1A2D3D",
    "hint":              "#6272A4",
    "success":           "#50FA7B",
    "success_bg":        "#1A3D1A",
    "minimap_bg":        "#21222C",
    "minimap_slider":    "#44475A66",
    "indent_guide":      "#44475A",
    "indent_guide_active":"#6272A4",
    "bracket_match":     "#44475A88",
    "bracket_match_border":"#BD93F9",
    "find_bg":           "#21222C",
    "find_border":       "#BD93F9",
    "find_match":        "#FFB86C44",
    "find_match_border": "#FFB86C",
    "terminal_bg":       "#282A36",
    "terminal_text":     "#F8F8F2",
    "terminal_cursor":   "#F8F8F2",
    "terminal_selection":"#44475A",
    "gutter_add":        "#50FA7B",
    "gutter_change":     "#FFB86C",
    "gutter_delete":     "#FF5555",
    # Syntax highlighting
    "syn_keyword":       "#FF79C6",
    "syn_type":          "#8BE9FD",
    "syn_string":        "#F1FA8C",
    "syn_number":        "#BD93F9",
    "syn_comment":       "#6272A4",
    "syn_comment_doc":   "#7282B4",
    "syn_ident":         "#F8F8F2",
    "syn_struct":        "#8BE9FD",
    "syn_enum":          "#8BE9FD",
    "syn_fn":            "#50FA7B",
    "syn_macro":         "#FF79C6",
    "syn_attribute":     "#8BE9FD",
    "syn_hot":           "#FF5555",
    "syn_operator":      "#FF79C6",
    "syn_punctuation":   "#F8F8F2",
    "syn_lifetime":      "#FF79C6",
    "syn_self":          "#8BE9FD",
    "syn_constant":      "#BD93F9",
    "syn_variable":      "#F8F8F2",
    "syn_parameter":     "#FFB86C",
    "syn_property":      "#F8F8F2",
    "syn_label":         "#6272A4",
    "syn_escape":        "#FF79C6",
    "syn_format":        "#8BE9FD",
    "syn_bool":          "#BD93F9",
    "syn_none":          "#BD93F9",
    "syn_regex":         "#F1FA8C",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Solarized Dark
# ═══════════════════════════════════════════════════════════════════════════════

SOLARIZED_DARK: Theme = {
    "name":              "Solarized Dark",
    "bg":                "#002B36",
    "sidebar":           "#073642",
    "activity":          "#002B36",
    "border":            "#073642",
    "accent":            "#268BD2",
    "accent_hover":      "#2196DD",
    "accent_fg":         "#FDF6E3",
    "tab_active":        "#002B36",
    "tab_inactive":      "#073642",
    "tab_text":          "#839496",
    "tab_text_muted":    "#657B83",
    "text":              "#839496",
    "text_secondary":    "#657B83",
    "muted":             "#586E75",
    "editor_bg":         "#002B36",
    "editor_text":       "#839496",
    "editor_selection":  "#073642",
    "editor_cursor":     "#839496",
    "editor_line_hl":    "#07364266",
    "line_number":       "#586E75",
    "line_number_bg":    "#002B36",
    "line_number_active":"#839496",
    "current_line":      "#07364266",
    "selection":         "#073642",
    "match_highlight":   "#B5890044",
    "breadcrumb":        "#073642",
    "breadcrumb_text":   "#839496",
    "panel_bg":          "#073642",
    "panel_border":      "#586E75",
    "statusbar":         "#073642",
    "statusbar_text":    "#839496",
    "statusbar_item_hover": "#002B36",
    "tree_selected":     "#073642",
    "tree_selected_fg":  "#FDF6E3",
    "tree_hover":        "#07364288",
    "tree_text":         "#839496",
    "scrollbar":         "#073642",
    "scrollbar_hover":   "#586E75",
    "input_bg":          "#073642",
    "input_border":      "#586E75",
    "input_text":        "#839496",
    "input_placeholder": "#586E75",
    "button_bg":         "#268BD2",
    "button_text":       "#FDF6E3",
    "button_hover":      "#2196DD",
    "button_secondary":  "#073642",
    "button_secondary_text": "#839496",
    "dropdown_bg":       "#073642",
    "dropdown_border":   "#586E75",
    "dropdown_text":     "#839496",
    "popup_bg":          "#073642",
    "popup_border":      "#586E75",
    "popup_shadow":      "rgba(0,0,0,0.5)",
    "popup_selected":    "#268BD2",
    "popup_selected_fg": "#FDF6E3",
    "popup_hover":       "#073642",
    "completion_bg":     "#073642",
    "completion_border": "#586E75",
    "completion_text":   "#839496",
    "completion_match":  "#268BD2",
    "completion_detail": "#586E75",
    "error":             "#DC322F",
    "error_bg":          "#200000",
    "warning":           "#B58900",
    "warning_bg":        "#202000",
    "info":              "#268BD2",
    "info_bg":           "#001A2D",
    "hint":              "#586E75",
    "success":           "#859900",
    "success_bg":        "#1A2000",
    "minimap_bg":        "#073642",
    "minimap_slider":    "#58687566",
    "indent_guide":      "#073642",
    "indent_guide_active":"#586E75",
    "bracket_match":     "#26ABD244",
    "bracket_match_border":"#268BD2",
    "find_bg":           "#073642",
    "find_border":       "#268BD2",
    "find_match":        "#B5890044",
    "find_match_border": "#B58900",
    "terminal_bg":       "#002B36",
    "terminal_text":     "#839496",
    "terminal_cursor":   "#839496",
    "terminal_selection":"#073642",
    "gutter_add":        "#859900",
    "gutter_change":     "#B58900",
    "gutter_delete":     "#DC322F",
    # Syntax highlighting
    "syn_keyword":       "#859900",
    "syn_type":          "#268BD2",
    "syn_string":        "#2AA198",
    "syn_number":        "#D33682",
    "syn_comment":       "#586E75",
    "syn_comment_doc":   "#6A7E75",
    "syn_ident":         "#839496",
    "syn_struct":        "#268BD2",
    "syn_enum":          "#B58900",
    "syn_fn":            "#268BD2",
    "syn_macro":         "#CB4B16",
    "syn_attribute":     "#2AA198",
    "syn_hot":           "#DC322F",
    "syn_operator":      "#839496",
    "syn_punctuation":   "#93A1A1",
    "syn_lifetime":      "#859900",
    "syn_self":          "#268BD2",
    "syn_constant":      "#CB4B16",
    "syn_variable":      "#839496",
    "syn_parameter":     "#839496",
    "syn_property":      "#839496",
    "syn_label":         "#657B83",
    "syn_escape":        "#DC322F",
    "syn_format":        "#2AA198",
    "syn_bool":          "#CB4B16",
    "syn_none":          "#CB4B16",
    "syn_regex":         "#2AA198",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Solarized Light
# ═══════════════════════════════════════════════════════════════════════════════

SOLARIZED_LIGHT: Theme = {
    "name":              "Solarized Light",
    "bg":                "#FDF6E3",
    "sidebar":           "#EEE8D5",
    "activity":          "#657B83",
    "border":            "#EEE8D5",
    "accent":            "#268BD2",
    "accent_hover":      "#2196DD",
    "accent_fg":         "#FDF6E3",
    "tab_active":        "#FDF6E3",
    "tab_inactive":      "#EEE8D5",
    "tab_text":          "#586E75",
    "tab_text_muted":    "#93A1A1",
    "text":              "#586E75",
    "text_secondary":    "#93A1A1",
    "muted":             "#93A1A1",
    "editor_bg":         "#FDF6E3",
    "editor_text":       "#586E75",
    "editor_selection":  "#EEE8D5",
    "editor_cursor":     "#586E75",
    "editor_line_hl":    "#EEE8D566",
    "line_number":       "#93A1A1",
    "line_number_bg":    "#FDF6E3",
    "line_number_active":"#586E75",
    "current_line":      "#EEE8D566",
    "selection":         "#EEE8D5",
    "match_highlight":   "#B5890044",
    "breadcrumb":        "#EEE8D5",
    "breadcrumb_text":   "#586E75",
    "panel_bg":          "#EEE8D5",
    "panel_border":      "#93A1A1",
    "statusbar":         "#EEE8D5",
    "statusbar_text":    "#586E75",
    "statusbar_item_hover": "#FDF6E3",
    "tree_selected":     "#EEE8D5",
    "tree_selected_fg":  "#002B36",
    "tree_hover":        "#EEE8D588",
    "tree_text":         "#586E75",
    "scrollbar":         "#93A1A1",
    "scrollbar_hover":   "#657B83",
    "input_bg":          "#FDF6E3",
    "input_border":      "#93A1A1",
    "input_text":        "#586E75",
    "input_placeholder": "#93A1A1",
    "button_bg":         "#268BD2",
    "button_text":       "#FDF6E3",
    "button_hover":      "#2196DD",
    "button_secondary":  "#EEE8D5",
    "button_secondary_text": "#586E75",
    "dropdown_bg":       "#FDF6E3",
    "dropdown_border":   "#93A1A1",
    "dropdown_text":     "#586E75",
    "popup_bg":          "#FDF6E3",
    "popup_border":      "#93A1A1",
    "popup_shadow":      "rgba(0,0,0,0.15)",
    "popup_selected":    "#268BD2",
    "popup_selected_fg": "#FDF6E3",
    "popup_hover":       "#EEE8D5",
    "completion_bg":     "#FDF6E3",
    "completion_border": "#93A1A1",
    "completion_text":   "#586E75",
    "completion_match":  "#268BD2",
    "completion_detail": "#93A1A1",
    "error":             "#DC322F",
    "error_bg":          "#FFF0F0",
    "warning":           "#B58900",
    "warning_bg":        "#FFFBF0",
    "info":              "#268BD2",
    "info_bg":           "#F0F8FF",
    "hint":              "#93A1A1",
    "success":           "#859900",
    "success_bg":        "#F0FFF4",
    "minimap_bg":        "#EEE8D5",
    "minimap_slider":    "#93A1A166",
    "indent_guide":      "#EEE8D5",
    "indent_guide_active":"#93A1A1",
    "bracket_match":     "#26ABD244",
    "bracket_match_border":"#268BD2",
    "find_bg":           "#FDF6E3",
    "find_border":       "#268BD2",
    "find_match":        "#B5890044",
    "find_match_border": "#B58900",
    "terminal_bg":       "#FDF6E3",
    "terminal_text":     "#586E75",
    "terminal_cursor":   "#586E75",
    "terminal_selection":"#EEE8D5",
    "gutter_add":        "#859900",
    "gutter_change":     "#B58900",
    "gutter_delete":     "#DC322F",
    # Syntax highlighting
    "syn_keyword":       "#859900",
    "syn_type":          "#268BD2",
    "syn_string":        "#2AA198",
    "syn_number":        "#D33682",
    "syn_comment":       "#93A1A1",
    "syn_comment_doc":   "#839191",
    "syn_ident":         "#586E75",
    "syn_struct":        "#268BD2",
    "syn_enum":          "#B58900",
    "syn_fn":            "#268BD2",
    "syn_macro":         "#CB4B16",
    "syn_attribute":     "#2AA198",
    "syn_hot":           "#DC322F",
    "syn_operator":      "#586E75",
    "syn_punctuation":   "#657B83",
    "syn_lifetime":      "#859900",
    "syn_self":          "#268BD2",
    "syn_constant":      "#CB4B16",
    "syn_variable":      "#586E75",
    "syn_parameter":     "#586E75",
    "syn_property":      "#586E75",
    "syn_label":         "#93A1A1",
    "syn_escape":        "#DC322F",
    "syn_format":        "#2AA198",
    "syn_bool":          "#CB4B16",
    "syn_none":          "#CB4B16",
    "syn_regex":         "#2AA198",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Nord
# ═══════════════════════════════════════════════════════════════════════════════

NORD: Theme = {
    "name":              "Nord",
    "bg":                "#2E3440",
    "sidebar":           "#3B4252",
    "activity":          "#2E3440",
    "border":            "#4C566A",
    "accent":            "#88C0D0",
    "accent_hover":      "#81A1C1",
    "accent_fg":         "#2E3440",
    "tab_active":        "#2E3440",
    "tab_inactive":      "#3B4252",
    "tab_text":          "#ECEFF4",
    "tab_text_muted":    "#D8DEE9",
    "text":              "#ECEFF4",
    "text_secondary":    "#D8DEE9",
    "muted":             "#A0A8B0",
    "editor_bg":         "#2E3440",
    "editor_text":       "#D8DEE9",
    "editor_selection":  "#434C5E",
    "editor_cursor":     "#D8DEE9",
    "editor_line_hl":    "#3B425266",
    "line_number":       "#616E88",
    "line_number_bg":    "#2E3440",
    "line_number_active":"#ECEFF4",
    "current_line":      "#3B425266",
    "selection":         "#434C5E",
    "match_highlight":   "#88C0D044",
    "breadcrumb":        "#3B4252",
    "breadcrumb_text":   "#D8DEE9",
    "panel_bg":          "#3B4252",
    "panel_border":      "#4C566A",
    "statusbar":         "#2E3440",
    "statusbar_text":    "#D8DEE9",
    "statusbar_item_hover": "#3B4252",
    "tree_selected":     "#4C566A",
    "tree_selected_fg":  "#ECEFF4",
    "tree_hover":        "#4C566A66",
    "tree_text":         "#D8DEE9",
    "scrollbar":         "#4C566A",
    "scrollbar_hover":   "#616E88",
    "input_bg":          "#3B4252",
    "input_border":      "#4C566A",
    "input_text":        "#ECEFF4",
    "input_placeholder": "#616E88",
    "button_bg":         "#88C0D0",
    "button_text":       "#2E3440",
    "button_hover":      "#81A1C1",
    "button_secondary":  "#4C566A",
    "button_secondary_text": "#ECEFF4",
    "dropdown_bg":       "#3B4252",
    "dropdown_border":   "#4C566A",
    "dropdown_text":     "#ECEFF4",
    "popup_bg":          "#3B4252",
    "popup_border":      "#4C566A",
    "popup_shadow":      "rgba(0,0,0,0.4)",
    "popup_selected":    "#4C566A",
    "popup_selected_fg": "#ECEFF4",
    "popup_hover":       "#4C566A66",
    "completion_bg":     "#3B4252",
    "completion_border": "#4C566A",
    "completion_text":   "#D8DEE9",
    "completion_match":  "#88C0D0",
    "completion_detail": "#616E88",
    "error":             "#BF616A",
    "error_bg":          "#3D1A1A",
    "warning":           "#EBCB8B",
    "warning_bg":        "#3D3200",
    "info":              "#88C0D0",
    "info_bg":           "#1A2D3D",
    "hint":              "#616E88",
    "success":           "#A3BE8C",
    "success_bg":        "#1A3D1A",
    "minimap_bg":        "#3B4252",
    "minimap_slider":    "#4C566A66",
    "indent_guide":      "#4C566A",
    "indent_guide_active":"#616E88",
    "bracket_match":     "#88C0D044",
    "bracket_match_border":"#88C0D0",
    "find_bg":           "#3B4252",
    "find_border":       "#88C0D0",
    "find_match":        "#EBCB8B44",
    "find_match_border": "#EBCB8B",
    "terminal_bg":       "#2E3440",
    "terminal_text":     "#D8DEE9",
    "terminal_cursor":   "#D8DEE9",
    "terminal_selection":"#434C5E",
    "gutter_add":        "#A3BE8C",
    "gutter_change":     "#EBCB8B",
    "gutter_delete":     "#BF616A",
    # Syntax highlighting
    "syn_keyword":       "#81A1C1",
    "syn_type":          "#8FBCBB",
    "syn_string":        "#A3BE8C",
    "syn_number":        "#B48EAD",
    "syn_comment":       "#616E88",
    "syn_comment_doc":   "#717E98",
    "syn_ident":         "#D8DEE9",
    "syn_struct":        "#8FBCBB",
    "syn_enum":          "#8FBCBB",
    "syn_fn":            "#88C0D0",
    "syn_macro":         "#81A1C1",
    "syn_attribute":     "#88C0D0",
    "syn_hot":           "#BF616A",
    "syn_operator":      "#ECEFF4",
    "syn_punctuation":   "#D8DEE9",
    "syn_lifetime":      "#81A1C1",
    "syn_self":          "#81A1C1",
    "syn_constant":      "#B48EAD",
    "syn_variable":      "#D8DEE9",
    "syn_parameter":     "#D8DEE9",
    "syn_property":      "#D8DEE9",
    "syn_label":         "#616E88",
    "syn_escape":        "#81A1C1",
    "syn_format":        "#8FBCBB",
    "syn_bool":          "#81A1C1",
    "syn_none":          "#81A1C1",
    "syn_regex":         "#A3BE8C",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Monokai
# ═══════════════════════════════════════════════════════════════════════════════

MONOKAI: Theme = {
    "name":              "Monokai",
    "bg":                "#272822",
    "sidebar":           "#1E1F1C",
    "activity":          "#1E1F1C",
    "border":            "#3D3E37",
    "accent":            "#A6E22E",
    "accent_hover":      "#90D118",
    "accent_fg":         "#272822",
    "tab_active":        "#272822",
    "tab_inactive":      "#1E1F1C",
    "tab_text":          "#F8F8F2",
    "tab_text_muted":    "#75715E",
    "text":              "#F8F8F2",
    "text_secondary":    "#75715E",
    "muted":             "#75715E",
    "editor_bg":         "#272822",
    "editor_text":       "#F8F8F2",
    "editor_selection":  "#49483E",
    "editor_cursor":     "#F8F8F2",
    "editor_line_hl":    "#3E3D3288",
    "line_number":       "#75715E",
    "line_number_bg":    "#272822",
    "line_number_active":"#F8F8F2",
    "current_line":      "#3E3D3288",
    "selection":         "#49483E",
    "match_highlight":   "#FFE79244",
    "breadcrumb":        "#1E1F1C",
    "breadcrumb_text":   "#75715E",
    "panel_bg":          "#1E1F1C",
    "panel_border":      "#3D3E37",
    "statusbar":         "#1E1F1C",
    "statusbar_text":    "#75715E",
    "statusbar_item_hover": "#272822",
    "tree_selected":     "#49483E",
    "tree_selected_fg":  "#F8F8F2",
    "tree_hover":        "#49483E88",
    "tree_text":         "#F8F8F2",
    "scrollbar":         "#49483E",
    "scrollbar_hover":   "#75715E",
    "input_bg":          "#1E1F1C",
    "input_border":      "#3D3E37",
    "input_text":        "#F8F8F2",
    "input_placeholder": "#75715E",
    "button_bg":         "#A6E22E",
    "button_text":       "#272822",
    "button_hover":      "#90D118",
    "button_secondary":  "#3D3E37",
    "button_secondary_text": "#F8F8F2",
    "dropdown_bg":       "#1E1F1C",
    "dropdown_border":   "#3D3E37",
    "dropdown_text":     "#F8F8F2",
    "popup_bg":          "#1E1F1C",
    "popup_border":      "#3D3E37",
    "popup_shadow":      "rgba(0,0,0,0.5)",
    "popup_selected":    "#49483E",
    "popup_selected_fg": "#F8F8F2",
    "popup_hover":       "#49483E88",
    "completion_bg":     "#1E1F1C",
    "completion_border": "#3D3E37",
    "completion_text":   "#F8F8F2",
    "completion_match":  "#A6E22E",
    "completion_detail": "#75715E",
    "error":             "#F92672",
    "error_bg":          "#3D1A1A",
    "warning":           "#E6DB74",
    "warning_bg":        "#3D3200",
    "info":              "#66D9E8",
    "info_bg":           "#1A2D3D",
    "hint":              "#75715E",
    "success":           "#A6E22E",
    "success_bg":        "#1A3D1A",
    "minimap_bg":        "#1E1F1C",
    "minimap_slider":    "#49483E66",
    "indent_guide":      "#3D3E37",
    "indent_guide_active":"#75715E",
    "bracket_match":     "#A6E22E44",
    "bracket_match_border":"#A6E22E",
    "find_bg":           "#1E1F1C",
    "find_border":       "#A6E22E",
    "find_match":        "#E6DB7444",
    "find_match_border": "#E6DB74",
    "terminal_bg":       "#272822",
    "terminal_text":     "#F8F8F2",
    "terminal_cursor":   "#F8F8F2",
    "terminal_selection":"#49483E",
    "gutter_add":        "#A6E22E",
    "gutter_change":     "#E6DB74",
    "gutter_delete":     "#F92672",
    # Syntax highlighting
    "syn_keyword":       "#F92672",
    "syn_type":          "#66D9E8",
    "syn_string":        "#E6DB74",
    "syn_number":        "#AE81FF",
    "syn_comment":       "#75715E",
    "syn_comment_doc":   "#857E6E",
    "syn_ident":         "#F8F8F2",
    "syn_struct":        "#66D9E8",
    "syn_enum":          "#66D9E8",
    "syn_fn":            "#A6E22E",
    "syn_macro":         "#F92672",
    "syn_attribute":     "#66D9E8",
    "syn_hot":           "#F92672",
    "syn_operator":      "#F92672",
    "syn_punctuation":   "#F8F8F2",
    "syn_lifetime":      "#FD971F",
    "syn_self":          "#FD971F",
    "syn_constant":      "#AE81FF",
    "syn_variable":      "#F8F8F2",
    "syn_parameter":     "#FD971F",
    "syn_property":      "#F8F8F2",
    "syn_label":         "#75715E",
    "syn_escape":        "#AE81FF",
    "syn_format":        "#66D9E8",
    "syn_bool":          "#AE81FF",
    "syn_none":          "#AE81FF",
    "syn_regex":         "#E6DB74",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Theme registry
# ═══════════════════════════════════════════════════════════════════════════════

ALL_THEMES: Dict[str, Theme] = {
    "light":           LIGHT,
    "dark":            DARK,
    "high_contrast":   HIGH_CONTRAST,
    "dracula":         DRACULA,
    "solarized_dark":  SOLARIZED_DARK,
    "solarized_light": SOLARIZED_LIGHT,
    "nord":            NORD,
    "monokai":         MONOKAI,
}

THEME_NAMES: Dict[str, str] = {k: v["name"] for k, v in ALL_THEMES.items()}

# ─── Current active theme (mutable) ──────────────────────────────────────────

_current_theme_key: str = "light"
_current: Theme = LIGHT


def get() -> Theme:
    """Returns the currently active theme dict."""
    return _current


def get_key() -> str:
    """Returns the current theme key."""
    return _current_theme_key


def set_theme(key: str) -> Theme:
    """Switch to a theme by key. Returns the new theme."""
    global _current, _current_theme_key
    if key in ALL_THEMES:
        _current_theme_key = key
        _current = ALL_THEMES[key]
    return _current


def theme_by_name(name: str) -> Theme:
    """Look up a theme by display name (case-insensitive)."""
    name_lower = name.lower()
    for k, t in ALL_THEMES.items():
        if t["name"].lower() == name_lower or k == name_lower:
            return t
    return LIGHT


def is_dark(theme: Theme | None = None) -> bool:
    """Returns True if the theme is a dark theme."""
    t = theme or _current
    bg = t.get("bg", "#FFFFFF")
    # Parse hex luminance
    try:
        r = int(bg[1:3], 16)
        g = int(bg[3:5], 16)
        b = int(bg[5:7], 16)
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return luminance < 128
    except Exception:
        return False


def get_color(key: str, theme: Theme | None = None) -> str:
    """Get a color value by key, with fallback."""
    t = theme or _current
    return t.get(key, "#888888")


def make_stylesheet(theme: Theme | None = None) -> str:
    """Generate a basic Qt stylesheet from the theme."""
    T = theme or _current
    return f"""
    QWidget {{
        background-color: {T['bg']};
        color: {T['text']};
        font-family: 'Segoe UI', 'SF Pro Text', Arial, sans-serif;
        font-size: 10pt;
    }}
    QMainWindow {{
        background-color: {T['bg']};
    }}
    QMenuBar {{
        background-color: {T['sidebar']};
        color: {T['text']};
        border-bottom: 1px solid {T['border']};
    }}
    QMenuBar::item:selected {{
        background-color: {T['accent']};
        color: {T['accent_fg']};
    }}
    QMenu {{
        background-color: {T['popup_bg']};
        color: {T['text']};
        border: 1px solid {T['popup_border']};
    }}
    QMenu::item:selected {{
        background-color: {T['popup_selected']};
        color: {T['popup_selected_fg']};
    }}
    QStatusBar {{
        background-color: {T['statusbar']};
        color: {T['statusbar_text']};
    }}
    QScrollBar:vertical {{
        background: {T['bg']};
        width: 12px;
    }}
    QScrollBar::handle:vertical {{
        background: {T['scrollbar']};
        border-radius: 6px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {T['scrollbar_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: {T['bg']};
        height: 12px;
    }}
    QScrollBar::handle:horizontal {{
        background: {T['scrollbar']};
        border-radius: 6px;
        min-width: 20px;
    }}
    QSplitter::handle {{
        background: {T['border']};
    }}
    QToolTip {{
        background-color: {T['popup_bg']};
        color: {T['text']};
        border: 1px solid {T['popup_border']};
        padding: 4px 8px;
        border-radius: 3px;
    }}
    QTabWidget::pane {{
        border: none;
        background: {T['bg']};
    }}
    QTabBar::tab {{
        background: {T['tab_inactive']};
        color: {T['tab_text_muted']};
        padding: 8px 16px;
        border: 1px solid {T['border']};
        border-bottom: none;
    }}
    QTabBar::tab:selected {{
        background: {T['tab_active']};
        color: {T['tab_text']};
        border-top: 2px solid {T['accent']};
    }}
    QTabBar::tab:hover {{
        background: {T['tab_active']};
        color: {T['tab_text']};
    }}
    QLineEdit, QPlainTextEdit, QTextEdit {{
        background-color: {T['input_bg']};
        color: {T['input_text']};
        border: 1px solid {T['input_border']};
        border-radius: 3px;
        padding: 4px;
        selection-background-color: {T['selection']};
    }}
    QLineEdit:focus, QPlainTextEdit:focus {{
        border-color: {T['accent']};
    }}
    QPushButton {{
        background-color: {T['button_bg']};
        color: {T['button_text']};
        border: none;
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {T['button_hover']};
    }}
    QPushButton:pressed {{
        opacity: 0.8;
    }}
    QPushButton[secondary="true"] {{
        background-color: {T['button_secondary']};
        color: {T['button_secondary_text']};
    }}
    QComboBox {{
        background-color: {T['dropdown_bg']};
        color: {T['dropdown_text']};
        border: 1px solid {T['dropdown_border']};
        border-radius: 3px;
        padding: 4px 8px;
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QListWidget, QTreeWidget {{
        background-color: {T['sidebar']};
        color: {T['tree_text']};
        border: none;
        selection-background-color: {T['tree_selected']};
        selection-color: {T['tree_selected_fg']};
    }}
    QListWidget::item:hover, QTreeWidget::item:hover {{
        background-color: {T['tree_hover']};
    }}
    QListWidget::item:selected, QTreeWidget::item:selected {{
        background-color: {T['tree_selected']};
        color: {T['tree_selected_fg']};
    }}
    QCheckBox {{
        color: {T['text']};
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {T['input_border']};
        border-radius: 2px;
        background: {T['input_bg']};
    }}
    QCheckBox::indicator:checked {{
        background: {T['accent']};
        border-color: {T['accent']};
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {T['border']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {T['accent']};
        width: 14px;
        height: 14px;
        border-radius: 7px;
        margin: -5px 0;
    }}
    QGroupBox {{
        border: 1px solid {T['border']};
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
        color: {T['text_secondary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }}
    QSplitter {{
        background: {T['bg']};
    }}
    """


# ─── Convenience alias ────────────────────────────────────────────────────────

T = LIGHT   # default theme shorthand (backwards compat)
