---
layout: article.njk
title: "Battery Pack 3D Scan Example | Interactive Model | 3DScanPost"
breadcrumb: "Battery pack"
description: "Rotate and zoom a 3D scan of a power tool battery pack. See how well a laser scan holds fine detail like contact slots and latch edges."
permalink: /examples/battery-pack/
tags:
  - indexable
  - example
threeImportMap: true
parent:
  name: Examples
  url: /examples/
order: 1
card: "A power tool battery pack. Contact slots and latch edges show how well a laser scan holds fine detail."
thumb: /assets/images/examples/battery-pack.webp
thumbAlt: "Wireframe view of a 3D scanned power tool battery pack"
ogImage: /assets/images/og/battery-pack.jpg
ogImageAlt: "Wireframe view of a 3D scanned power tool battery pack"
---

# Battery pack

<p class="not-prose -mt-4 mb-6 text-sm opacity-70">By {{ site.author }}</p>

Drag to rotate, scroll or pinch to zoom, and switch to wireframe to see the mesh itself.

{% set viewerSrc = "/assets/scans/battery.glb" %}{% set viewerScale = 1 %}{% set viewerLabel = "Interactive 3D scan of a battery pack" %}
{% include "mesh-viewer.njk" %}

## What it is

A Milwaukee power tool battery pack, scanned with the laser scanner.

## Why I scanned it

I used this to make an adapter to securely hold spare batteries in my tool box. There are other models available online, but none had sufficient detail around the locking mechanism.

## What the scan shows

It shows how well the scan holds fine detail like the contact slots and latch edges.

Want something like this for your own part? [Request a quote](/quote/), or see how [3D scanning for 3D printing](/3d-scanning-for-3d-printing/) and [reverse engineering](/reverse-engineering-3d-scanning/) work.
