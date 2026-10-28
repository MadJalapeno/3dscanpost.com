#!/usr/bin/env python3
"""
stl_align.py - Level, align, center and scale an STL (also PLY / OBJ).

GUI:
    python stl_align.py [part.stl]

    Right-click (or press P) on the model to pick up to 3 points.
      1 point   -> Origin > Put P1 at origin
      2 points  -> measure; Scale > Set distance (Ctrl+K); Align edge to X/Y (Ctrl+1/2)
      3 points  -> a plane: Level (Ctrl+L), Refine (Ctrl+E), Flip (Ctrl+F),
                   or, on a side face, Align face to X/Y
    Plane > RANSAC (Ctrl+R) finds flat areas automatically; repeat for the next one.
    Every operation accumulates into one 4x4 matrix, saved next to the STL.
    Edit > Undo (Ctrl+Z) steps back through transforms.

Command line (no GUI):
    python stl_align.py part.stl --auto [-o out.stl] [--tol 0.2] [--center xy|xyz]
        RANSAC-finds the largest plane, levels the part on it, saves.
    python stl_align.py hires.stl --apply-matrix part_aligned_matrix.txt [-o out.stl]
        Applies a saved 4x4 transform to another file (e.g. a full-res scan).

Requires: python -m pip install numpy pyvista pyvistaqt pyside6
"""

import argparse
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # reported nicely by _check_deps()
    np = None

# --------------------------------------------------------------------------------------
# Geometry core (no GUI dependencies)
# --------------------------------------------------------------------------------------


def unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    if n < 1e-15:
        raise ValueError("zero-length vector")
    return v / n


def plane_from_points(p1, p2, p3):
    """Plane through three points -> (unit normal, center). Raises if collinear."""
    p1, p2, p3 = (np.asarray(p, float) for p in (p1, p2, p3))
    n = np.cross(p2 - p1, p3 - p1)
    scale = max(np.linalg.norm(p2 - p1), np.linalg.norm(p3 - p1), 1e-12) ** 2
    if np.linalg.norm(n) < 1e-9 * scale:
        raise ValueError("points are (nearly) collinear - pick a wider triangle")
    return unit(n), (p1 + p2 + p3) / 3.0


def fit_plane_lsq(pts):
    """Least-squares plane through points -> (unit normal, centroid, rms residual)."""
    pts = np.asarray(pts, float)
    c = pts.mean(axis=0)
    _, s, vt = np.linalg.svd(pts - c, full_matrices=False)
    n = vt[2]
    rms = s[2] / np.sqrt(len(pts)) if len(pts) else 0.0
    return unit(n), c, rms


def orient_toward(n, center, body_points):
    """Flip n if needed so the bulk of the part is on the +n side of the plane."""
    side = np.mean((np.asarray(body_points) - center) @ n)
    return -n if side < 0 else n


def face_data(mesh):
    """Cell centers, unit cell normals and areas of a PolyData mesh."""
    sized = mesh.compute_cell_sizes(length=False, area=True, volume=False)
    return mesh.cell_centers().points, mesh.cell_normals, np.abs(sized["Area"])


def orient_normal(n, center, mesh, tol, faces=None):
    """
    Choose the sign of the plane normal (= the new +Z).

    If the plane lies on an actual face of the model, use the "lay flat on face"
    convention slicers use: the face's outward normal points down, so the part rests
    on that face. Otherwise (a plane cutting through the part, or a mesh with messy
    normals), put the bulk of the part above the plane.
    """
    cc, cn, area = faces if faces is not None else face_data(mesh)
    on_plane = (np.abs((cc - center) @ n) <= tol) & (np.abs(cn @ n) > 0.9)
    if on_plane.any():
        s = np.sum(area[on_plane] * (cn[on_plane] @ n))
        if abs(s) > 0.5 * area[on_plane].sum():  # normals agree with each other
            return -n if s > 0 else n
    return orient_toward(n, center, mesh.points)


def ransac_plane(points, tol, iterations=1500, sample=40000, seed=None, batch=100):
    """
    Find the plane supported by the most points within +/- tol.
    Returns (normal, center, inlier_mask over `points`) or None.
    """
    pts = np.asarray(points, float)
    if len(pts) < 3:
        return None
    rng = np.random.default_rng(seed)
    score_pts = pts if len(pts) <= sample else pts[rng.choice(len(pts), sample, replace=False)]

    best_count, best = -1, None
    for start in range(0, iterations, batch):
        k = min(batch, iterations - start)
        idx = rng.integers(0, len(score_pts), size=(k, 3))
        a, b, c = score_pts[idx[:, 0]], score_pts[idx[:, 1]], score_pts[idx[:, 2]]
        nrm = np.cross(b - a, c - a)
        lens = np.linalg.norm(nrm, axis=1)
        ok = lens > 1e-12
        if not ok.any():
            continue
        nrm, a = nrm[ok] / lens[ok, None], a[ok]
        d = -np.einsum("ij,ij->i", nrm, a)
        dist = np.abs(score_pts @ nrm.T + d)  # (N, k)
        counts = (dist <= tol).sum(axis=0)
        j = int(np.argmax(counts))
        if counts[j] > best_count:
            best_count, best = counts[j], (nrm[j], d[j])

    if best is None or best_count < 3:
        return None

    # Refine on all points: LSQ fit of inliers, twice (inlier set can shift slightly).
    n, d = best
    for _ in range(2):
        mask = np.abs(pts @ n + d) <= tol
        if mask.sum() < 3:
            break
        n, c, _ = fit_plane_lsq(pts[mask])
        d = -n @ c
    mask = np.abs(pts @ n + d) <= tol
    return n, pts[mask].mean(axis=0), mask


def rotation_to_z(n):
    """Rotation matrix taking unit vector n onto +Z."""
    n = unit(n)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(n, z)
    s = np.linalg.norm(v)
    c = float(n @ z)
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / s**2)


