---
layout: article.njk
title: "STL Scan to SolidWorks as IGES Curves | 3DScanPost"
breadcrumb: "Scan to SolidWorks"
description: Turn a scanned STL into section curves and flat faces that open in SolidWorks as an IGES file, using Claude AI and ScanRuler. Copy-and-paste prompts.
permalink: /guides/scan-to-solidworks/
tags:
  - indexable
  - guide
cta: download
ogType: article
parent:
  name: Guides
  url: /guides/
schema: article
ogImage: /assets/images/og/solidworks-guide.jpg
ogImageAlt: "Five section lines cut through a scanned hub cap, ready to export as IGES curves"
---

# From a scanned STL to section curves in SolidWorks

SolidWorks can open an STL, but you can't build on it: it is a mesh of thousands of tiny triangles with nothing to sketch on. This tutorial shows a better route. You ask Claude to slice the scan into cross-sections and hand them to you as an **IGES file**. SolidWorks opens that as real 3D curves (or flat faces), and you build the part on top of them.

The worked example is a scanned car hub cap. The method suits any part you want to rebuild from a scan, especially a part with a lot of curved surface.

You don't need to write or run any code. Everything below is a prompt you paste into Claude and adjust. Anything in **[square brackets]** is the part to change for your own scan.

## What you need

