"""Accessible Route Visualizer for Winter Park Resort (WCAG 2.1 AA Compliant)."""

from pathlib import Path
from typing import Dict, List, Optional
from .graph import SkiResortTopology, AlpineEdge, AlpineNode


class AccessibleSkiVisualizer:
    """Generates accessible SVG and HTML maps of Winter Park Resort and optimized ski itineraries."""

    DIFFICULTY_STYLES = {
        "green": {"color": "#2e7d32", "dash": "none", "label": "Green Circle (Easiest)"},
        "blue": {"color": "#1565c0", "dash": "none", "label": "Blue Square (Intermediate)"},
        "black": {"color": "#212121", "dash": "6,3", "label": "Black Diamond (Advanced)"},
        "double_black": {"color": "#b71c1c", "dash": "4,2", "label": "Double Black (Expert)"},
        "lift": {"color": "#ff6a00", "dash": "2,2", "label": "Chairlift / Gondola (Uphill)"},
    }

    def __init__(self, resort: SkiResortTopology, width: int = 1000, height: int = 700, padding: int = 60):
        self.resort = resort
        self.width = width
        self.height = height
        self.padding = padding

        # Compute bounding box for projection
        lats = [n.lat for n in resort.nodes_data.values()]
        lons = [n.lon for n in resort.nodes_data.values()]

        self.min_lat, self.max_lat = min(lats), max(lats)
        self.min_lon, self.max_lon = min(lons), max(lons)

    def _project(self, lat: float, lon: float) -> tuple:
        """Projects GPS (lat, lon) to 2D SVG canvas (x, y)."""
        # Invert latitude since higher latitude is higher on map (lower y)
        norm_x = (lon - self.min_lon) / max((self.max_lon - self.min_lon), 1e-6)
        norm_y = 1.0 - (lat - self.min_lat) / max((self.max_lat - self.min_lat), 1e-6)

        x = self.padding + norm_x * (self.width - 2 * self.padding)
        y = self.padding + norm_y * (self.height - 2 * self.padding)
        return x, y

    def generate_svg(self, highlighted_route: Optional[List[AlpineEdge]] = None) -> str:
        """Renders an SVG string representing the Winter Park network and optimal route."""
        highlight_names = {e.name for e in highlighted_route} if highlighted_route else set()

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" '
            f'width="100%" height="auto" role="img" aria-labelledby="mapTitle mapDesc" '
            f'style="background-color: #0d0d10; font-family: ui-monospace, SFMono-Regular, monospace;">',
            f'<title id="mapTitle">Winter Park Resort - QUASAR Optimal Route Map</title>',
            f'<desc id="mapDesc">Geospatial topology of Winter Park ski lifts and trails with QAOA optimal route highlighted.</desc>',
            # Defs & Filters for Glow
            '<defs>',
            '  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">',
            '    <feGaussianBlur stdDeviation="3" result="blur" />',
            '    <feMerge>',
            '      <feMergeNode in="blur" />',
            '      <feMergeNode in="SourceGraphic" />',
            '    </feMerge>',
            '  </filter>',
            '</defs>',
            # Title & Header
            f'<text x="{self.padding}" y="35" fill="#f7f4ef" font-size="18" font-weight="bold">WINTER PARK RESORT • QUASAR QUANTUM ROUTE</text>',
            f'<text x="{self.padding}" y="52" fill="#9e9d9b" font-size="11">PARSENN BOWL • MARY JANE • VASQUEZ RIDGE • THE CIRQUE • WINTER PARK</text>',
        ]

        # Draw all Base Edges (Trails & Lifts)
        svg_parts.append('<g id="base-network" opacity="0.45">')
        for edge in self.resort.get_edges_list():
            if edge.name in highlight_names:
                continue
            if edge.u in self.resort.nodes_data and edge.v in self.resort.nodes_data:
                n1 = self.resort.nodes_data[edge.u]
                n2 = self.resort.nodes_data[edge.v]
                x1, y1 = self._project(n1.lat, n1.lon)
                x2, y2 = self._project(n2.lat, n2.lon)
                style = self.DIFFICULTY_STYLES.get(edge.difficulty, self.DIFFICULTY_STYLES["blue"])
                stroke = style["color"]
                dash = style["dash"]
                svg_parts.append(
                    f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="{stroke}" stroke-width="2.5" stroke-dasharray="{dash}" stroke-linecap="round" />'
                )
        svg_parts.append('</g>')

        # Draw Highlighted Route (QAOA Optimal Path)
        if highlighted_route:
            svg_parts.append('<g id="highlighted-route">')
            for idx, edge in enumerate(highlighted_route, 1):
                if edge.u in self.resort.nodes_data and edge.v in self.resort.nodes_data:
                    n1 = self.resort.nodes_data[edge.u]
                    n2 = self.resort.nodes_data[edge.v]
                    x1, y1 = self._project(n1.lat, n1.lon)
                    x2, y2 = self._project(n2.lat, n2.lon)
                    color = "#ffd700" if edge.edge_type == "run" else "#ff6a00"
                    dash = "none" if edge.edge_type == "run" else "4,3"
                    svg_parts.append(
                        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="{color}" stroke-width="5" stroke-dasharray="{dash}" stroke-linecap="round" filter="url(#glow)" />'
                    )
                    # Step marker
                    mid_x, mid_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                    svg_parts.append(
                        f'<circle cx="{mid_x:.1f}" cy="{mid_y:.1f}" r="8" fill="#ff6a00" stroke="#f7f4ef" stroke-width="1.5" />'
                        f'<text x="{mid_x:.1f}" y="{mid_y+3.5:.1f}" fill="#0d0d10" font-size="9" font-weight="bold" text-anchor="middle">{idx}</text>'
                    )
            svg_parts.append('</g>')

        # Draw Nodes (Terminals & Summits)
        svg_parts.append('<g id="nodes">')
        for node in self.resort.nodes_data.values():
            x, y = self._project(node.lat, node.lon)
            is_summit = "summit" in node.node_type
            radius = 6 if is_summit else 4.5
            fill = "#ff6a00" if is_summit else "#f7f4ef"
            svg_parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{fill}" stroke="#0d0d10" stroke-width="1.5" />')
            # Label
            label_y = y - 9 if is_summit else y + 14
            svg_parts.append(
                f'<text x="{x:.1f}" y="{label_y:.1f}" fill="#f7f4ef" font-size="9.5" text-anchor="middle" font-weight="500">{node.name}</text>'
                f'<text x="{x:.1f}" y="{label_y+10:.1f}" fill="#9e9d9b" font-size="8" text-anchor="middle">{node.elevation_ft:,.0f}ft</text>'
            )
        svg_parts.append('</g>')

        # Legend (Accessible, High-Contrast)
        svg_parts.append(f'<g id="legend" transform="translate({self.width - 230}, 25)">')
        svg_parts.append('<rect width="210" height="150" fill="#16161a" stroke="#2b2b33" rx="4" />')
        svg_parts.append('<text x="12" y="20" fill="#f7f4ef" font-size="11" font-weight="bold">TRAIL DIFFICULTY</text>')
        legend_items = [
            ("Green Circle (Easiest)", "#2e7d32", "none"),
            ("Blue Square (Intermediate)", "#1565c0", "none"),
            ("Black Diamond (Advanced)", "#212121", "6,3"),
            ("Uphill Chairlift", "#ff6a00", "2,2"),
            ("QAOA Optimal Descent", "#ffd700", "none"),
        ]
        for i, (label, color, dash) in enumerate(legend_items):
            ly = 42 + i * 22
            svg_parts.append(f'<line x1="12" y1="{ly}" x2="36" y2="{ly}" stroke="{color}" stroke-width="3.5" stroke-dasharray="{dash}" />')
            svg_parts.append(f'<text x="44" y="{ly+4}" fill="#f7f4ef" font-size="9.5">{label}</text>')
        svg_parts.append('</g>')

        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    def save_html(self, output_filepath: str or Path, highlighted_route: Optional[List[AlpineEdge]] = None):
        """Saves a standalone, accessible HTML page with interactive SVG and screen-reader data table."""
        svg_content = self.generate_svg(highlighted_route)
        path = Path(output_filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        rows_html = ""
        if highlighted_route:
            for idx, e in enumerate(highlighted_route, 1):
                role = "Downhill Run" if e.edge_type == "run" else "Uphill Chairlift"
                rows_html += f"""
                <tr>
                    <td>{idx}</td>
                    <td><strong>{e.name}</strong></td>
                    <td>{role}</td>
                    <td>{e.territory}</td>
                    <td>{e.vertical_drop:,.0f} ft</td>
                    <td>{e.distance_3d_m:,.0f} m</td>
                    <td>{e.grade_percent:.1f}%</td>
                    <td>{e.duration_min:.1f} min</td>
                </tr>
                """

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Winter Park Resort - QUASAR Quantum Ski Route</title>
    <style>
        :root {{
            --bg: #0d0d10;
            --cream: #f7f4ef;
            --orange: #ff6a00;
            --card: #16161a;
            --border: #2b2b33;
            --text-muted: #9e9d9b;
        }}
        body {{
            background: var(--bg);
            color: var(--cream);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1040px;
            margin: 0 auto;
        }}
        header {{
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
        }}
        h1 {{
            margin: 0 0 6px 0;
            font-size: 26px;
            color: var(--cream);
        }}
        .tagline {{
            color: var(--orange);
            font-size: 14px;
            font-weight: 500;
        }}
        .map-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 32px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            font-size: 14px;
        }}
        th, td {{
            text-align: left;
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            color: var(--orange);
            font-weight: 600;
            background: #121216;
        }}
        tr:hover {{
            background: rgba(255, 255, 255, 0.04);
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            background: rgba(255, 106, 0, 0.15);
            color: var(--orange);
            font-size: 12px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <span class="badge">QOLLAB HACKATHON • STUDENT TRACK</span>
            <h1>QUASAR: Winter Park Ski Resort Altitude Optimization</h1>
            <div class="tagline">Hybrid Quantum Walk + QAOA Route Discovery • Supported by Qollab & IonQ</div>
        </header>

        <section class="map-card" aria-label="Interactive Trail Map">
            {svg_content}
        </section>

        <section aria-label="Accessible Route Table">
            <h2>Optimal Route Sequence & Elevation Breakdown</h2>
            <p style="color: var(--text-muted); font-size: 14px;">Screen-reader accessible table detailing the optimal continuous sequence of chairlifts and trails generated by the QAOA variational solver.</p>
            <table>
                <thead>
                    <tr>
                        <th>Step</th>
                        <th>Segment Name</th>
                        <th>Type</th>
                        <th>Territory</th>
                        <th>Vertical Drop</th>
                        <th>3D Slope Length</th>
                        <th>Avg. Grade</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </section>
    </div>
</body>
</html>
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_template)
