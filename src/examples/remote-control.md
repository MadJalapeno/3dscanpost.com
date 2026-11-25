---
layout: article.njk
title: "Remote Control 3D Scan Example | Interactive Model | 3DScanPost"
breadcrumb: "Remote control"
description: "Rotate and zoom a 3D scan of a handheld remote, cleaned up as an STL and shaded by curvature to bring out the buttons and edges."
permalink: /examples/remote-control/
tags:
  - indexable
  - example
threeImportMap: true
parent:
  name: Examples
  url: /examples/
order: 2
card: "A handheld remote, cleaned up as an STL and shaded by curvature to bring out the buttons and edges."
thumb: /assets/images/examples/remote-control.webp
thumbAlt: "Wireframe view of a 3D scanned remote control"
ogImage: /assets/images/og/remote-control.jpg
ogImageAlt: "Wireframe view of a 3D scanned remote control"
---

# Remote control

<p class="not-prose -mt-4 mb-6 text-sm opacity-70">By {{ site.author }}</p>

Drag to rotate, scroll or pinch to zoom, and switch to wireframe to see the mesh itself.

{% set viewerSrc = "/assets/scans/remote.glb" %}{% set viewerScale = 1000 %}{% set viewerLabel = "Interactive 3D scan of a remote control" %}
{% include "mesh-viewer.njk" %}

## What it is

A handheld remote, scanned and cleaned up as an STL.

## Why I scanned it

Remotes are getting smaller, thinner and easier to lose. I used this scan to make a mold to cast a silicone cover in a bright color, which has the added bonus of being less likely to slide down the side of the couch.

## About this model

The mesh here has been reduced to 120,000 triangles so it loads quickly, and shaded by surface curvature to bring out the buttons and edges.

Want something like this for your own part? [Request a quote](/quote/), or see how [3D scanning for 3D printing](/3d-scanning-for-3d-printing/) and [reverse engineering](/reverse-engineering-3d-scanning/) work.
