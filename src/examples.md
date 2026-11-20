---
layout: article.njk
title: "3D Scan Examples | Interactive Models | 3DScanPost"
breadcrumb: "Examples"
description: Interactive examples of 3D scans from 3DScanPost. Rotate, zoom and switch between shaded and wireframe views of each mesh.
permalink: /examples/
tags: indexable
threeImportMap: true
---

# 3D Scan Examples

Real scans, straight from the scanner. Drag to rotate, scroll or pinch to zoom, and switch to wireframe to see the mesh itself.

## Battery pack

A power tool battery pack scanned with the laser scanner. It shows how well the scan holds fine detail like the contact slots and latch edges.

<div class="not-prose my-8 overflow-hidden rounded-box border border-base-content/15 bg-base-100" data-mesh-viewer data-src="/assets/scans/battery.glb" data-unit-scale="1">
  <div class="relative h-[460px] cursor-grab active:cursor-grabbing bg-[radial-gradient(color-mix(in_oklab,var(--color-base-content)_14%,transparent)_1px,transparent_1px)] bg-size-[24px_24px] [&_canvas]:block [&_canvas]:h-full [&_canvas]:w-full" data-canvas role="img" aria-label="Interactive 3D scan of a battery pack"><p class="absolute inset-0 m-0 grid place-items-center font-mono text-sm opacity-70" data-status>Loading 3D viewer…</p></div>
  <div class="flex flex-wrap items-center justify-between gap-3 border-t border-base-content/10 px-4 py-3">
    <div class="join" role="group" aria-label="Display mode">
      <button type="button" class="btn btn-sm join-item btn-active" data-mode="shaded" aria-pressed="true">Shaded</button>
      <button type="button" class="btn btn-sm join-item [&:not(.btn-active)]:bg-base-100" data-mode="both" aria-pressed="false">Both</button>
      <button type="button" class="btn btn-sm join-item [&:not(.btn-active)]:bg-base-100" data-mode="wireframe" aria-pressed="false">Wireframe</button>
    </div>
    <span class="font-mono text-xs tracking-wide text-primary" data-readout></span>
  </div>
</div>

## Remote control

A handheld remote, scanned and cleaned up as an STL. The mesh here has been reduced to 120,000 triangles so it loads quickly, and shaded by surface curvature to bring out the buttons and edges.

<div class="not-prose my-8 overflow-hidden rounded-box border border-base-content/15 bg-base-100" data-mesh-viewer data-src="/assets/scans/remote.glb" data-unit-scale="1000">
  <div class="relative h-[460px] cursor-grab active:cursor-grabbing bg-[radial-gradient(color-mix(in_oklab,var(--color-base-content)_14%,transparent)_1px,transparent_1px)] bg-size-[24px_24px] [&_canvas]:block [&_canvas]:h-full [&_canvas]:w-full" data-canvas role="img" aria-label="Interactive 3D scan of a remote control"><p class="absolute inset-0 m-0 grid place-items-center font-mono text-sm opacity-70" data-status>Loading 3D viewer…</p></div>
  <div class="flex flex-wrap items-center justify-between gap-3 border-t border-base-content/10 px-4 py-3">
    <div class="join" role="group" aria-label="Display mode">
      <button type="button" class="btn btn-sm join-item btn-active" data-mode="shaded" aria-pressed="true">Shaded</button>
      <button type="button" class="btn btn-sm join-item [&:not(.btn-active)]:bg-base-100" data-mode="both" aria-pressed="false">Both</button>
      <button type="button" class="btn btn-sm join-item [&:not(.btn-active)]:bg-base-100" data-mode="wireframe" aria-pressed="false">Wireframe</button>
    </div>
    <span class="font-mono text-xs tracking-wide text-primary" data-readout></span>
  </div>
</div>

<script type="module" src="/assets/js/mesh-viewer.js"></script>
