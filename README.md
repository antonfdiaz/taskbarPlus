# taskbarPlus

taskbarPlus is a very customizable taskbar replacement for Windows.  

<img alt="preview" src="https://github.com/user-attachments/assets/2d1f3737-c39b-401a-aba3-75800d72ea74">

## Features

- Customize a lot of stuff
- Create skins and use custom icons
- Tray support
- "Everything" support for search
- Task list with instant update
- Multiple language support
- Taskbar animations
- And more!

## How to run
To get started with taskbarPlus, download the code and run it with Python, or download a [prebuilt release](https://github.com/antonfdiaz/taskbarPlus/releases).  

- CD to the project folder with: `cd PATH/TO/SOURCE`
- Make a venv inside the project folder with `py -m venv .venv`
- Activate the venv with `.venv\Scripts\activate`
- Install libraries with `pip install -r requirements.txt`
- Run the code with `py main.py`

## Build from source
To build the project and make an .exe, do the following steps:  

- Do the same steps as above except the last one
- Install Nuitka with `pip install nuitka`
- Build by double clicking `build.bat`
- To run it, just open `taskbarPlus.exe`

After building, it is best to copy the files `taskbarPlus.exe`, `config/`, `assets/` and `l18n/` to a folder separate from the source code.

## Configuration

taskbarPlus is configured using **JSON** files. The configuration folder is located at `taskbarPlus/config`. The user configuration is located at `taskbarPlus/config/user`. User configuration includes these files:
- `behavior.json`: Defines clock settings and search function settings.
- `settings.json`: Defines the active language and skin.
- `apps.json`: Defines the apps pinned in the taskbar.

## Skins

Skins are located at `taskbarPlus/config/skins`. You can create your own skins by creating a new folder in the skins directory and adding `metadata.json`, `theme.json` and `layout.json` and any necessary icons in the `assets` folder.

Normally it is easier to start by copying an existing skin and modifying it to suit your needs.  
You can view documentation about skins [here](https://github.com/antonfdiaz/taskbarPlus/blob/main/docs/skins.md). 

taskbarPlus comes with 3 default skins:

- `default` is the Windows 10 style skin.
- `centered` is a centered taskbar style, like in Windows 11.
- `aero` is a Windows 7 style skin.