def leveling_transform(n, center, datum=None):
    """
    4x4 matrix that puts the plane (n, center) at Z=0 with n -> +Z.

    datum=None      : rotate about `center`; part keeps roughly its XY position.
    datum=(p1, p2)  : p1 -> origin, and the direction p1->p2 (projected) -> +X.
    """
    R = rotation_to_z(n)
    if datum is not None:
        p1, p2 = (np.asarray(p, float) for p in datum)
        v = R @ (p2 - p1)
        ang = np.arctan2(v[1], v[0])
        ca, sa = np.cos(-ang), np.sin(-ang)
        Rz = np.array([[ca, -sa, 0], [sa, ca, 0], [0, 0, 1.0]])
        R = Rz @ R
        t = -R @ p1
        # Snap p1 exactly onto the plane height (it may sit slightly off a refined plane).
        t[2] = -(R @ center)[2]
    else:
        center = np.asarray(center, float)
        t = -R @ center + np.array([center[0], center[1], 0.0])
    M = np.eye(4)
    M[:3, :3], M[:3, 3] = R, t
    return M


def yaw_transform(direction, axis, pivot):
    """
    4x4 rotation about Z (through `pivot`) that makes the XY projection of `direction`
    parallel to the X or Y axis. Uses the smallest rotation (|angle| <= 90 deg), so the
    part never gets spun around - press the other axis button for a 90 deg change.
    Returns (matrix, angle_degrees).
    """
    dx, dy = float(direction[0]), float(direction[1])
    if np.hypot(dx, dy) < 1e-12:
        raise ValueError("direction is vertical - it has no XY component")
    target = 0.0 if axis.upper() == "X" else np.pi / 2
    delta = target - np.arctan2(dy, dx)
    delta = (delta + np.pi / 2) % np.pi - np.pi / 2
    c, s = np.cos(delta), np.sin(delta)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
    pivot = np.array([pivot[0], pivot[1], 0.0])
    M = np.eye(4)
    M[:3, :3], M[:3, 3] = R, pivot - R @ pivot
    return M, float(np.degrees(delta))


def centering_transform(bounds, mode="xy"):
    """Translate so the bounding-box center is at the origin (XY only, or XYZ)."""
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    t = np.array([-(xmin + xmax) / 2, -(ymin + ymax) / 2,
                  -(zmin + zmax) / 2 if mode == "xyz" else 0.0])
    M = np.eye(4)
    M[:3, 3] = t
    return M


def scale_transform(factor, pivot):
    """Uniform scale about `pivot`."""
    pivot = np.asarray(pivot, float)
    M = np.eye(4)
    M[:3, :3] *= factor
    M[:3, 3] = pivot - factor * pivot
    return M


def tilt_degrees(n):
    return float(np.degrees(np.arccos(np.clip(abs(unit(n)[2]), -1, 1))))


def output_paths(src, out=None):
    src = Path(src)
    stl = Path(out) if out else src.with_name(src.stem + "_aligned.stl")
    return stl, stl.with_name(stl.stem + "_matrix.txt")


def save_matrix(path, M, src):
    header = (
        f"4x4 transform applied to {Path(src).name} by stl_align.py\n"
        "row-major; apply as  p' = M @ [x, y, z, 1]"
    )
    np.savetxt(path, M, fmt="%.12g", header=header)


# --------------------------------------------------------------------------------------
# Command-line modes
# --------------------------------------------------------------------------------------


def run_auto(path, out, tol, center=None):
    import pyvista as pv

    mesh = pv.read(path)
    diag = mesh.length
    tol = tol if tol else diag * 0.003
    res = ransac_plane(mesh.points, tol, seed=0)
    if res is None:
        sys.exit("RANSAC found no plane - try a larger --tol")
    n, c, mask = res
    n = orient_normal(n, c, mesh, tol)
    M = leveling_transform(n, c)
    mesh = mesh.transform(M, inplace=False)
    if center:
        C = centering_transform(mesh.bounds, center)
        mesh = mesh.transform(C, inplace=False)
        M = C @ M
    stl, mtx = output_paths(path, out)
    mesh.save(stl, binary=True)
    save_matrix(mtx, M, path)
    print(f"plane: {mask.sum()} inlier vertices ({100 * mask.mean():.1f}%), tol {tol:.4g}")
    print(f"tilt corrected: {tilt_degrees(n):.3f} deg")
    print(f"saved {stl}\n      {mtx}")


def run_apply_matrix(path, matrix_file, out):
    import pyvista as pv

    M = np.loadtxt(matrix_file)
    if M.shape != (4, 4):
        sys.exit(f"{matrix_file} is not a 4x4 matrix")
    mesh = pv.read(path).transform(M, inplace=False)
    stl, _ = output_paths(path, out)
    mesh.save(stl, binary=True)
    print(f"saved {stl}")


# --------------------------------------------------------------------------------------
# GUI (Qt window with menus, embedding a PyVista 3D view)
# --------------------------------------------------------------------------------------

PICK_COLORS = ["#e6194b", "#3cb44b", "#4363d8"]
APP_NAME = "STL Align"
APP_VERSION = "1.3"
DEFAULT_MODEL_COLOR = "#c9ccd1"

HELP_VIEW = ("<b>View:</b> Rotate = left-drag &nbsp;·&nbsp; Pan = middle-drag or Shift+left-drag"
             " &nbsp;·&nbsp; Zoom = scroll wheel &nbsp;·&nbsp; Roll = Ctrl+left-drag"
             " &nbsp;·&nbsp; Fit to window = Ctrl+0")

QUICK_START = """
<h3>Quick start</h3>
<p><b>Picking points:</b> <b>right-click</b> on the model (or hover over it and press <b>P</b>).
Picks are numbered P1, P2, P3. A 4th pick starts a new set. <b>Esc</b> clears them.</p>
<ol>
<li><b>Level the part</b> - pick 3 points spread out on the face that should sit on the bed,
    or use <i>Plane &gt; Find plane (RANSAC)</i> (Ctrl+R; repeat to cycle through flat areas).
    Optionally <i>Refine</i> (Ctrl+E) to fit the whole face, <i>Flip</i> (Ctrl+F) if the arrow
    points the wrong way, then <i>Plane &gt; Level on plane</i> (Ctrl+L).
    The arrow shows the new +Z: the part ends up on the arrow side.</li>
<li><b>Square it up</b> - pick 2 points along a straight edge (or 3 on a side face) and use
    <i>Align &gt; parallel to X / Y</i> (Ctrl+1 / Ctrl+2). Only rotates about Z, so the level is kept.</li>
<li><b>Scale</b> (optional) - pick 2 points across a known dimension, <i>Scale &gt; Set distance</i>
    (Ctrl+K), type the real value.</li>
<li><b>Set the origin</b> - <i>Origin &gt; Center of extents XY</i> (Ctrl+4) for a part
    centred on 0,0 sitting on Z=0.</li>
<li><b>Save</b> (Ctrl+S) - writes <tt>name_aligned.stl</tt> plus <tt>name_aligned_matrix.txt</tt>,
    the combined 4x4 transform. Apply that to another file with
    <tt>--apply-matrix</tt> (e.g. a full-resolution scan).</li>
</ol>
<p>Every step can be undone with Ctrl+Z. The <i>plane tolerance</i> (Plane menu) is how close,
in model units, a vertex must be to count as on a plane - raise it for noisy scans.</p>
"""

