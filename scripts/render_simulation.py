"""
3D mission visualization — renders drone flight as a proper 3D simulation video.
No GPU required: uses matplotlib Agg backend, renders frame-by-frame to MP4.
"""

import json, math, sys
from pathlib import Path

import numpy as np

matplotlib = __import__("matplotlib", fromlist=["use"])
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
import matplotlib.patheffects as pe
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

MISSION_PATH = "/workspace/config/perimeter_loop.json"
OUTPUT_PATH = "/workspace/output/demo/demo_simulation.mp4"
FPS = 30
DURATION_PER_WP = 2.5
PAUSE_AT_WP = 0.8


def load_mission(path):
    with open(path) as f:
        data = json.load(f)
    wps = data.get("waypoints", data.get("actions", []))
    if wps and isinstance(wps[0], dict) and "action" in wps[0]:
        wps = [w for w in wps if w["action"] in ("GOTO", "TAKEOFF", "LAND")]
    return wps


def interpolate_3d(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def build_progress_bar(pct, width=30):
    filled = int(pct * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {int(pct * 100)}%"


def main():
    plt.rcParams.update({
        "font.size": 11,
        "font.family": "monospace",
        "axes.facecolor": "#0a0a14",
        "figure.facecolor": "#0a0a14",
    })

    wps = load_mission(MISSION_PATH)
    if not wps:
        print("No waypoints found in mission file")
        sys.exit(1)

    print(f"Loaded {len(wps)} waypoints from {MISSION_PATH}")
    for i, wp in enumerate(wps):
        print(f"  WP{i}: {wp}")

    waypoints = []
    for wp in wps:
        alt = float(wp.get("altitude", wp.get("z", 10)))
        x_val = float(wp.get("latitude", wp.get("x", wp.get("waypoint", {}).get("x", 0))))
        y_val = float(wp.get("longitude", wp.get("y", wp.get("waypoint", {}).get("y", 0))))
        if wp.get("action") == "TAKEOFF":
            z = 0
        else:
            z = -alt
        waypoints.append((x_val, y_val, z))

    for i, wp in enumerate(wps):
        if wp.get("action") == "LAND":
            prev = waypoints[i - 1] if i > 0 else waypoints[0]
            waypoints[i] = (prev[0], prev[1], 0)

    center = np.mean(waypoints, axis=0)
    extent = np.max(np.abs(waypoints - center)) + 15

    n_wp = len(waypoints)
    total_frames = int((n_wp - 1) * DURATION_PER_WP * FPS + n_wp * PAUSE_AT_WP * FPS)

    mission_name = "PERIMETER PATROL — 50m SQUARE"

    print(f"Rendering {total_frames} frames ({total_frames/FPS:.0f}s @ {FPS}fps)...")

    fig = plt.figure(figsize=(16, 9), dpi=100)
    ax = fig.add_subplot(111, projection="3d", facecolor="#0a0a14")
    ax.set_facecolor("#0a0a14")

    def setup_axes():
        ax.clear()
        ax.set_xlim(center[0] - extent, center[0] + extent)
        ax.set_ylim(center[1] - extent, center[1] + extent)
        ax.set_zlim(-max(abs(w[2]) for w in waypoints) - 3 if waypoints else -20, 2)
        ax.set_xlabel("X (m)", color="#808090", labelpad=6)
        ax.set_ylabel("Y (m)", color="#808090", labelpad=6)
        ax.set_zlabel("Altitude (m)", color="#808090", labelpad=6)
        ax.tick_params(colors="#606070", labelsize=8)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor("#202030")
        ax.yaxis.pane.set_edgecolor("#202030")
        ax.zaxis.pane.set_edgecolor("#202030")
        ax.grid(True, color="#202030", linewidth=0.4, alpha=0.6)
        ax.view_init(elev=20, azim=-45)
        for spine in ax.spines.values():
            spine.set_color("#303045")

    setup_axes()

    flight_path = []
    for i in range(n_wp - 1):
        a, b = waypoints[i], waypoints[i + 1]
        steps = int(DURATION_PER_WP * FPS)
        for s in range(steps):
            flight_path.append(interpolate_3d(a, b, s / steps))
        for _ in range(int(PAUSE_AT_WP * FPS)):
            flight_path.append(b)
    for _ in range(int(PAUSE_AT_WP * FPS * 2)):
        flight_path.append(waypoints[-1])

    n_frames = len(flight_path)
    wp_x = [w[0] for w in waypoints]
    wp_y = [w[1] for w in waypoints]
    wp_z = [w[2] for w in waypoints]

    def get_drone_verts(dx, dy, dz, angle=0):
        verts = []
        for a in np.linspace(0, 2 * math.pi, 13):
            verts.append((dx + 1.2 * math.cos(a), dy + 1.2 * math.sin(a), dz))
        return verts

    # Second pass: render with FFMpegWriter
    writer = FFMpegWriter(fps=FPS, metadata={"title": "Agentic Drones - Mission Simulation"},
                          bitrate=8000)

    with writer.saving(fig, OUTPUT_PATH, dpi=100):
        for fi in range(n_frames):
            progress = (fi + 1) / n_frames
            cam_angle = -45 + 95 * min(progress * 1.2, 1.0)
            drone_pos = flight_path[fi]

            trail_start = max(0, fi - 200)
            trail_x = [flight_path[j][0] for j in range(trail_start, fi + 1)]
            trail_y = [flight_path[j][1] for j in range(trail_start, fi + 1)]
            trail_z = [flight_path[j][2] for j in range(trail_start, fi + 1)]

            drone_angle = fi * 0.05

            if fi < n_frames * 0.15:
                status = "TAKEOFF"
            elif fi < n_frames * 0.85:
                status = "MISSION"
            elif fi < n_frames * 0.95:
                status = "LANDING"
            else:
                status = "COMPLETE"

            setup_axes()
            ax.view_init(elev=18 + 3 * math.sin(fi * 0.02), azim=cam_angle)

            # ground grid
            gs = np.linspace(-extent * 0.8, extent * 0.8, 9)
            gx, gy = np.meshgrid(gs, gs)
            gz = np.full_like(gx, -0.1)
            ax.plot_wireframe(gx, gy, gz, color="#151528", linewidth=0.3, alpha=0.5)

            # concentric terrain rings
            theta = np.linspace(0, 2 * np.pi, 50)
            for ri in np.linspace(5, extent * 0.7, 6):
                cx = center[0] + ri * np.cos(theta)
                cy = center[1] + ri * np.sin(theta)
                ax.plot(cx, cy, np.full_like(theta, -0.1),
                        color="#151528", linewidth=0.3, alpha=0.3)

            # waypoint path (dashed)
            ax.plot(wp_x, wp_y, wp_z, color="#40a060", linewidth=0.5,
                    alpha=0.3, linestyle="--")

            # waypoint markers
            visited = min(int((fi / n_frames) * n_wp), n_wp - 1)
            for i, (wx, wy, wz) in enumerate(waypoints):
                done = i <= visited
                color = "#40ff80" if done else "#40a060"
                alpha = 0.9 if done else 0.35
                ax.scatter([wx], [wy], [wz], c=[color], s=60 if done else 30,
                           alpha=alpha, marker="o",
                           edgecolors="#40ff80" if done else None,
                           linewidths=0.5)
                if done and i % 2 == 0:
                    ax.text(wx, wy, wz + 1.5, f"WP{i}", color="#40ff80",
                            alpha=0.7, fontsize=6, ha="center", va="bottom",
                            path_effects=[pe.withStroke(linewidth=2, foreground="#0a0a14")])

            # start/home marker
            sx, sy, sz = waypoints[0]
            ax.scatter([sx], [sy], [sz], c=["#80e0ff"], s=40, alpha=0.5,
                       marker="s", edgecolors="#80e0ff", linewidths=0.5)

            # flight trail (single Line3DCollection instead of many ax.plot calls)
            if len(trail_x) > 1:
                segments = []
                for i in range(len(trail_x) - 1):
                    segments.append([(trail_x[i], trail_y[i], trail_z[i]),
                                     (trail_x[i+1], trail_y[i+1], trail_z[i+1])])
                trail_colors = [0.1 + 0.7 * (i / len(trail_x)) for i in range(len(trail_x) - 1)]
                trail_lc = Line3DCollection(segments, colors=[(1.0, 0.5, 0.25, a) for a in trail_colors],
                                             linewidths=1.5)
                ax.add_collection3d(trail_lc)

            # drone body (Poly3DCollection instead of ax.fill for 3D compatibility)
            dx, dy, dz = drone_pos
            d_verts = get_drone_verts(dx, dy, dz)
            drone_poly = Poly3DCollection([d_verts], color="#ff6030", alpha=0.7, zorder=5)
            ax.add_collection3d(drone_poly)

            # drone arms + rotors
            for ang in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
                ex = dx + 2.0 * math.cos(ang + drone_angle)
                ey = dy + 2.0 * math.sin(ang + drone_angle)
                ax.plot([dx, ex], [dy, ey], [dz, dz],
                        color="#ff8040", linewidth=1.5, alpha=0.6, zorder=4)
                ax.scatter([ex], [ey], [dz], c=["#40ff80"], s=15,
                           alpha=0.5, zorder=3)

            # altitude line
            ax.plot([dx, dx], [dy, dy], [dz, 0],
                    color="#40ff80", linewidth=0.3, alpha=0.15, linestyle=":")

            # === 2D text overlays (no FancyBboxPatch — pure text) ===

            # title
            ax.text2D(0.02, 0.95, mission_name, transform=ax.transAxes,
                      color="#80e0ff", fontsize=14, fontweight="bold",
                      path_effects=[pe.withStroke(linewidth=2, foreground="#0a0a14")])

            # info panel
            alt_m = abs(dz)
            info_lines = [
                f"  MISSION: Perimeter Loop (2 circuits)",
                f"  DRONE:   Quadrotor (PX4)      ALT: {alt_m:5.1f} m",
                f"  SPEED:   5.0 m/s              WP:  {visited+1:2d}/{n_wp}",
                f"  STATUS:  {status:<14s}",
            ]
            for li, line in enumerate(info_lines):
                ax.text2D(0.02, 0.82 - li * 0.045, line, transform=ax.transAxes,
                          color="#c0c0d0", fontsize=9, fontfamily="monospace",
                          path_effects=[pe.withStroke(linewidth=1, foreground="#0a0a14")])

            # progress bar (Unicode)
            bar_str = build_progress_bar(progress)
            ax.text2D(0.02, 0.78, bar_str, transform=ax.transAxes,
                      color="#40ff80" if progress < 1.0 else "#00ff60",
                      fontsize=9, fontfamily="monospace",
                      path_effects=[pe.withStroke(linewidth=1, foreground="#0a0a14")])

            # corner timestamp
            elapsed = fi / FPS
            ax.text2D(0.98, 0.02, f"AGENTIC DRONES    {int(elapsed//60):02d}:{int(elapsed%60):02d}",
                      transform=ax.transAxes, color="#404060", fontsize=8,
                      ha="right", va="bottom", fontfamily="monospace")

            # legend
            ax.text2D(0.66, 0.05, "● Waypoint\n■ Start/Home\n━ Flight path\n━ Planned route",
                      transform=ax.transAxes, color="#606070", fontsize=7,
                      fontfamily="monospace", verticalalignment="bottom",
                      path_effects=[pe.withStroke(linewidth=1, foreground="#0a0a14")])

            writer.grab_frame()

            if fi % 200 == 0:
                print(f"  Frame {fi}/{n_frames} ({100 * fi // n_frames}%)")

    writer.finish()
    plt.close(fig)

    size_mb = Path(OUTPUT_PATH).stat().st_size / (1024 * 1024)
    print(f"\n✓ Simulation video saved: {OUTPUT_PATH}")
    print(f"  Resolution: 1600x900  |  Frames: {n_frames}  |  Duration: {n_frames / FPS:.0f}s")
    print(f"  Size: {size_mb:.0f} MB  |  FPS: {FPS}")
    print(f"  Mission: {mission_name}  |  Waypoints: {n_wp}")


if __name__ == "__main__":
    main()
