---
layout: article.njk
title: "STL Align | Free STL Leveling & Alignment Tool | 3DScanPost"
breadcrumb: "STL Align"
description: A free desktop tool for levelling, squaring up, scaling and re-centring STL meshes and 3D scans before CAD or 3D printing.
permalink: /stl-align/
tags: indexable
---

# STL Align

**STL Align** is a free, open desktop tool for tidying up the orientation of STL meshes — especially 3D scans, which rarely come out of the scanner sitting square to anything. Pick a few points on the model (or let it find a flat face for you) and it will level the part, square it to the X/Y axes, scale it to a known dimension and put the origin where you want it. Then save a clean STL that drops straight into CAD, a slicer or a reverse-engineering workflow.

[Download stl_align.py](/stl-align/stl_align.py)

*Current version: 1.4 · Windows, macOS and Linux · requires Python 3.10 or newer*

## What it does

- **Level a part on any face.** Pick three points on the face that should sit flat, or use **Find plane** to detect the largest flat area automatically (press it again to cycle to the next one). A preview shows the plane and which way is "up" before anything changes.
- **Refine the fit.** Three hand-picked points on a noisy scan can be a fraction of a degree off. *Refine* fits the plane to every vertex on that face using least squares, so the result is as flat as the scan allows.
- **Square it to X or Y.** Pick two points along a straight edge, or define a plane on a side face, and rotate the part about Z so that edge runs along X or Y. The level you set is kept.
- **Scale to a real dimension.** Pick two points across a feature you know the size of, type the true measurement, and the whole mesh scales to match. One-click inch ↔ mm conversion is included for files exported in the wrong units.
- **Set the origin.** Centre the part's bounding box on 0,0 (keeping its base on Z = 0), centre it in all three axes, or put any picked point at the origin.
- **Undo anything.** Every step can be undone, and nothing touches your original file.
- **Re-use the transform.** Alongside the aligned STL, STL Align saves the exact 4×4 transformation matrix it applied. You can apply that same transform to another file — for example, align a lightweight decimated scan interactively, then apply the identical move to the full-resolution mesh.

It opens **STL, PLY and OBJ** files and saves binary STL.

## Installing

STL Align is a single Python script. You'll need Python and four free libraries.

### 1. Install Python

If you don't already have it, download Python 3.10 or newer from [python.org](https://www.python.org/downloads/).

On **Windows**, tick **"Add python.exe to PATH"** on the first screen of the installer.

### 2. Install the libraries

Open a terminal (on Windows, *Command Prompt* or *PowerShell*; on macOS, *Terminal*) and run:

```
python -m pip install numpy pyvista pyvistaqt pyside6
```

On macOS and some Linux systems the command is `python3` rather than `python`:

```
python3 -m pip install numpy pyvista pyvistaqt pyside6
```

This downloads a few hundred megabytes (mostly the VTK 3D engine and the Qt interface toolkit), so it may take a minute or two.

### 3. Download STL Align

[Download stl_align.py](/stl-align/stl_align.py) and save it somewhere convenient, such as your Documents folder.

## Running it

In a terminal, change to the folder you saved it in and run:

```
python stl_align.py
```

A file browser opens so you can choose a mesh. You can also open a file directly:

```
python stl_align.py "C:\Scans\bracket.stl"
```

On Windows you can usually just double-click `stl_align.py` as well.

## A typical session

1. **Open** your scan (*File › Open*, or Ctrl+O).
2. **Level it.** Right-click three points spread out across the face that should sit on the bed — or use **Find plane automatically**. A yellow plane appears with an arrow showing the new +Z; the part will end up on the arrow side. Use **Refine** for a more accurate fit and **Flip** if the arrow is pointing the wrong way, then click the green **Level on this plane** button (or press Enter).
3. **Square it up.** Right-click two points along a straight edge, then choose **Align edge to X** or **Align edge to Y**.
4. **Scale it** (optional). Right-click two points across a known dimension, choose **Scale to distance…** and type the real value.
5. **Set the origin.** *Origin › Center of extents – XY* centres the part on 0,0 with its base on Z = 0.
6. **Save** (Ctrl+S). This writes `yourfile_aligned.stl` and `yourfile_aligned_matrix.txt` next to the original.

The strip along the bottom of the window always tells you what your picks can be used for, offers buttons for the next step, and shows whether you have unsaved changes. *Help › Quick start* (F1) walks through the same steps inside the program.

## Controls

| Action | How |
|---|---|
| Rotate the view | Left-drag |
| Pan | Middle-drag, or Shift + left-drag |
| Zoom | Scroll wheel |
| Roll | Ctrl + left-drag |
| Fit model to window | Ctrl+0 |
| Pick a point | **Right-click** on the model, or hover and press **P** |
| Clear picks | Esc |
| Apply a previewed plane | Enter |
| Undo | Ctrl+Z |

Every command is in the menus at the top of the window, with its keyboard shortcut alongside. *Help › Mouse & keyboard controls* lists them all. On a Mac, use **Cmd** in place of Ctrl; a two-finger click on a trackpad counts as a right-click.

You can change the model's display colour under *View › Model colour…*.

## Command-line use

STL Align can also run without the window, which is handy for batch jobs.

Automatically level a part on its largest flat face and save it:

```
python stl_align.py part.stl --auto
```

Add `--center xy` to also centre it on the origin, `--tol 0.2` to set how close (in model units) a point must be to count as on the plane, and `-o output.stl` to choose the output name.

Apply a saved transform to another file:

```
python stl_align.py full_res_scan.stl --apply-matrix part_aligned_matrix.txt
```

The matrix file is plain text: a 4×4 row-major transform, so it can also be used in your own scripts or other software.

## Troubleshooting

**The window flashes open and closes immediately.**
Run it from a terminal instead of double-clicking, so you can read the error. In most cases a library is missing.

**"No module named numpy" (or pyvista, pyvistaqt, qtpy).**
The libraries were installed for a different copy of Python. Run the install command using the same `python` you use to start the program:

```
python -m pip install numpy pyvista pyvistaqt pyside6
```

**Picking doesn't seem to do anything.**
Make sure you're right-clicking directly on the model, not the background. The bottom strip updates after every successful pick.

**Find plane picks the wrong face.**
Press it again — each press moves on to the next-largest flat area. For noisy scans, try raising the tolerance under *Plane › Plane tolerance…*.

**On Linux: "Could not load the Qt platform plugin xcb".**
Install the missing system library, e.g. on Ubuntu/Debian: `sudo apt install libxcb-cursor0`.

## Download

[Download stl_align.py](/stl-align/stl_align.py)

STL Align is built with [PyVista](https://pyvista.org/), [VTK](https://vtk.org/), [Qt](https://www.qt.io/) and [NumPy](https://numpy.org/).