#!/usr/bin/env python3
"""Generate CRIS-IoMT paper SVG figures from evaluation data.

All figures use pure SVG with no external dependencies.
White background for print and IEEE submission compatibility.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

OUT_DIR = Path("paper/iomt-healthcare/figures")

# ── Palette (print-safe, colourblind-friendly) ────────────────────────────────
BLUE   = "#1d4ed8"
TEAL   = "#0d9488"
GREEN  = "#059669"
RED    = "#dc2626"
AMBER  = "#d97706"
PURPLE = "#7c3aed"
SLATE  = "#475569"
LIGHT  = "#f8fafc"
WHITE  = "#ffffff"
INK    = "#172033"
MUTED  = "#617083"
BORDER = "#d8e2ec"

FONT = "Inter, Arial, sans-serif"


# ── SVG helpers ───────────────────────────────────────────────────────────────

def svg_open(w: int, h: int, title: str, desc: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">\n'
        f'  <title id="t">{escape(title)}</title>\n'
        f'  <desc id="d">{escape(desc)}</desc>\n'
        f'  <rect width="{w}" height="{h}" fill="{WHITE}"/>\n'
    )


def text(x: float, y: float, s: str, size: int, color: str = INK,
         weight: int = 400, anchor: str = "start") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" '
        f'font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">'
        f'{escape(str(s))}</text>'
    )


def rect(x: float, y: float, w: float, h: float, fill: str,
         stroke: str = "none", rx: float = 6.0, opacity: float = 1.0) -> str:
    op = f' opacity="{opacity}"' if opacity < 1.0 else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="{rx}" fill="{fill}" stroke="{stroke}"{op}/>'
    )


def line(x1: float, y1: float, x2: float, y2: float,
         color: str = BORDER, sw: float = 1.0) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{sw}"/>'
    )


def arrow(x1: float, y1: float, x2: float, y2: float, color: str = BLUE) -> str:
    ah = 7
    parts = [
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2 - ah:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="2"/>',
        f'<polygon points="{x2 - ah},{y2 - 4} {x2},{y2} {x2 - ah},{y2 + 4}" '
        f'fill="{color}"/>',
    ]
    return "\n".join(parts)


def multiline(x: float, y: float, lines: list[str], size: int,
              color: str = MUTED, gap: int = 16,
              anchor: str = "start") -> str:
    parts = []
    for i, ln in enumerate(lines):
        parts.append(text(x, y + i * gap, ln, size, color, anchor=anchor))
    return "\n".join(parts)


def write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path}")
    return path


# ── Figure 1: System Architecture ─────────────────────────────────────────────

def fig_architecture() -> str:
    W, H = 960, 440
    parts = [svg_open(W, H,
        "CRIS-IoMT System Architecture",
        "Pipeline from Azure IoT Hub through evidence collection, IotProfile, "
        "IoMT controls, scoring engine, and evidence pack. The dashed boundary "
        "below shows evidence outside cloud observability scope.")]

    # Title
    parts.append(text(40, 44, "CRIS-IoMT System Architecture", 22, INK, 700))
    parts.append(text(40, 66, "Cloud control-plane evidence pipeline", 14, MUTED))

    # Pipeline boxes
    boxes = [
        (TEAL,   "Azure\nIoT Hub",       "Device registry\nDiagnostics\nPolicies"),
        (BLUE,   "Evidence\nCollector",   "ARM + IoT CLI\nazure_collector.py"),
        (PURPLE, "IotProfile\nModel",     "20 cloud-\nobservable fields"),
        (BLUE,   "IoMT\nControls",        "IOT-001 to\nIOT-010"),
        (GREEN,  "Evidence\nPack",        "Findings\nDSPT mapping\nCaveats"),
    ]

    bw, bh = 142, 94
    gap = 32
    total_w = len(boxes) * bw + (len(boxes) - 1) * gap
    start_x = (W - total_w) / 2
    mid_y = 160

    for i, (color, title, body) in enumerate(boxes):
        bx = start_x + i * (bw + gap)
        by = mid_y - bh / 2

        # Shadow
        parts.append(rect(bx + 3, by + 3, bw, bh, "#d1d5db", rx=8))
        # Box
        parts.append(rect(bx, by, bw, bh, color, rx=8))
        # Title
        for j, ln in enumerate(title.split("\n")):
            parts.append(text(bx + bw / 2, by + 26 + j * 18, ln, 14, WHITE, 700, "middle"))
        # Body
        for j, ln in enumerate(body.split("\n")):
            parts.append(text(bx + bw / 2, by + 62 + j * 15, ln, 11, WHITE, 400, "middle"))

        # Arrow to next box
        if i < len(boxes) - 1:
            ax = bx + bw + 2
            ay = mid_y
            parts.append(arrow(ax, ay, ax + gap - 2, ay, WHITE if i == 0 else BLUE))
            # Override: draw BLUE on white bg
            parts.append(
                f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{ax + gap - 9:.1f}" y2="{ay:.1f}" '
                f'stroke="{BLUE}" stroke-width="2"/>'
            )
            parts.append(
                f'<polygon points="{ax + gap - 9},{ay - 4} {ax + gap},{ay} {ax + gap - 9},{ay + 4}" '
                f'fill="{BLUE}"/>'
            )

    # Scoring engine label between controls and pack
    cx = start_x + 3 * (bw + gap) + bw / 2 + gap / 2
    parts.append(text(cx, mid_y + 8, "Scoring\nEngine", 10, MUTED, 600, "middle"))

    # Out-of-scope boundary
    boundary_y = mid_y + 70
    parts.append(line(40, boundary_y, W - 40, boundary_y, BORDER, 1.5))
    parts.append(
        f'<line x1="40" y1="{boundary_y}" x2="{W - 40}" y2="{boundary_y}" '
        f'stroke="{BORDER}" stroke-width="1.5" stroke-dasharray="6,4"/>'
    )

    # Out-of-scope label
    parts.append(text(W / 2, boundary_y - 8, "▲ Cloud control-plane scope", 11, MUTED, 400, "middle"))
    parts.append(text(W / 2, boundary_y + 18, "▼ Outside CRIS-IoMT scope", 11, RED, 400, "middle"))

    # Out-of-scope boxes
    oos = [
        ("Device firmware\n& trust anchors", SLATE),
        ("Clinical telemetry\npayloads", SLATE),
        ("Patient data\ncontent", SLATE),
        ("Radio / sensing\nchannels", SLATE),
        ("Clinical safety\napproval", SLATE),
    ]
    oos_bw = 148
    oos_gap = 18
    oos_total = len(oos) * oos_bw + (len(oos) - 1) * oos_gap
    oos_start = (W - oos_total) / 2
    for i, (lbl, col) in enumerate(oos):
        bx = oos_start + i * (oos_bw + oos_gap)
        by = boundary_y + 30
        parts.append(rect(bx, by, oos_bw, 56, LIGHT, BORDER, 6))
        for j, ln in enumerate(lbl.split("\n")):
            parts.append(text(bx + oos_bw / 2, by + 22 + j * 16, ln, 11, SLATE, 400, "middle"))

    # Footer
    parts.append(text(40, H - 16,
        "Figure 1. CRIS-IoMT architecture. Healthcare IoT is an optional research domain; IoMT findings "
        "do not alter the base CRIS SME overall score.", 11, MUTED))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


# ── Figure 2: Control firing matrix (the key result) ─────────────────────────

def fig_control_matrix() -> str:
    W, H = 820, 520

    controls = [
        ("IOT-001", "Cloud device identity"),
        ("IOT-002", "Shared access policy least privilege"),
        ("IOT-003", "Diagnostic logging"),
        ("IOT-004", "Security monitoring observability"),
        ("IOT-005", "Public network access"),
        ("IOT-006", "Conditional private endpoint"),
        ("IOT-007", "Telemetry routing and retention"),
        ("IOT-008", "Secret governance"),
        ("IOT-009", "Clinical alert routing"),
        ("IOT-010", "Clinical-operational boundary"),
    ]
    # Weak baseline all fire. Simulated clinic passes alerting. Hardened clinic
    # additionally passes public-access, conditional private endpoint, and
    # telemetry-routing controls.
    results = {
        "Weak\nbaseline":    [True] * 10,
        "Simulated\nclinic": [True, True, True, True, True, True, True, True, False, True],
        "Hardened\nclinic":  [True, True, True, True, False, False, False, True, False, True],
    }
    scenarios = list(results.keys())

    label_w = 310
    cell_w = 120
    cell_h = 34
    top = 100
    left = label_w + 20

    desc = (
        "Heatmap of CRIS-IoMT control outcomes across three paper scenarios. "
        "Red = finding triggered. Green = control passes. "
        "IOT-005, IOT-006, IOT-007, and IOT-009 are the core controlled results."
    )
    parts = [svg_open(W, H, "CRIS-IoMT Control Firing Matrix", desc)]

    # Title
    parts.append(text(40, 44, "CRIS-IoMT Control Outcomes by Scenario", 20, INK, 700))
    parts.append(text(40, 64,
        "Red = finding triggered (governance weakness observed)   "
        "Green = control passes   ★ Core controlled results", 12, MUTED))

    # Column headers
    for j, sc in enumerate(scenarios):
        cx = left + j * cell_w + cell_w / 2
        for k, ln in enumerate(sc.split("\n")):
            parts.append(text(cx, top - 20 + k * 16, ln, 13, INK, 700, "middle"))

    # Row labels and cells
    for i, (cid, desc_short) in enumerate(controls):
        ry = top + i * cell_h
        is_key = cid in {"IOT-005", "IOT-006", "IOT-007", "IOT-009"}

        # Row background for key result
        if is_key:
            parts.append(rect(0, ry, W, cell_h, "#fffbeb", rx=0))
            parts.append(text(left - 10, ry + cell_h / 2 + 5, "★", 14, AMBER, 700, "end"))

        # Alternating row bg
        if not is_key and i % 2 == 0:
            parts.append(rect(0, ry, W, cell_h, "#f8fafc", rx=0))

        # Gridline
        parts.append(line(0, ry, W, ry, BORDER, 0.8))

        # Control label
        parts.append(text(40, ry + cell_h / 2 + 4, cid, 12, BLUE, 700))
        parts.append(text(108, ry + cell_h / 2 + 4, desc_short, 12, INK, 400))

        # Cells
        for j, sc in enumerate(scenarios):
            fired = results[sc][i]
            cx = left + j * cell_w
            fill = RED if fired else GREEN
            label = "Triggered" if fired else "Passes"
            lcolor = "#fef2f2" if fired else "#f0fdf4"
            parts.append(rect(cx + 4, ry + 4, cell_w - 8, cell_h - 8, lcolor, fill, 5))
            parts.append(text(cx + cell_w / 2, ry + cell_h / 2 + 4, label, 11, fill, 700, "middle"))

    # Bottom border
    parts.append(line(0, top + len(controls) * cell_h, W, top + len(controls) * cell_h, BORDER, 0.8))

    # Legend
    ly = top + len(controls) * cell_h + 22
    parts.append(rect(40, ly, 14, 14, "#fef2f2", RED, 3))
    parts.append(text(60, ly + 11, "Finding triggered — governance weakness observed", 12, INK))
    parts.append(rect(40, ly + 22, 14, 14, "#f0fdf4", GREEN, 3))
    parts.append(text(60, ly + 33, "Control passes — no cloud-observable weakness detected", 12, INK))
    parts.append(text(40, ly + 54,
        "Figure 2. IoMT control outcomes. The hardened clinic passes IOT-005, IOT-006, "
        "IOT-007, and IOT-009 after public access is disabled, telemetry routing is "
        "added, and an Azure Monitor alert is deployed.", 11, MUTED))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


# ── Figure 3: Scenario score comparison ───────────────────────────────────────

def fig_scenario_scores() -> str:
    W, H = 840, 420

    scenarios = [
        "Clean\nstanding demo",
        "Weak IoMT\nbaseline",
        "Simulated\nclinic",
        "Hardened\nclinic",
    ]
    overall  = [27.20, 33.06, 32.16, 32.16]
    iot_cat  = [26.64, 26.40, 27.08, 25.19]
    iot_cnt  = [10,    10,    9,     6]

    left, right, top, bottom = 70, W - 40, 100, H - 100
    pw = right - left
    ph = bottom - top
    max_score = 40.0
    n = len(scenarios)
    group_w = pw / n
    bar_w = 28
    gap = 10

    desc = (
        "Bar chart comparing CRIS overall risk score and Healthcare IoT category score "
        "across four controlled scenarios. The hardened clinic shows the lowest IoMT "
        "finding count after public exposure, telemetry routing, and alerting controls pass."
    )
    parts = [svg_open(W, H, "Scenario Score Comparison", desc)]

    parts.append(text(40, 44, "Scenario Score Comparison", 20, INK, 700))
    parts.append(text(40, 64,
        "Overall CRIS risk score and Healthcare IoT category score across controlled scenarios", 13, MUTED))

    # Gridlines and y-axis
    for tick in [0, 10, 20, 30, 40]:
        ty = bottom - (tick / max_score) * ph
        parts.append(line(left, ty, right, ty, BORDER, 0.8))
        parts.append(text(left - 8, ty + 4, str(tick), 11, MUTED, 400, "end"))

    parts.append(line(left, top, left, bottom, BORDER, 1.0))
    parts.append(line(left, bottom, right, bottom, BORDER, 1.5))

    # Bars
    for i, (sc, ov, iot, cnt) in enumerate(zip(scenarios, overall, iot_cat, iot_cnt)):
        cx = left + i * group_w + group_w / 2

        # Overall bar (blue)
        bh1 = (ov / max_score) * ph
        bx1 = cx - bar_w - gap / 2
        by1 = bottom - bh1
        parts.append(rect(bx1, by1, bar_w, bh1, BLUE, rx=4))
        parts.append(text(bx1 + bar_w / 2, by1 - 6, f"{ov:.2f}", 12, BLUE, 700, "middle"))

        # IoT category bar (teal)
        bh2 = (iot / max_score) * ph
        bx2 = cx + gap / 2
        by2 = bottom - bh2
        parts.append(rect(bx2, by2, bar_w, bh2, TEAL, rx=4))
        parts.append(text(bx2 + bar_w / 2, by2 - 6, f"{iot:.2f}", 12, TEAL, 700, "middle"))

        # IoT finding count badge
        parts.append(rect(cx - 20, bottom + 14, 40, 20, "#f1f5f9", BORDER, 4))
        parts.append(text(cx, bottom + 28, f"IOT: {cnt}", 11, SLATE, 600, "middle"))

        # Scenario label
        for j, ln in enumerate(sc.split("\n")):
            parts.append(text(cx, bottom + 52 + j * 15, ln, 12, INK, 600, "middle"))

    # Legend
    lx = left
    ly = H - 22
    parts.append(rect(lx, ly - 10, 12, 12, BLUE, rx=2))
    parts.append(text(lx + 16, ly, "Overall CRIS risk score", 12, INK))
    parts.append(rect(lx + 200, ly - 10, 12, 12, TEAL, rx=2))
    parts.append(text(lx + 216, ly, "Healthcare IoT category score (standalone, weight=0.0 in base model)", 12, INK))

    # Footer
    parts.append(text(40, H - 6,
        "Figure 3. Score comparison across scenarios. The Healthcare IoT score is reported "
        "separately from the standard SME overall risk score.", 10, MUTED))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


# ── Figure 4: Evidence sufficiency boundary ────────────────────────────────────

def fig_evidence_boundary() -> str:
    W, H = 860, 420

    cloud_items = [
        ("Direct cloud", "IOT Hub inventory", BLUE),
        ("Direct cloud", "Shared access policies", BLUE),
        ("Direct cloud", "Diagnostic settings", BLUE),
        ("Direct cloud", "Public network access", BLUE),
        ("Direct cloud", "Private endpoint posture", BLUE),
        ("Inferred cloud", "IoT message routes", TEAL),
        ("Inferred cloud", "Telemetry storage links", TEAL),
        ("Inferred cloud", "Alert rule presence", TEAL),
    ]
    outside_items = [
        ("Device / endpoint", "Firmware integrity", RED),
        ("Device / endpoint", "Device-side credentials", RED),
        ("Clinical / operational", "Patient telemetry payloads", AMBER),
        ("Clinical / operational", "Clinical safety case", AMBER),
        ("Clinical / operational", "Ownership boundaries (human)", AMBER),
        ("Permission gap", "Defender for IoT (IOT-004)", SLATE),
        ("Permission gap", "Tenant-level Entra signals", SLATE),
    ]

    desc = (
        "Evidence sufficiency boundary diagram showing what CRIS-IoMT can and cannot assess. "
        "Left zone: cloud control-plane evidence collected. Right zone: evidence outside scope."
    )
    parts = [svg_open(W, H, "CRIS-IoMT Evidence Sufficiency Boundary", desc)]

    parts.append(text(40, 44, "CRIS-IoMT Evidence Sufficiency Boundary", 20, INK, 700))
    parts.append(text(40, 64,
        "Cloud control-plane evidence (left) vs evidence outside CRIS-IoMT scope (right)", 13, MUTED))

    mid = W // 2
    zone_top = 82
    zone_h = H - 130

    # Left zone
    parts.append(rect(20, zone_top, mid - 30, zone_h, "#eff6ff", "#bfdbfe", 10))
    parts.append(text(mid // 2, zone_top + 22, "Cloud Observable", 14, BLUE, 700, "middle"))
    parts.append(text(mid // 2, zone_top + 38, "Assessed by CRIS-IoMT", 11, BLUE, 400, "middle"))

    row_h = 30
    for i, (cls, label, color) in enumerate(cloud_items):
        ry = zone_top + 55 + i * row_h
        parts.append(rect(36, ry, 8, 16, color, rx=2))
        parts.append(text(52, ry + 12, label, 12, INK))
        parts.append(text(52, ry + 24, cls, 10, MUTED))

    # Right zone
    parts.append(rect(mid + 10, zone_top, mid - 30, zone_h, "#fafafa", BORDER, 10))
    parts.append(text(mid + (mid - 30) // 2, zone_top + 22, "Outside Scope", 14, SLATE, 700, "middle"))
    parts.append(text(mid + (mid - 30) // 2, zone_top + 38, "Requires non-cloud evidence", 11, SLATE, 400, "middle"))

    for i, (cls, label, color) in enumerate(outside_items):
        ry = zone_top + 55 + i * row_h
        parts.append(rect(mid + 24, ry, 8, 16, color, rx=2))
        parts.append(text(mid + 40, ry + 12, label, 12, INK))
        col = RED if cls == "Device / endpoint" else AMBER if cls == "Clinical / operational" else SLATE
        parts.append(text(mid + 40, ry + 24, cls, 10, col))

    # Divider arrow annotation
    parts.append(
        f'<line x1="{mid}" y1="{zone_top + 10}" x2="{mid}" y2="{H - 50}" '
        f'stroke="{BORDER}" stroke-width="2" stroke-dasharray="6,4"/>'
    )

    # Legend
    lx, ly = 20, H - 32
    items = [("Direct cloud", BLUE), ("Inferred cloud", TEAL),
             ("Device / endpoint", RED), ("Clinical / operational", AMBER), ("Permission gap", SLATE)]
    for k, (lbl, col) in enumerate(items):
        parts.append(rect(lx + k * 160, ly - 9, 10, 10, col, rx=2))
        parts.append(text(lx + k * 160 + 14, ly, lbl, 10, INK))

    parts.append(text(40, H - 8,
        "Figure 4. Evidence sufficiency boundary. Permission gaps (e.g. IOT-004) "
        "are reported as observability gaps, not proof of absent monitoring.", 10, MUTED))

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args(argv)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print("Generating CRIS-IoMT paper figures...")
    write(out / "fig1-architecture.svg",      fig_architecture())
    write(out / "fig2-control-matrix.svg",    fig_control_matrix())
    write(out / "fig3-scenario-scores.svg",   fig_scenario_scores())
    write(out / "fig4-evidence-boundary.svg", fig_evidence_boundary())
    print(f"Done — 4 figures written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
