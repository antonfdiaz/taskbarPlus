from PySide6.QtCore import Qt
from PySide6.QtGui import QColor,QPixmap
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
        QMenu::icon {{
            margin-left: 10px;
        }}
        QMenu::right-arrow {{
            height: 12px;
        }}
    """

def pixmap_dominant_color(pixmap: QPixmap | None):
    if pixmap is None or pixmap.isNull():
        return "#00000000"

    image = pixmap.scaled(24,24,Qt.KeepAspectRatio,Qt.SmoothTransformation).toImage()
    colors: dict[tuple[int,int,int],int] = {}

    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x,y)
            alpha = color.alpha()
            if alpha < 32:
                continue

            key = (
                color.red()//16*16,
                color.green()//16*16,
                color.blue()//16*16
            )
            colors[key] = colors.get(key,0)+alpha

    if not colors:
        return "#ffffff"

    red,green,blue = max(colors,key=colors.get)
    return QColor(red,green,blue).name()