- **A scan of your part** as an STL file.
- **[ScanRuler](https://scanruler.com/)**, a measuring app for 3D scans that runs in your browser.
- **Claude with the ScanRuler MCP connected.** The MCP is what lets Claude drive ScanRuler: cut sections, measure and compare. ScanRuler's *Settings → Agents* page explains how to connect it.
- **[3D Mesh Tools](/tools/3d-mesh-tools/)** (free) to level and centre the scan first. See *Before you start* below.
- **SolidWorks.**

## What you end up with

| File | What it holds |
|---|---|
| `sections_3d.igs` | The cross-sections as closed 3D curves, in their true positions. |
| `section_faces.igs` | The same sections as flat faces, ready to use as profiles (optional). |
| `projected_circles.igs` | Circles of chosen diameters projected onto the top surface (optional). |

All three are in millimetres.

## Before you start: align the scan

Every section is cut through an axis, so the scan needs to be sitting square to it. We aligned the hub cap first in [3D Mesh Tools](/tools/3d-mesh-tools/), then loaded the aligned STL into ScanRuler.

## Step 1: Connect Claude to ScanRuler

Start Claude and ask it to connect:

```
Connect to ScanRuler.
```

Claude opens ScanRuler in your browser and pairs with it. You watch every step in the viewport, and you can undo anything there.

## Step 2: Load the scan and brief Claude

Load your STL in ScanRuler yourself (drag it in, or use the open button). Then tell Claude what the part is and what you want from it. Mention three things: any **symmetry**, what to **ignore**, and your **tolerance**.

```
I've loaded a scan of [a car hub cap]. It has [4-fold] rotational symmetry
about the [Z] axis, so I only need [one eighth of it: the wedge from 0° to 45°].

I'll build the model myself in SolidWorks, so don't try to model it. I only
want section curves out of ScanRuler. Ignore [the lettering, the cross in the
middle and the underside]. I want a tighter tolerance of [±0.1 mm] on [the
front surface].

Before you do anything: read ScanRuler's guides, check the scan quality, and
tell me what you see and what your plan is.
```

Claude reads the scan-to-CAD guide, checks the noise level and holes in the scan, and posts a plan. This is the moment to correct it. In our example it found a clean scan with a noise level of about 0.012 mm, which is why a ±0.1 mm tolerance on the front was realistic.

{% shot "step2-scan-loaded.png", "The hub cap scan loaded in ScanRuler, shown in an isometric view and from above. The top view shows four sloped arms around a round dish with a pinwheel-shaped opening.", "The scan loaded in ScanRuler, from an angle and from above. The four-fold symmetry is easy to see in the top view." %}

**Why symmetry matters.** The hub cap repeats every 90°, and each quarter mirrors itself, so one eighth is all the information there is. You get the other seven in SolidWorks with a mirror and a circular pattern. Fewer sections means less to check.

## Step 3: Cut the sections

```
Cut radial sections through the [Z] axis at [0, 11.25, 22.5, 33.75 and 45]
degrees. Name them S0, S11_25, S22_5, S33_75 and S45. Render each one so I can
see it, and tell me if any outline looks broken: gaps, open loops or noisy
edges.
```

Pick the angles to suit the part. Put sections where the shape changes: at the ends of the wedge (the mirror lines) and in between. For a part that changes quickly, use more sections. Five sections across a 45° wedge was enough for the hub cap.

Each cut is a flat plane through the Z axis, turned to the angle you ask for. Claude lays the five planes on the scan, and ScanRuler draws each one in its own colour:

{% shot "step3-section-lines.png", "The scan seen from above and at an angle, with five coloured lines running through the centre. Each line is one section, at 0, 11.25, 22.5, 33.75 and 45 degrees.", "The five section cuts on the scan. Each coloured line is one slice through the middle of the part." %}

Then Claude draws each slice as a flat outline, so you can check it. This is what a good section looks like: a clean closed outline with no gaps or stray points. The part is a thin shell, so the outline follows both the top and the underside of the wall.

{% shot "step3-section-S0.png", "The S0 section: a flat cross-section drawn against a millimetre grid, showing the thin wall of the hub cap, with a flat rim at each side and a shallow dish in the middle.", "Section S0 (0°), drawn on ScanRuler's millimetre grid." %}

{% shot "step3-section-S45.png", "The S45 section: the same kind of cross-section at 45 degrees, where the wall slopes steeply from the rim down to a step near the centre.", "Section S45 (45°). The shape changes a lot between S0 and S45, which is why the angles in between are worth cutting." %}

If Claude reports a broken outline, ask it to re-cut at a slightly different angle.

## Step 4: Export the sections as IGES curves

```
Export all the sections as ONE IGES file, in millimetres. Put each outline in
its true 3D position, rotated around the [Z] axis to its section angle, as a
closed 3D polyline (IGES entity 106) labelled with its angle. Simplify each
outline to within [0.02 mm].

ScanRuler only exports one section at a time as a DXF, so write the IGES file
yourself. Then check it: lines are 80 characters, sequence numbers are right,
every outline is closed. Save it as [~/scan_sections/sections_3d.igs] and tell
me the path.
```

This is what the file holds: the same outlines, now with the scan taken away and each one in its true 3D position around the axis.

{% shot "step4-sections-3d.png", "The five section outlines floating in 3D space, each in a different colour, fanned out around the vertical axis.", "The section outlines on their own, in 3D. These are what you get in SolidWorks." %}

Two things to know:

- **Claude writes this IGES file itself.** ScanRuler's own exports are DXF, STEP, STL and a few others. Claude writes the IGES by generating it, then checks it. That's why the prompt asks for the check.
- **IGES, not Parasolid or a SolidWorks part.** Claude can't create a native `.sldprt`, and it can't write Parasolid reliably without a way to test it. IGES is plain text, and SolidWorks opens it well.

You can add circles that really are circles, such as the walls of a round skirt. Add this to the prompt:

```
Also fit true circles to [the skirt's outer and inner walls and the rim], and
add them to the file as proper circle entities rather than polylines.
```

## Step 5 (optional): Flat faces instead of curves

Closed curves are enough if you plan to sketch from them. If you'd rather have a flat face for each section, ask for faces straight away:

```
Make a second IGES file where each closed section outline is a flat planar
face: a trimmed surface (IGES entity 144 on a 108 plane), one face per
outline. Where an outline sits inside another, make it a hole. Check the file
and save it as [~/scan_sections/section_faces.igs].
```

Without this step, you can get the same result inside SolidWorks by sketching on the imported curves, or by extruding a cut onto a flat surface, and this step saves you that work.

Both the curve file and the face file import cleanly into SolidWorks.

## Step 6 (optional): Project circles onto the surface

Circles projected onto a curved top surface give you guide curves that follow the skin. They're useful for lofts and for checking a shape as it grows.

```
Take circles of diameter [35, 45, 55, 65, 75, 85, 95, 105, 115, 125 and 135]
mm, centred on the [Z] axis. Project each one straight down onto the top
surface of the scan, so that each becomes a 3D curve following the surface
height. Use only the points on the scan that face up.

Write each curve as a cubic B-spline (IGES entity 126), labelled with its
diameter, in ONE IGES file. Tell me how well each curve fits the scan, and
flag any that fit loosely. Save it as
[~/scan_sections/projected_circles.igs].
```

Expect a few loose ones. Where a circle crosses a steep wall, such as the flank of a step, the surface is almost vertical, so the scan points don't pin the curve down. In our example Ø65 and Ø75 were loose and the rest were within about 0.06 mm. Claude should tell you; if it doesn't, ask.

## Step 7: Import into SolidWorks

1. In SolidWorks, choose **File → Open** and set the file type to IGES (`*.igs`).
2. Before you open it, click **Options** and make sure the file's entities are brought in. For the curve files that means the free point and curve entities; for the face file, the surface entities.
3. Set the units to **millimetres** and open the file into a new part.
4. The curves sit around the Z axis in their true positions.

From here you build the part. For the hub cap we revolved the middle, lofted between the sections for the low areas, lofted again for the rest, then mirrored and patterned the one-eighth wedge into the full part. That's the usual order for a part like this: the simple revolved features first, then lofts between the sections, then the symmetry.

<!-- SCREENSHOT: SolidWorks IGES import options dialog -->
<!-- SCREENSHOT: imported section curves around the Z axis -->
<!-- SCREENSHOT: lofted surfaces on the one-eighth wedge, and after mirror/pattern -->

## Step 8 (optional): Check your model against the scan

When you've built a first version, export it from SolidWorks as a mesh (PLY or STL) and ask Claude to compare it with the scan. This tells you where the model is off before you spend more time on it.

```
I've saved my SolidWorks mesh as [model.ply] in [~/scan_sections/]. Load it as
the reference in ScanRuler's Deviation workspace and align it to the scan.
Check the alignment before you trust any numbers, because the automatic
alignment can come out turned 180°. Use a tolerance of [±0.1 mm] with a
colour range of [±0.3 mm].

Then compare [the front surface only], because I haven't modelled the
underside. Tell me what percentage of the points are within tolerance, and
where the biggest errors are.
```

{% shot "scan-vs-model-overlay.png", "Scan and SolidWorks model overlaid in three views. The model sits close to the scan, with the modelled front surface in tan and the scan showing blue where the model stops short.", "The scan (blue) with the SolidWorks model (tan) overlaid, in ScanRuler." %}

{% shot "scan-vs-model-deviation.png", "A deviation map of the model against the scan. Most of the front surface is green and blue, which are close to the scan. Red bands mark the step ring where the model is further off.", "The deviation map. Green and blue are within tolerance; red bands show where the model is off." %}

In our example the dish and arm centres matched well, while the step ring and the tops of the ears were off, and the model stopped short of the rim. That told us exactly where to work next.

## Tips

- **Say what to ignore.** Text, logos and interior detail you'll model by hand just add noise to the sections.
- **Always ask Claude to check the file.** An IGES file that fails to open wastes more time than the check takes.
- **Check the frame.** Claude's section positions come from ScanRuler's coordinates. If your scan isn't aligned to a useful axis, ask Claude to align it first (for example, level the base and centre it on the axis).
- **Let Claude say it's unsure.** If a fit is loose or an outline is broken, the right answer is "re-cut it", not a smoother file.
- **Keep the prompts.** Save the ones that worked. Next time you scan a similar part, you change the brackets and paste.

## Related

- [3D Mesh Tools](/tools/3d-mesh-tools/) tidies, levels and reduces STL scans before you start.
- [3D Mesh Compare](/tools/3d-mesh-compare/) compares two meshes and reports the deviation.
- [Installation guide](/tools/install/)
