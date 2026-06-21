# Skins
This file contains documentation on JSON files and custom assets for making taskbarPlus skins.

## metadata.json
In this file you define information about the skin, such as name, author, version and ID. The ID is the identifier for your skin. It's best to put a short ID for your skin, and avoid spaces. Example:
```
{
    "id": "my_skin",
    "name": "My Skin",
    "author": "t0nchi7",
    "version": "1.0.0"
}
```

## layout.json
In this file you define the position of the widgets in the taskbar.  
You can put widgets on the side of the taskbar you want. These are the available widgets:
- `start`: Start button
- `search`: Search button/box
- `task_view`: Task View button
- `apps`: Apps bar (pinned & running apps)
- `tray`: System tray
- `clock`: Clock (date & time)
- `show_desktop`: Show desktop button  

Example file:
```
{
    "left": ["start","search","task_view","apps"],
    "center": [],
    "right": ["tray","clock","show_desktop"]
}
```

## theme.json
If you want to make a custom look for your taskbar, this is the most important file. There are a lot of properties in this file, each one to define something about the taskbar and its items, such as colors, sizes, icons, and more. These are the current properties:

### Taskbar

- `taskbar_height`: Height of the taskbar in pixels.

- `taskbar_texture`: Background texture for the taskbar. Set it to a relative asset path such as `assets/texture.png`, or `null` to disable the texture.

- `taskbar_texture_mode`: How the taskbar texture is drawn. It can be `stretch` or `tile`.

- `taskbar_texture_opacity`: The opacity of the taskbar texture. Its value can be between 0.0 and 1.0.

- `taskbar_blur`: Enables Windows acrylic/DWM blur on the taskbar. Use `true` to enable it or `false` to disable it.

- `taskbar_blur_tint`: Tint color applied to the taskbar blur. This uses an ARGB-style hex value in the form `#AARRGGBB`, where the first two digits are the alpha channel. Example: `#cc202020`. Lower alpha values make the taskbar more transparent.

- `background`: Base background color of the taskbar. This is usually a hex color such as `#202020` or `#00000000`. If blur is enabled, it is best to set this to `transparent`.

- `foreground`: Default foreground/text color used by taskbar widgets.

- `accent`: Accent color used mainly by running app indicators.

### Buttons

- `hover`: Default button background color used when a taskbar button is hovered.

- `active`: Default button background color used when a taskbar button is pressed or active.

- `icon_size`: Default icon size in pixels for taskbar app buttons.

- `icon_opacity`: Opacity of button icons. Use values between `0.0` and `1.0`.

- `button_width`: Default width in pixels for taskbar buttons.

- `button_height`: Default height in pixels for taskbar buttons.

- `button_style`: The style in which taskbar buttons will be drawn. It can be `win10`, `win8` or `win7`.

- `padding_x`: Horizontal internal padding used by several widgets.

- `padding_y`: Vertical internal padding used by several widgets.

- `gap`: Spacing in pixels between taskbar widgets and app buttons in normal taskbar sections.

### Tray

- `tray_icon_size`: Icon size in pixels for tray icons.

- `tray_gap`: Spacing in pixels between tray icons.

### Start button

- `start_icon_transition`: Transition settings for the Start button icon animation. This is currently an object with:
  - `duration`: animation duration in milliseconds
  - `easing`: Qt easing curve name, such as `OutCubic`.

- `start_icon`: Path to the Start button icon image.

- `start_icon_size`: Size in pixels for the Start button icon.

- `start_button_fx`: Whether or not to apply hover and active effects to the Start button.

- `start_button_width`: Width in pixels of the Start button.

- `start_button_height`: Height in pixels of the Start button.

- `start_button_hover`: Background color used when the Start button is hovered.

- `start_button_active`: Background color used when the Start button is pressed or active.

### Search

- `search_icon`: Path to the search icon image.

- `search_icon_size`: Size in pixels of the search icon. This is used both for the search button and for the icon drawn inside the search box.

- `search_button_width`: Width in pixels of the search button, when search is configured in icon mode.

- `search_button_height`: Height in pixels of the search button, when search is configured in icon mode.

- `search_box_width`: Width in pixels of the search box area, not counting the extra horizontal padding added by the widget.

- `search_box_height`: Height in pixels of the search box.

- `search_box_background`: Background color of the search box.

- `search_box_foreground`: Text color of the search box.

### Task View

- `task_view_icon`: Path to the Task View button icon image.

- `task_view_icon_size`: Size in pixels of the Task View button icon.

- `task_view_button_width`: Width in pixels of the Task View button.

- `task_view_button_height`: Height in pixels of the Task View button.

### Show desktop

- `show_desktop_width`: Width in pixels of the Show Desktop button.

- `show_desktop_border_color`: Border color of the Show Desktop button.

### Menus

- `menu_background`: Background color of taskbar context menus.

- `menu_foreground`: Text color of taskbar context menus. This color is also used as the menu border color.

- `menu_hover`: Background color used when hovering an item in a taskbar context menu.

- `menu_separator_color`: Color of separators in taskbar context menus.

## Custom assets
With skins, you can override default icons by making an `assets` folder inside the skin folder and placing the custom assets you want to use. Usually, they have to use the same filename as the asset you want to override for them to be correctly loaded, but some settings like the taskbar texture allow you to specify the asset path so you can use whatever filename you want. Paths to assets are relative, for example, `assets/start.png`.
