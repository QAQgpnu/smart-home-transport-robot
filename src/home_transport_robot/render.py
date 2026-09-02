from __future__ import annotations

import html
import json
from pathlib import Path


PALETTE = {
    "navy": "#0b1930",
    "blue": "#2f7cf6",
    "cyan": "#42d6c7",
    "yellow": "#ffca58",
    "red": "#ff6b6b",
    "ink": "#17233c",
    "muted": "#61708b",
    "wall": "#d9e2ef",
    "paper": "#f7f9fc",
}


def write_data(result: dict, artifact_dir: Path, docs_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    (artifact_dir / "navigation-run.json").write_text(payload + "\n", encoding="utf-8")
    compact = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    (docs_dir / "demo-data.js").write_text("window.DEMO_DATA=" + compact + ";\n", encoding="utf-8")


def render_svg(result: dict, destination: Path) -> None:
    width, height = 1200, 760
    pad_x, pad_y, map_w, map_h = 70, 155, 760, 500
    scene = result["scenario"]
    sx = map_w / scene["width"]
    sy = map_h / scene["height"]

    def xy(point: list[float]) -> tuple[float, float]:
        return pad_x + point[0] * sx, pad_y + point[1] * sy

    def poly(points: list[list[float]]) -> str:
        return " ".join(f"{xy(p)[0]:.1f},{xy(p)[1]:.1f}" for p in points)

    metrics = result["metrics"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="8" stdDeviation="12" flood-opacity=".13"/></filter>',
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f8fbff"/><stop offset="1" stop-color="#eef5ff"/></linearGradient>',
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="url(#bg)"/>',
        f'<text x="70" y="66" font-family="Segoe UI,Arial" font-size="30" font-weight="700" fill="{PALETTE["navy"]}">Smart-home robot navigation reconstruction</text>',
        f'<text x="70" y="102" font-family="Segoe UI,Arial" font-size="17" fill="{PALETTE["muted"]}">Dijkstra global route + dynamic-window local avoidance · deterministic offline demo</text>',
        f'<rect x="{pad_x}" y="{pad_y}" width="{map_w}" height="{map_h}" rx="18" fill="white" filter="url(#shadow)"/>',
    ]

    for x, y in scene["blocked"]:
        parts.append(f'<rect x="{pad_x + x*sx:.1f}" y="{pad_y + y*sy:.1f}" width="{sx+0.2:.1f}" height="{sy+0.2:.1f}" fill="{PALETTE["wall"]}"/>')
    parts.append(f'<polyline points="{poly(result["global_path"])}" fill="none" stroke="{PALETTE["blue"]}" stroke-width="5" stroke-dasharray="9 9" stroke-linecap="round" stroke-linejoin="round" opacity=".8"/>')
    trajectory = [[s["x"], s["y"]] for s in result["trajectory"]]
    parts.append(f'<polyline points="{poly(trajectory)}" fill="none" stroke="{PALETTE["cyan"]}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>')

    for obs in scene["dynamic_obstacles"]:
        ox, oy = xy([obs["x"], obs["y"]])
        parts.append(f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="{obs["radius"]*sx:.1f}" fill="{PALETTE["red"]}" opacity=".2" stroke="{PALETTE["red"]}" stroke-width="3"/>')
        parts.append(f'<text x="{ox+18:.1f}" y="{oy-16:.1f}" font-family="Segoe UI,Arial" font-size="14" font-weight="600" fill="{PALETTE["red"]}">dynamic obstacle</text>')

    start = xy([scene["start"][0] + 0.5, scene["start"][1] + 0.5])
    goal = xy([scene["goal"][0] + 0.5, scene["goal"][1] + 0.5])
    parts.extend([
        f'<circle cx="{start[0]:.1f}" cy="{start[1]:.1f}" r="11" fill="{PALETTE["yellow"]}" stroke="white" stroke-width="4"/>',
        f'<circle cx="{goal[0]:.1f}" cy="{goal[1]:.1f}" r="12" fill="{PALETTE["cyan"]}" stroke="white" stroke-width="4"/>',
        f'<text x="{start[0]+16:.1f}" y="{start[1]+5:.1f}" font-family="Segoe UI,Arial" font-size="15" font-weight="700" fill="{PALETTE["ink"]}">START</text>',
        f'<text x="{goal[0]+16:.1f}" y="{goal[1]+5:.1f}" font-family="Segoe UI,Arial" font-size="15" font-weight="700" fill="{PALETTE["ink"]}">GOAL</text>',
        '<g font-family="Segoe UI,Arial">',
        f'<text x="885" y="188" font-size="15" font-weight="700" fill="{PALETTE["blue"]}">GLOBAL PLANNER</text>',
        f'<text x="885" y="220" font-size="25" font-weight="700" fill="{PALETTE["navy"]}">Dijkstra / 8-connected</text>',
        f'<text x="885" y="278" font-size="15" font-weight="700" fill="{PALETTE["cyan"]}">LOCAL PLANNER</text>',
        f'<text x="885" y="310" font-size="25" font-weight="700" fill="{PALETTE["navy"]}">Dynamic Window</text>',
        f'<text x="885" y="370" font-size="15" font-weight="700" fill="{PALETTE["muted"]}">DEMO RESULT</text>',
        f'<text x="885" y="420" font-size="44" font-weight="750" fill="{PALETTE["navy"]}">{html.escape(str(metrics["route_length"]))} m</text>',
        f'<text x="885" y="447" font-size="16" fill="{PALETTE["muted"]}">simulated route length</text>',
        f'<text x="885" y="505" font-size="44" font-weight="750" fill="{PALETTE["navy"]}">{html.escape(str(metrics["minimum_clearance"]))} m</text>',
        f'<text x="885" y="532" font-size="16" fill="{PALETTE["muted"]}">minimum obstacle clearance</text>',
        f'<rect x="885" y="584" width="218" height="48" rx="24" fill="{PALETTE["navy"]}"/>',
        f'<text x="994" y="615" text-anchor="middle" font-size="16" font-weight="700" fill="white">GOAL REACHED · {html.escape(str(metrics["steps"]))} STEPS</text>',
        "</g>",
        f'<text x="70" y="713" font-family="Segoe UI,Arial" font-size="14" fill="{PALETTE["muted"]}">Blue dashed: global route  ·  Cyan: simulated robot trajectory  ·  Red: obstacle introduced during navigation</text>',
        "</svg>",
    ])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(parts), encoding="utf-8")