CONTROLS = """
<h3>Mouse</h3>
<table cellpadding="3">
<tr><td>Rotate</td><td>left-drag</td></tr>
<tr><td>Pan</td><td>middle-drag, or Shift + left-drag</td></tr>
<tr><td>Zoom</td><td>scroll wheel</td></tr>
<tr><td>Roll (spin in screen plane)</td><td>Ctrl + left-drag</td></tr>
<tr><td>Pick a point</td><td>right-click on the model, or hover and press P</td></tr>
</table>
<h3>Keyboard</h3>
<table cellpadding="3">
<tr><td>Ctrl+O / Ctrl+S</td><td>Open / Save</td></tr>
<tr><td>Ctrl+Z</td><td>Undo last transform</td></tr>
<tr><td>Esc</td><td>Clear picks</td></tr>
<tr><td>Ctrl+R</td><td>Find plane (RANSAC) - repeat for the next one</td></tr>
<tr><td>Ctrl+E / Ctrl+F</td><td>Refine plane / Flip plane normal</td></tr>
<tr><td>Ctrl+L</td><td>Level on plane</td></tr>
<tr><td>Ctrl+1 / Ctrl+2 / Ctrl+3</td><td>Align to X / Align to Y / Rotate 90&deg;</td></tr>
<tr><td>Ctrl+4 / Ctrl+5</td><td>Origin to center of extents XY / XYZ</td></tr>
<tr><td>Ctrl+K</td><td>Scale so P1-P2 is a typed distance</td></tr>
<tr><td>Ctrl+T</td><td>Set plane tolerance</td></tr>
<tr><td>Ctrl+0</td><td>Fit view</td></tr>
<tr><td>F1</td><td>Quick start</td></tr>
</table>
"""


