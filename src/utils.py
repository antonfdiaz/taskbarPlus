from PySide6.QtGui import QColor
from src.config import Config

def theme_color_css(value,fallback="transparent"):
    if value is None:
        return "#01000000"

    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() == "transparent":
            return "#01000000"

    color = QColor(value)
    if color.isValid():
        if color.alpha() == 0:
            return "#01000000"
        return color.name(QColor.HexArgb)

    return fallback

def theme_color(value,fallback="#00000000"):
    if value is None:
        return QColor(0,0,0,0)

    if isinstance(value,str):
        value = value.strip()
        if not value or value.lower() == "transparent":
            return QColor(0,0,0,0)

    color = QColor(value)
    if not color.isValid():
        return QColor(fallback)

    return color

def menu_style(config: Config):
    theme = config.theme
    return f"""
        QMenu {{
            background-color: {theme_color_css(theme.menu_background)};
            color: {theme_color_css(theme.menu_foreground)};
            border: 1px solid {theme_color_css(theme.menu_foreground)};
        }}
        QMenu::item {{
            padding: 8px;
            padding-right: 80px;
        }}
        QMenu::item:selected {{
            background-color: {theme_color_css(theme.menu_hover)};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {theme_color_css(theme.menu_separator_color)};
        }}
    """