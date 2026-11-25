---
layout: article.njk
title: "Install 3D Mesh Tools & Compare | 3DScanPost"
breadcrumb: "Installation"
description: How to install 3D Mesh Tools and 3D Mesh Compare — free STL mesh programs for Windows, macOS and Linux. Install Python, five libraries and download the source.
permalink: /tools/install/
tags: indexable
cta: download
ogType: article
parent:
  name: Free Tools
  url: /tools/
---

# Installing 3D Mesh Tools and 3D Mesh Compare

[3D Mesh Tools](/tools/3d-mesh-tools/) and [3D Mesh Compare](/tools/3d-mesh-compare/) are installed together — one download, one set of libraries. They are small Python programs, so you'll need Python and five free libraries. The source code is on [GitHub](https://github.com/madjalapeno/3dmeshtools).

3D Mesh Tools and 3D Mesh Compare are small Python programs that share the same libraries. You'll need Python and five free libraries.

## 1. Install Python

If you don't already have it, download Python 3.10 or newer from [python.org](https://www.python.org/downloads/).

On **Windows**, tick **"Add python.exe to PATH"** on the first screen of the installer.

## 2. Install the libraries

Open a terminal (on Windows, *Command Prompt* or *PowerShell*; on macOS, *Terminal*) and run:

```
python -m pip install numpy scipy pyvista pyvistaqt pyside6
```

On macOS and some Linux systems the command is `python3` rather than `python`:

```
python3 -m pip install numpy scipy pyvista pyvistaqt pyside6
```

This downloads a few hundred megabytes (mostly the VTK 3D engine and the Qt interface toolkit), so it may take a minute or two.

## 3. Optional: MeshLab, for clean file-size reduction

3D Mesh Tools' built-in reduction is fast, but on dense scans it can leave a few tiny holes and broken edges (slicers usually repair these). For a clean result that keeps the mesh intact, also install MeshLab's Python package — about 280 MB:

```
python -m pip install pymeshlab
```

3D Mesh Tools uses it automatically when it's installed. It is only used for file-size reduction in 3D Mesh Tools; 3D Mesh Compare doesn't need it.

## 4. Download

[Download the zip](https://github.com/madjalapeno/3dmeshtools/archive/refs/heads/main.zip) (or clone [the repository](https://github.com/madjalapeno/3dmeshtools) with git) and unzip it somewhere convenient, such as your Documents folder. Both programs are in the one download. Keep the files together: `3dmeshtools.py`, `3dmeshcompare.py` and the `meshtools3d` folder next to them.

## Running the programs

In a terminal, change to the unzipped folder, then run whichever you need:

```
python 3dmeshtools.py
python 3dmeshcompare.py
```

On macOS and some Linux systems, use `python3` instead of `python`. See the guides for [3D Mesh Tools](/tools/3d-mesh-tools/#running-it) and [3D Mesh Compare](/tools/3d-mesh-compare/#running-it) for what happens next.

## Troubleshooting

{% include "troubleshooting-common.njk" %}

## Source code

The source is at [github.com/madjalapeno/3dmeshtools](https://github.com/madjalapeno/3dmeshtools). 3D Mesh Tools is built with [PyVista](https://pyvista.org/), [VTK](https://vtk.org/), [Qt](https://www.qt.io/) and [NumPy](https://numpy.org/), with optional mesh reduction by [MeshLab](https://www.meshlab.net/) (pymeshlab).