def build_window_class():
    """Imported lazily so the CLI modes don't need Qt installed."""
    import pyvista as pv
    from pyvistaqt import QtInteractor
    from qtpy import QtCore, QtGui, QtWidgets

    class AlignWindow(QtWidgets.QMainWindow):
        def __init__(self, path=None, out=None):
            super().__init__()
            self.pv = pv
            self.out = out
            self.path = None
            self.mesh = None
            self.resize(1400, 900)
            self.setWindowTitle("STL Align")

            self.settings = QtCore.QSettings("STLAlign", "STLAlign")
            self.model_color = self.settings.value("model_color", DEFAULT_MODEL_COLOR)
            self.tol = None

            central = QtWidgets.QWidget()
            lay = QtWidgets.QVBoxLayout(central)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(0)
            self.p = QtInteractor(central)
            lay.addWidget(self.p.interactor, 1)
            lay.addWidget(self._build_help_strip())
            self.setCentralWidget(central)

            self.p.set_background("#2b2d31", top="#4a4d55")
            self.p.enable_surface_point_picking(
                callback=self.on_pick, show_message=False, show_point=False, left_clicking=False
            )
            try:  # PyVista binds Q to "close the render window" - not wanted inside an app
                self.p.clear_events_for_key("q")
            except Exception:
                pass

            self._build_menus()
            for key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                sc = getattr(QtGui, "QShortcut", None) or QtWidgets.QShortcut
                sc = sc(QtGui.QKeySequence(key), self)
                sc.setContext(QtCore.Qt.ApplicationShortcut)
                sc.activated.connect(self._on_enter)
            self._update_hint()
            if path:
                self.load(path)
            else:
                self.status("File > Open (Ctrl+O) to load an STL.")
                QtCore.QTimer.singleShot(0, self.on_open)

        # ---------------- help strip & menus ----------------

        def _build_help_strip(self):
            frame = QtWidgets.QFrame()
            frame.setStyleSheet(
                "QFrame#strip { background: #1f2023; border-top: 1px solid #3a3c42; }"
                " QLabel { color: #d6d8dc; padding: 2px 10px; }"
                " QPushButton { color: #e8e9eb; background: #3a3c42; border: 1px solid #50535a;"
                "   border-radius: 4px; padding: 5px 12px; }"
                " QPushButton:hover { background: #4a4d55; }"
                " QPushButton[primary='true'] { background: #2e7d32; border-color: #43a047;"
                "   font-weight: bold; }"
                " QPushButton[primary='true']:hover { background: #388e3c; }"
                " QPushButton[save='true'] { background: #1565c0; border-color: #1e88e5;"
                "   font-weight: bold; }"
                " QPushButton:disabled { background: #2b2d31; color: #6b6e75;"
                "   border-color: #3a3c42; }")
            frame.setObjectName("strip")
            v = QtWidgets.QVBoxLayout(frame)
            v.setContentsMargins(0, 4, 0, 6)
            v.setSpacing(2)
            view = QtWidgets.QLabel(HELP_VIEW)
            view.setTextFormat(QtCore.Qt.RichText)
            v.addWidget(view)

            row = QtWidgets.QHBoxLayout()
            row.setContentsMargins(0, 0, 10, 0)
            self.hint_label = QtWidgets.QLabel()
            self.hint_label.setTextFormat(QtCore.Qt.RichText)
            self.hint_label.setWordWrap(True)
            row.addWidget(self.hint_label, 1)
            self.btn_box = QtWidgets.QHBoxLayout()
            self.btn_box.setSpacing(6)
            row.addLayout(self.btn_box)
            sep = QtWidgets.QFrame()
            sep.setFrameShape(QtWidgets.QFrame.VLine)
            sep.setStyleSheet("color: #3a3c42;")
            row.addSpacing(8)
            row.addWidget(sep)
            self.save_label = QtWidgets.QLabel()
            self.save_label.setTextFormat(QtCore.Qt.RichText)
            row.addWidget(self.save_label)
            self.save_btn = QtWidgets.QPushButton("Save  (Ctrl+S)")
            self.save_btn.setProperty("save", True)
            self.save_btn.clicked.connect(self.on_save)
            self.save_btn.setToolTip("Writes <name>_aligned.stl and <name>_aligned_matrix.txt")
            row.addWidget(self.save_btn)
            v.addLayout(row)
            return frame

        def _set_buttons(self, specs):
            """specs: list of (label, slot, primary?, tooltip)."""
            while self.btn_box.count():
                w = self.btn_box.takeAt(0).widget()
                if w:
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()
            for label, slot, primary, tip in specs:
                b = QtWidgets.QPushButton(label)
                b.setProperty("primary", bool(primary))
                if tip:
                    b.setToolTip(tip)
                b.setFocusPolicy(QtCore.Qt.NoFocus)
                b.clicked.connect(lambda _=False, f=slot: f())
                self.btn_box.addWidget(b)

        def _dirty(self):
            return self.mesh is not None and not np.allclose(self.M_total, self.saved_M)

        def _update_hint(self, extra=None):
            """Bottom strip: what to do next, buttons to do it, and the save state."""
            k = "<span style='color:#f5c542'><b>%s</b></span>"
            cancel = ("Cancel  (Esc)", self.on_clear, False, "Discard the picks / preview")
            if self.mesh is None:
                t = "<b>Start:</b> open an STL, PLY or OBJ file."
                b = [("Open...  (Ctrl+O)", self.on_open, True, None)]
            elif self.plane is not None:
                t = (k % "Preview only - not applied yet." + " Yellow = the plane, arrow = the new +Z"
                     " (the part ends up on the arrow side). Press " + k % "Level" + " to apply it.")
                b = [("\u2714  Level on this plane  (Enter)", self.on_apply, True,
                      "Rotate and move the part so this plane becomes Z=0"),
                     ("Flip", self.on_flip, False, "Swap which side the part ends up on (Ctrl+F)"),
                     ("Refine", self.on_refine, False,
                      "Least-squares fit to the whole face for better accuracy (Ctrl+E)")]
                if np.hypot(*self.plane[0][:2]) > 0.9:  # a side face: offer axis alignment
                    b += [("Align face to X", lambda: self.on_align_axis("X"), False, None),
                          ("Align face to Y", lambda: self.on_align_axis("Y"), False, None)]
                b.append(cancel)
            elif len(self.picks) == 0:
                t = ("<b>Pick points:</b> " + k % "right-click on the model"
                     + " (or hover and press P). &nbsp;3 points = a plane to level on"
                     " &nbsp;·&nbsp; 2 points = an edge to align, or a distance to scale.")
                b = [("Find plane automatically", self.on_ransac, False,
                      "RANSAC: find the largest flat area; press again for the next one (Ctrl+R)")]
            elif len(self.picks) == 1:
                t = "<b>P1 picked.</b> Right-click P2 for an edge or distance, or two more for a plane."
                b = [("Put P1 at origin", self.on_p1_origin, False, None), cancel]
            else:
                d = np.linalg.norm(self.picks[1] - self.picks[0])
                t = (f"<b>P1-P2 = {d:.4f}.</b> Choose what to do with it, or right-click P3"
                     " for a plane.")
                b = [("Scale to distance...", self.on_scale_distance, False,
                      "Type what P1-P2 should measure; the part scales to match (Ctrl+K)"),
                     ("Align edge to X", lambda: self.on_align_axis("X"), False, "Ctrl+1"),
                     ("Align edge to Y", lambda: self.on_align_axis("Y"), False, "Ctrl+2"),
                     cancel]
            self.hint_label.setText(t)
            self._set_buttons(b)

            dirty = self._dirty()
            n = len(getattr(self, "history", []))
            if self.mesh is None:
                self.save_label.setText("")
            elif dirty:
                self.save_label.setText("<span style='color:#ffb74d'>\u25cf Changes applied, not"
                                        " saved</span>")
            elif n:
                self.save_label.setText("<span style='color:#81c784'>\u2714 Saved</span>")
            else:
                self.save_label.setText("<span style='color:#9a9da3'>No changes yet</span>")
            self.save_btn.setEnabled(dirty)
            if self.mesh is not None:
                self.setWindowTitle(f"{APP_NAME} - {Path(self.path).name}{' *' if dirty else ''}")

        def _on_enter(self):
            if self.mesh is not None and self.plane is not None:
                self.on_apply()

        def _act(self, menu, text, slot, shortcut=None, checkable=False, tip=None):
            a = QtGui.QAction(text, self)
            if shortcut:
                a.setShortcut(QtGui.QKeySequence(shortcut))
                a.setShortcutContext(QtCore.Qt.ApplicationShortcut)
            if tip:
                a.setToolTip(tip)
            a.setCheckable(checkable)
            if checkable:
                a.toggled.connect(slot)
            else:
                a.triggered.connect(lambda _=False: slot())
            menu.addAction(a)
            return a

        def _menu(self, title):
            m = self.menuBar().addMenu(title)
            m.setToolTipsVisible(True)
            return m

        def _build_menus(self):
            m = self._menu("&File")
            self._act(m, "&Open...", self.on_open, "Ctrl+O")
            self._act(m, "&Save", self.on_save, "Ctrl+S",
                      tip="Writes <name>_aligned.stl and <name>_aligned_matrix.txt")
            self._act(m, "Save &As...", self.on_save_as, "Ctrl+Shift+S")
            m.addSeparator()
            self._act(m, "&Quit", self.close, "Ctrl+Q")

            m = self._menu("&Edit")
            self._act(m, "&Undo last transform", self.on_undo, "Ctrl+Z")
            self._act(m, "&Reset to original", self.on_reset)
            m.addSeparator()
            self._act(m, "&Clear picks", self.on_clear, "Esc")

            m = self._menu("&Plane")
            self._act(m, "Find plane (&RANSAC) - repeat for next", self.on_ransac, "Ctrl+R",
                      tip="Auto-find the largest flat area; run again for the next-largest")
            self._act(m, "R&efine fit to nearby surface", self.on_refine, "Ctrl+E",
                      tip="Least-squares fit to every vertex near the plane - more accurate than 3 picks")
            self._act(m, "&Flip normal", self.on_flip, "Ctrl+F",
                      tip="Swap which side of the plane the part ends up on")
            m.addSeparator()
            self._act(m, "&Level on plane", self.on_apply, "Ctrl+L", tip="Make the current plane Z=0")
            self.datum_action = self._act(
                m, "&Datum mode (P1 = origin, P1->P2 = +X)", self.on_datum, checkable=True,
                tip="When levelling on 3 picked points, also fix the origin and X direction")
            m.addSeparator()
            self.tol_action = self._act(m, "Plane &tolerance...", self.on_set_tol, "Ctrl+T",
                                        tip="How close (model units) a vertex must be to count as"
                                            " on the plane. Raise it for noisy scans.")

            m = self._menu("&Align")
            self._act(m, "Edge/face parallel to &X", lambda: self.on_align_axis("X"), "Ctrl+1",
                      tip="Use 2 picks along an edge, or a plane on a side face")
            self._act(m, "Edge/face parallel to &Y", lambda: self.on_align_axis("Y"), "Ctrl+2",
                      tip="Use 2 picks along an edge, or a plane on a side face")
            self._act(m, "Rotate &90 deg about Z", self.on_rot90, "Ctrl+3")

            m = self._menu("&Origin")
            self._act(m, "Center of extents - &XY (keep Z=0)", lambda: self.on_center("xy"), "Ctrl+4")
            self._act(m, "Center of extents - XY&Z", lambda: self.on_center("xyz"), "Ctrl+5")
            self._act(m, "Put &P1 at origin", self.on_p1_origin)

            m = self._menu("&Scale")
            self._act(m, "Set &distance P1-P2...", self.on_scale_distance, "Ctrl+K",
                      tip="Pick 2 points, then type what that distance should be")
            self._act(m, "Scale by &factor...", self.on_scale_factor)
            m.addSeparator()
            self._act(m, "&Inches -> mm (x25.4)", lambda: self._scale(25.4, "inches -> mm"))
            self._act(m, "&mm -> inches (/25.4)", lambda: self._scale(1 / 25.4, "mm -> inches"))

            m = self._menu("&View")
            self._act(m, "&Fit to window", lambda: self.p.reset_camera(), "Ctrl+0")
            self._act(m, "&Top (looking down Z)", lambda: self.p.view_xy())
            self._act(m, "&Front (looking along Y)", lambda: self.p.view_xz())
            self._act(m, "&Right (looking along X)", lambda: self.p.view_yz())
            self._act(m, "&Isometric", lambda: self.p.view_isometric())
            m.addSeparator()
            self._act(m, "Model &colour...", self.on_model_color)
            self._act(m, "Reset model colour", lambda: self._set_model_color(DEFAULT_MODEL_COLOR))

            m = self._menu("&Help")
            self._act(m, "&Quick start", self.on_quick_start, "F1")
            self._act(m, "Mouse && &keyboard controls", self.on_controls)
            m.addSeparator()
            self._act(m, f"&About {APP_NAME}", self.on_about)

        def _info_box(self, title, html):
            box = QtWidgets.QMessageBox(self)
            box.setWindowTitle(title)
            box.setTextFormat(QtCore.Qt.RichText)
            box.setText(html)
            box.setStandardButtons(QtWidgets.QMessageBox.Ok)
            box.exec_() if hasattr(box, "exec_") else box.exec()

        def on_quick_start(self):
            self._info_box(f"{APP_NAME} - Quick start", QUICK_START)

        def on_controls(self):
            self._info_box(f"{APP_NAME} - Controls", CONTROLS)

        def on_about(self):
            import platform
            import vtk
            from qtpy import API_NAME, QT_VERSION

            html = (f"<h2>{APP_NAME} {APP_VERSION}</h2>"
                    "<p>Level, square up, scale and re-origin STL / PLY / OBJ meshes - built for"
                    " tidying up 3D scans before CAD or printing.</p>"
                    "<p>Plane from 3 picked points or RANSAC, least-squares refinement, edge/face"
                    " alignment, distance-based scaling, and a saved 4x4 transform that can be"
                    " re-applied to other files.</p>"
                    f"<p style='color:gray'>Python {platform.python_version()} &nbsp;·&nbsp; "
                    f"PyVista {pv.__version__} &nbsp;·&nbsp; VTK {vtk.vtkVersion.GetVTKVersion()}"
                    f" &nbsp;·&nbsp; {API_NAME} / Qt {QT_VERSION} &nbsp;·&nbsp; NumPy {np.__version__}</p>")
            QtWidgets.QMessageBox.about(self, f"About {APP_NAME}", html)

        def on_model_color(self):
            c = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.model_color), self, "Model colour")
            if c.isValid():
                self._set_model_color(c.name())

        def _set_model_color(self, color):
            self.model_color = color
            self.settings.setValue("model_color", color)
            if getattr(self, "mesh_actor", None) is not None:
                self.mesh_actor.prop.color = color
                self.p.render()

        # ---------------- loading / state ----------------

        def load(self, path):
            mesh = pv.read(path)
            if not isinstance(mesh, pv.PolyData):
                mesh = mesh.extract_surface()
            if not mesh.is_all_triangles:
                mesh = mesh.triangulate()
            self.path = path
            self.original = mesh
            self.mesh = mesh.copy()
            self.diag = self.mesh.length
            self.M_total = np.eye(4)
            self.history = []
            self.saved_M = np.eye(4)
            self.picks, self.plane, self.plane_source = [], None, ""
            self.ransac_excluded, self._faces = None, None
            self._set_tol(self.diag * 0.003)

            self.p.clear()
            self.p.enable_lightkit()  # clear() also removes the default lights
            self.p.add_axes(viewport=(0.9, 0.0, 1.0, 0.12))
            self.mesh_actor = self.p.add_mesh(self.mesh, color=self.model_color, specular=0.3,
                                              name="mesh")
            self.p.reset_camera()
            self.setWindowTitle(f"{APP_NAME} - {Path(path).name}")
            self.status("Loaded.")
            self._update_hint()

        def _need_mesh(self):
            if self.mesh is None:
                self.status("Open a file first (Ctrl+O).")
                return True
            return False

        def _orient(self, n, c):
            if self._faces is None:
                self._faces = face_data(self.mesh)
            return orient_normal(n, c, self.mesh, max(self.tol, self.diag * 0.002), self._faces)

        def status(self, msg):
            if self.mesh is not None:
                bb = self.mesh.bounds
                info = (f"{Path(self.path).name}   {self.mesh.n_cells:,} triangles   "
                        f"size {bb[1] - bb[0]:.4g} x {bb[3] - bb[2]:.4g} x {bb[5] - bb[4]:.4g}")
            else:
                info = "No file loaded"
            self.p.add_text(f"{info}\n{msg}", position="upper_left", font_size=10,
                            color="white", name="status")
            if hasattr(self, "hint_label"):
                self._update_hint()

        # ---------------- drawing ----------------

        def _clear_overlays(self):
            for name in ("plane", "normal", "inliers", "picklabels", "measure"):
                self.p.remove_actor(name)
            for i in range(3):
                self.p.remove_actor(f"pick{i}")

        def _draw_picks(self):
            r = self.diag * 0.006
            for i, pt in enumerate(self.picks):
                self.p.add_mesh(pv.Sphere(radius=r, center=pt), color=PICK_COLORS[i],
                                name=f"pick{i}", pickable=False)
            if self.picks:
                self.p.add_point_labels(
                    np.array(self.picks), [f"P{i + 1}" for i in range(len(self.picks))],
                    font_size=14, text_color="white", shape_opacity=0.5, name="picklabels",
                    always_visible=True, show_points=False, pickable=False)
            if len(self.picks) >= 2:
                self.p.add_mesh(pv.Line(self.picks[0], self.picks[1]), color="#ffffff",
                                line_width=2, name="measure", pickable=False)

        def _draw_plane(self, inlier_pts=None):
            n, c = self.plane
            size = self.diag * 0.7
            self.p.add_mesh(pv.Plane(center=c, direction=n, i_size=size, j_size=size),
                            color="#f5c542", opacity=0.35, name="plane", pickable=False)
            self.p.add_mesh(pv.Arrow(start=c, direction=n, scale=self.diag * 0.25),
                            color="#f5c542", name="normal", pickable=False)
            if inlier_pts is not None and len(inlier_pts):
                if len(inlier_pts) > 60000:
                    inlier_pts = inlier_pts[
                        np.random.default_rng(0).choice(len(inlier_pts), 60000, False)]
                self.p.add_mesh(pv.PolyData(inlier_pts), color="#33d17a", point_size=3,
                                name="inliers", pickable=False)
            else:
                self.p.remove_actor("inliers")

        def _draw_ground(self):
            bb = self.mesh.bounds
            span = max(bb[1] - bb[0], bb[3] - bb[2]) * 1.3
            cx, cy = (bb[0] + bb[1]) / 2, (bb[2] + bb[3]) / 2
            grid = pv.Plane(center=(cx, cy, 0), direction=(0, 0, 1), i_size=span, j_size=span,
                            i_resolution=20, j_resolution=20)
            self.p.add_mesh(grid, style="wireframe", color="#8a8f99", opacity=0.5,
                            name="ground", pickable=False)
            L = self.mesh.length * 0.12
            for ax, vec, col in (("x", (L, 0, 0), "#ff5555"), ("y", (0, L, 0), "#55dd55"),
                                 ("z", (0, 0, L), "#5599ff")):
                self.p.add_mesh(pv.Line((0, 0, 0), vec), color=col, line_width=5,
                                name=f"origin_{ax}", pickable=False)

        def _plane_summary(self):
            n, c = self.plane
            near = np.abs((self.mesh.points - c) @ n) <= self.tol
            return (f"{self.plane_source}: tilt from horizontal {tilt_degrees(n):.3f} deg, "
                    f"{near.sum():,} vertices within tol.\n"
                    "Arrow = new +Z: the part will sit on the arrow side (Ctrl+F to flip).")

        # ---------------- transforms ----------------

        def _apply(self, M, reset_view=False):
            """Transform the mesh, accumulate the matrix and refresh the scene."""
            self.history.append(self.M_total.copy())
            self.mesh.transform(M, inplace=True)
            self.M_total = M @ self.M_total
            self.diag = self.mesh.length
            self.picks, self.plane, self.ransac_excluded, self._faces = [], None, None, None
            self._clear_overlays()
            self._draw_ground()
            if reset_view:
                self.p.reset_camera()
                self.p.view_isometric()
            else:
                self.p.render()

        def _set_total(self, M_total):
            self.mesh.copy_from(self.original.transform(M_total, inplace=False))
            self.M_total = M_total
            self.diag = self.mesh.length
            self.picks, self.plane, self.ransac_excluded, self._faces = [], None, None, None
            self._clear_overlays()

        def _pivot(self):
            """Scale/rotate about the XY center of the part at Z=0 so a levelled base stays put."""
            bb = self.mesh.bounds
            return np.array([(bb[0] + bb[1]) / 2, (bb[2] + bb[3]) / 2, 0.0])

        # ---------------- callbacks: picking & plane ----------------

        def on_pick(self, point):
            if point is None or self.mesh is None:
                return
            if len(self.picks) == 3:
                self.picks, self.plane = [], None
                self._clear_overlays()
            self.picks.append(np.asarray(point, float))
            self._draw_picks()
            if len(self.picks) == 1:
                return self.status("Picked P1. Pick 2 more for a plane, or 1 more for an edge/distance.")
            if len(self.picks) == 2:
                d = self.picks[1] - self.picks[0]
                return self.status(
                    f"P1-P2 distance {np.linalg.norm(d):.4f}  (dx {abs(d[0]):.4f}, dy {abs(d[1]):.4f},"
                    f" dz {abs(d[2]):.4f})")
            try:
                n, c = plane_from_points(*self.picks)
            except ValueError as e:
                return self.status(str(e))
            self.plane, self.plane_source = (self._orient(n, c), c), "3-point plane"
            self._draw_plane()
            self.status(self._plane_summary())

        def on_clear(self):
            if self._need_mesh():
                return
            self.picks, self.plane = [], None
            self._clear_overlays()
            self.status("Cleared. Pick points, or Plane > RANSAC.")

        def on_flip(self):
            if self.mesh is None or self.plane is None:
                return self.status("No plane yet.")
            n, c = self.plane
            self.plane = (-n, c)
            self._draw_plane()
            self.status("Flipped. " + self._plane_summary())

        def on_ransac(self):
            if self._need_mesh():
                return
            pts = self.mesh.points
            if self.ransac_excluded is None or len(self.ransac_excluded) != len(pts):
                self.ransac_excluded = np.zeros(len(pts), bool)
            avail = ~self.ransac_excluded
            if avail.sum() < 3:
                self.ransac_excluded[:] = False
                avail[:] = True
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                res = ransac_plane(pts[avail], self.tol)
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()
            if res is None or res[2].sum() < 10:
                self.ransac_excluded[:] = False
                return self.status("No further plane found - cycled back. Run RANSAC again.")
            n, c, mask_sub = res
            idx = np.flatnonzero(avail)[mask_sub]
            self.ransac_excluded[idx] = True
            self.picks = []
            self._clear_overlays()
            self.plane, self.plane_source = (self._orient(n, c), c), "RANSAC plane"
            self._draw_plane(pts[idx])
            rms = fit_plane_lsq(pts[idx])[2]
            self.status(self._plane_summary() + f"  RMS {rms:.4g}"
                        "\nGreen = supporting vertices. Ctrl+R again for the next-largest plane.")

        def on_refine(self):
            if self.mesh is None or self.plane is None:
                return self.status("No plane yet.")
            n0, c0 = self.plane
            pts = self.mesh.points
            near = np.abs((pts - c0) @ n0) <= self.tol
            if near.sum() < 3:
                return self.status("Too few vertices within tolerance - raise it (Plane > Plane"
                                   " tolerance, Ctrl+T).")
            sel = pts[near]
            if self.picks:
                radius = max(np.linalg.norm(p - c0) for p in self.picks) * 1.5 + self.tol
                local = sel[np.linalg.norm(sel - c0, axis=1) <= radius]
                if len(local) >= 3:
                    sel = local
            n, c, rms = fit_plane_lsq(sel)
            if n @ n0 < 0:
                n = -n
            change = np.degrees(np.arccos(np.clip(n @ n0, -1, 1)))
            self.plane, self.plane_source = (n, c), "Refined plane"
            self._draw_plane(sel)
            self.status(self._plane_summary() + f"\nRefit on {len(sel):,} vertices, RMS {rms:.4g},"
                        f" normal moved {change:.3f} deg.")

        def on_datum(self, state):
            self.status(f"Datum mode {'ON: P1 -> origin, P1->P2 -> +X' if state else 'OFF'}"
                        " (applies when levelling a 3-point plane).")

        def _set_tol(self, value):
            self.tol = float(value)
            self.tol_action.setText(f"Plane &tolerance... (now {self.tol:.4g})")

        def on_set_tol(self):
            if self._need_mesh():
                return
            val, ok = QtWidgets.QInputDialog.getDouble(
                self, "Plane tolerance",
                "How close (model units) a vertex must be to count as on the plane.\n"
                f"Default for this part: {self.diag * 0.003:.4g}. Raise it for noisy scans.",
                self.tol, self.diag * 1e-6, self.diag, 4)
            if ok and val > 0:
                self._set_tol(val)
                self.status(f"Plane tolerance set to {val:.4g}.")

        def on_apply(self):
            if self.mesh is None or self.plane is None:
                return self.status("No plane yet - pick 3 points or run RANSAC.")
            n, c = self.plane
            datum = None
            if self.datum_action.isChecked() and len(self.picks) == 3:
                datum = (self.picks[0], self.picks[1])
            tilt = tilt_degrees(n)
            self._apply(leveling_transform(n, c, datum), reset_view=True)
            self.status(f"Levelled: corrected {tilt:.3f} deg of tilt{' with datum' if datum else ''}."
                        " Plane is now Z=0.\nNext: align an edge or side face to X/Y, center,"
                        " or scale.")

        # ---------------- callbacks: align / origin ----------------

        def on_align_axis(self, axis):
            if self._need_mesh():
                return
            if self.plane is not None:
                n = self.plane[0]
                if np.hypot(n[0], n[1]) < 0.17:
                    return self.status("That face is (nearly) horizontal, so it can't set a"
                                       " direction. Use a side face, or 2 points along an edge.")
                note = (f"  (face is {90 - tilt_degrees(n):.1f} deg off vertical; only its heading"
                        " was used)") if abs(n[2]) > 0.26 else ""
                direction, what = np.array([n[1], -n[0], 0.0]), "Face"
            elif len(self.picks) == 2:
                direction = self.picks[1] - self.picks[0]
                if np.hypot(direction[0], direction[1]) < self.diag * 1e-4:
                    return self.status("P1 and P2 are stacked vertically - pick along a"
                                       " horizontal edge.")
                note, what = "", "Edge P1->P2"
            else:
                return self.status(f"To align to {axis}: pick 2 points along an edge, or make a"
                                   " plane on a side face (3 picks / RANSAC).")
            M, ang = yaw_transform(direction, axis, self._pivot())
            self._apply(M)
            self.status(f"{what} is now parallel to {axis} (rotated {ang:+.3f} deg about Z).{note}")

        def on_rot90(self):
            if self._need_mesh():
                return
            M, _ = yaw_transform([0.0, -1.0, 0.0], "X", self._pivot())  # +90 deg
            self._apply(M)
            self.status("Rotated 90 deg about Z.")

        def on_center(self, mode):
            if self._need_mesh():
                return
            M = centering_transform(self.mesh.bounds, mode)
            t = M[:3, 3] + 0.0
            self._apply(M)
            where = ("center of extents is at 0,0,0" if mode == "xyz"
                     else "XY center of extents is at 0,0 (Z unchanged)")
            self.status(f"Moved by ({t[0]:.4g}, {t[1]:.4g}, {t[2]:.4g}): {where}.")

        def on_p1_origin(self):
            if self._need_mesh():
                return
            if not self.picks:
                return self.status("Pick a point first.")
            M = np.eye(4)
            M[:3, 3] = -self.picks[0]
            self._apply(M)
            self.status("P1 is now at 0,0,0.")

        # ---------------- callbacks: scale ----------------

        def _scale(self, factor, label):
            if self._need_mesh():
                return
            self._apply(scale_transform(factor, self._pivot()))
            self.p.reset_camera()
            self.status(f"Scaled x{factor:.6g} ({label}). Scaled about the part's XY center at Z=0,"
                        " so a levelled base stays on Z=0.")

        def on_scale_distance(self):
            if self._need_mesh():
                return
            if len(self.picks) < 2:
                return self.status("Pick 2 points first (right-click or P), then Scale > Set"
                                   " distance (Ctrl+K).")
            cur = float(np.linalg.norm(self.picks[1] - self.picks[0]))
            if cur <= 0:
                return self.status("P1 and P2 are the same point.")
            val, ok = QtWidgets.QInputDialog.getDouble(
                self, "Scale to distance",
                f"Current P1-P2 distance: {cur:.4f}\nNew distance:", cur, 1e-9, 1e9, 4)
            if not ok or val <= 0:
                return
            self._scale(val / cur, f"P1-P2 {cur:.4f} -> {val:.4f}")

        def on_scale_factor(self):
            if self._need_mesh():
                return
            val, ok = QtWidgets.QInputDialog.getDouble(
                self, "Scale by factor", "Uniform scale factor:", 1.0, 1e-9, 1e9, 6)
            if ok and val > 0 and val != 1.0:
                self._scale(val, "by factor")

        # ---------------- callbacks: file / edit ----------------

        def _confirm_discard(self):
            """True if it's OK to throw away the current (unsaved) result."""
            if not self._dirty():
                return True
            r = QtWidgets.QMessageBox.question(
                self, APP_NAME, "The aligned part hasn't been saved. Save it first?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard
                | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Save)
            if r == QtWidgets.QMessageBox.Save:
                self.on_save()
                return True
            return r == QtWidgets.QMessageBox.Discard

        def on_open(self):
            if not self._confirm_discard():
                return
            f, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open mesh", "", "Meshes (*.stl *.ply *.obj);;All files (*)")
            if f:
                try:
                    self.load(f)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Could not open", str(e))

        def _write(self, stl):
            stl = Path(stl)
            mtx = stl.with_name(stl.stem + "_matrix.txt")
            self.mesh.save(stl, binary=True)
            save_matrix(mtx, self.M_total, self.path)
            self.saved_M = self.M_total.copy()
            self.status(f"Saved {stl.name} and {mtx.name} in {stl.parent}")

        def on_save(self):
            if self._need_mesh():
                return
            self._write(output_paths(self.path, self.out)[0])

        def on_save_as(self):
            if self._need_mesh():
                return
            default = str(output_paths(self.path, self.out)[0])
            f, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save STL", default, "STL (*.stl)")
            if f:
                self._write(f if f.lower().endswith(".stl") else f + ".stl")

        def on_undo(self):
            if self._need_mesh():
                return
            if not self.history:
                return self.status("Nothing to undo.")
            self._set_total(self.history.pop())
            if self.history:
                self._draw_ground()
            else:
                for name in ("ground", "origin_x", "origin_y", "origin_z"):
                    self.p.remove_actor(name)
            self.p.render()
            self.status(f"Undone. {len(self.history)} transform(s) remain.")

        def on_reset(self):
            if self._need_mesh():
                return
            self.history = []
            self._set_total(np.eye(4))
            for name in ("ground", "origin_x", "origin_y", "origin_z"):
                self.p.remove_actor(name)
            self.p.reset_camera()
            self.status("Reset to original.")

        def closeEvent(self, event):
            if not self._confirm_discard():
                event.ignore()
                return
            self.p.close()
            super().closeEvent(event)

    return AlignWindow


