# taskbarPlus

taskbarPlus is a very customizable taskbar replacement for Windows.  

<img width="1920" height="30" alt="win10 taskbar" src="https://github.com/user-attachments/assets/bc2b5681-b5f0-46d1-b28d-aa8848e5b7f8" />
<img width="1920" height="41" alt="win7 taskbar" src="https://github.com/user-attachments/assets/c06d4f31-bd45-4e0f-9fae-eeccc13fd09d" />

## Features

- Custom widget plugins
- Create skins and use custom icons
- Tray support
- "Everything" support for search
- Task list with instant update
- Multiple language support
- Taskbar animations
- Custom button styles (and *hottracking*)
- And more!

## How to run
To get started with taskbarPlus, download the code and run it with Python, or download a [prebuilt release](https://github.com/antonfdiaz/taskbarPlus/releases).  

- CD to the project folder with: `cd PATH/TO/SOURCE`
- Make a venv inside the project folder with `py -m venv .venv`
- Activate the venv with `.venv\Scripts\activate`
- Install libraries with `pip install -r requirements.txt`
- Run the code with `py main.py`

> **Note:** taskbarPlus works on Windows 7 if you use VxKex. However, it won't have taskbar blur; an Aero implementation is coming soon. For now, you can use the `default-solid` skin: [Link](https://github.com/antonfdiaz/taskbarPlus/releases/download/0.6.8/default-solid.zip)

## Build from source
To build the project and make an .exe, do the following steps:  

- Do the same steps as above except the last one
- Install build deps with `pip install nuitka imageio`
- Build the project by double-clicking `build.bat`
- To run it, just open `taskbarPlus.exe`

After building, it is best to copy `taskbarPlus.exe`, `config/`, `assets/`, `plugins` and `l18n/` to a folder separate from the source code.

## Configuration

taskbarPlus is configured using **JSON/JSONC** files. The configuration folder is located at `taskbarPlus/config`. The user configuration is located at `taskbarPlus/config/user`. User configuration includes these files:
- `behavior.json`: Defines clock settings and search function settings.
- `settings.json`: Defines the active language and skin.
- `apps.json`: Defines the apps pinned in the taskbar.

## Skins

Skins are located at `taskbarPlus/config/skins`. You can create your own skins by creating a new folder in the skins directory and adding `metadata.json`, `theme.jsonc` and `layout.json` and any necessary icons in the `assets` folder. Older `theme.json` files are still supported.

It is usually easiest to start by copying an existing skin and modifying it to suit your needs.  
You can view documentation about skins [here](https://github.com/antonfdiaz/taskbarPlus/blob/main/docs/skins.md). 

taskbarPlus comes with 5 default skins:

- `default` is the Windows 10 style skin.
- `default-sb` is the superbar variant of `default`.
- `centered` is a centered taskbar style, like in Windows 11.
- `centered-sb` is the superbar variant of `centered`.
- `aero` is a Windows 7 style skin.
