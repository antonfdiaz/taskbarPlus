# taskbarPlus

taskbarPlus is a very customizable taskbar replacement for Windows.  

## Features

- Customize a lot of stuff
- Create skins and use custom icons
- Tray support
- "Everything" support for search
- Task list with instant update
- Multiple language support
- And more!

## How to run
To get started with taskbarPlus, download the code and run it with Python.  

- CD to the project folder with: `cd PATH/TO/SOURCE`
- Make a venv inside the project folder with `py -m venv .venv`
- Activate the venv with `.venv\Scripts\activate`
- Install libraries with `pip install -r requirements.txt`
- Run the code with `py main.py`

## Configuration

taskbarPlus is configured using **JSON** files. The configuration folder is located at `taskbarPlus/config`. The user configuration is located at `taskbarPlus/config/user`.

## Skins

Skins are located at `taskbarPlus/config/skins`. You can create your own skins by creating a new folder in the skins directory and adding `metadata.json`, `theme.json` and `layout.json` and any necessary icons in the `assets` folder.

Normally it is easier to start by copying an existing skin and modifying it to suit your needs.

taskbarPlus comes with 3 default skins:

- `default` is the Windows 10 style skin.
- `centered` is a centered taskbar style, like in Windows 11.
- `aero` is a Windows 7 style skin.