def run_gui(path, out):
    from qtpy import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win = build_window_class()(path, out)
    win.show()
    return app.exec_() if hasattr(app, "exec_") else app.exec()


def main():
    ap = argparse.ArgumentParser(description="Level, align, center and scale an STL.")
    ap.add_argument("stl", nargs="?", help="input mesh (STL/PLY/OBJ)")
    ap.add_argument("-o", "--out", help="output STL path (default <name>_aligned.stl)")
    ap.add_argument("--auto", action="store_true", help="no GUI: RANSAC largest plane and save")
    ap.add_argument("--tol", type=float, help="plane tolerance in model units (--auto)")
    ap.add_argument("--center", choices=["xy", "xyz"],
                    help="(--auto) move the bounding-box center to the origin")
    ap.add_argument("--apply-matrix", metavar="TXT", help="no GUI: apply a saved 4x4 matrix")
    args = ap.parse_args()

    if args.apply_matrix or args.auto:
        if not args.stl:
            ap.error("an input file is required with --auto / --apply-matrix")
        if args.apply_matrix:
            return run_apply_matrix(args.stl, args.apply_matrix, args.out)
        return run_auto(args.stl, args.out, args.tol, args.center)
    return run_gui(args.stl, args.out)


def _pause(msg="\nPress Enter to close..."):
    """Keep a double-clicked console window open so errors can be read."""
    try:
        input(msg)
    except Exception:
        pass


def _check_deps():
    missing = []
    for mod in ("numpy", "pyvista", "pyvistaqt", "qtpy"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    try:
        import qtpy  # noqa: F401  (raises if no Qt binding is installed)
    except Exception:
        missing.append("pyside6")
    if missing:
        print("Missing Python packages for this Python:\n  " + sys.executable + "\n\n"
              "Install them with:\n  \"" + sys.executable + "\" -m pip install "
              "numpy pyvista pyvistaqt pyside6")
        _pause()
        sys.exit(1)


if __name__ == "__main__":
    try:
        _check_deps()
        sys.exit(main())
    except SystemExit as e:
        if e.code not in (0, None):
            _pause()
        raise
    except Exception:
        import traceback

        traceback.print_exc()
        _pause()
        sys.exit(1)