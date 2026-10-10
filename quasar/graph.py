"""Alpine graph model with real-world geospatial coordinates and elevation metrics."""

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import networkx as nx
import numpy as np


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the great-circle surface distance in meters between two GPS coordinates."""
    r = 6371000.0  # Earth's radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def compute_3d_slope_metrics(
    lat1: float, lon1: float, elev1_ft: float,
    lat2: float, lon2: float, elev2_ft: float
) -> Tuple[float, float]:
    """Computes the 3D surface slope distance (meters) and average grade percentage."""
    surface_dist_m = haversine_distance_m(lat1, lon1, lat2, lon2)
    vertical_diff_m = abs(elev1_ft - elev2_ft) * 0.3048

    slope_distance_m = math.sqrt(surface_dist_m**2 + vertical_diff_m**2)
    grade_percent = (vertical_diff_m / max(surface_dist_m, 1.0)) * 100.0
    return slope_distance_m, grade_percent


@dataclass
class AlpineNode:
    node_id: str
    name: str
    lat: float
    lon: float
    elevation_ft: float
    elevation_m: float
    territory: str = "General"
    node_type: str = "junction"  # 'base_area', 'summit', 'junction', 'lift_terminal'


@dataclass
class AlpineEdge:
    u: str
    v: str
    edge_type: str  # 'run' or 'lift'
    name: str
    vertical_drop: float  # feet (positive for downhill runs, 0 net for lifts)
    elevation_gain: float  # feet (positive for uphill lifts, 0 for runs)
    duration_min: float  # ski transit time or lift ride + queue in minutes
    difficulty: str  # 'green', 'blue', 'black', 'double_black', or 'lift'
    territory: str = "General"
    coordinates: List[List[float]] = field(default_factory=list)  # [[lon, lat], ...]
    distance_3d_m: float = 0.0
    grade_percent: float = 0.0


class SkiResortTopology:
    """Represents a ski mountain as a directed multigraph with geospatial coordinates."""

    def __init__(self, name: str):
        self.name = name
        self.graph = nx.DiGraph()
        self.nodes_data: Dict[str, AlpineNode] = {}
        self.node_elevations: Dict[str, float] = {}

    def add_node(self, node: AlpineNode):
        self.nodes_data[node.node_id] = node
        self.node_elevations[node.node_id] = node.elevation_ft
        self.graph.add_node(
            node.node_id,
            name=node.name,
            lat=node.lat,
            lon=node.lon,
            elevation=node.elevation_ft,
            elevation_m=node.elevation_m,
            territory=node.territory,
            node_type=node.node_type,
        )

    def add_edge(self, edge: AlpineEdge):
        # Calculate 3D slope distance and grade if coordinates exist
        if edge.u in self.nodes_data and edge.v in self.nodes_data:
            n_u = self.nodes_data[edge.u]
            n_v = self.nodes_data[edge.v]
            slope_m, grade = compute_3d_slope_metrics(
                n_u.lat, n_u.lon, n_u.elevation_ft,
                n_v.lat, n_v.lon, n_v.elevation_ft
            )
            edge.distance_3d_m = slope_m
            edge.grade_percent = grade
            if not edge.coordinates:
                edge.coordinates = [[n_u.lon, n_u.lat], [n_v.lon, n_v.lat]]

        self.graph.add_edge(
            edge.u,
            edge.v,
            key=edge.name,
            edge_type=edge.edge_type,
            name=edge.name,
            vertical_drop=edge.vertical_drop,
            elevation_gain=edge.elevation_gain,
            duration=edge.duration_min,
            difficulty=edge.difficulty,
            territory=edge.territory,
            distance_3d_m=edge.distance_3d_m,
            grade_percent=edge.grade_percent,
            coordinates=edge.coordinates,
        )

    def get_adjacency_matrix(self) -> np.ndarray:
        """Returns the binary adjacency matrix of the underlying network."""
        nodes = list(self.graph.nodes())
        return nx.to_numpy_array(self.graph, nodelist=nodes)

    def get_edges_list(self) -> List[AlpineEdge]:
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append(
                AlpineEdge(
                    u=u,
                    v=v,
                    edge_type=data.get("edge_type", "run"),
                    name=data.get("name", f"{u}->{v}"),
                    vertical_drop=data.get("vertical_drop", 0.0),
                    elevation_gain=data.get("elevation_gain", 0.0),
                    duration_min=data.get("duration", 10.0),
                    difficulty=data.get("difficulty", "blue"),
                    territory=data.get("territory", "General"),
                    coordinates=data.get("coordinates", []),
                    distance_3d_m=data.get("distance_3d_m", 0.0),
                    grade_percent=data.get("grade_percent", 0.0),
                )
            )
        return edges

    @classmethod
    def from_geojson(cls, filepath: str or Path) -> "SkiResortTopology":
        """Loads resort topology and real-world GPS coordinates from a GeoJSON FeatureCollection."""
        path = Path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        resort_name = data.get("name", "Winter Park Resort Ski Topology")
        resort = cls(resort_name)

        # First pass: parse Point features (Alpine Nodes)
        for feat in data.get("features", []):
            geom = feat.get("geometry", {})
            props = feat.get("properties", {})
            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [0.0, 0.0])
                node_id = props.get("node_id", feat.get("id"))
                elev_ft = float(props.get("elevation_ft", 0.0))
                elev_m = float(props.get("elevation_m", elev_ft * 0.3048))
                node = AlpineNode(
                    node_id=node_id,
                    name=props.get("name", node_id),
                    lon=coords[0],
                    lat=coords[1],
                    elevation_ft=elev_ft,
                    elevation_m=elev_m,
                    territory=props.get("territory", "General"),
                    node_type=props.get("type", "junction"),
                )
                resort.add_node(node)

        # Second pass: parse LineString features (Alpine Edges: Lifts & Trails)
        for feat in data.get("features", []):
            geom = feat.get("geometry", {})
            props = feat.get("properties", {})
            if geom.get("type") == "LineString":
                coords = geom.get("coordinates", [])
                edge = AlpineEdge(
                    u=props.get("u"),
                    v=props.get("v"),
                    edge_type=props.get("edge_type", "run"),
                    name=props.get("name", feat.get("id")),
                    vertical_drop=float(props.get("vertical_drop_ft", 0.0)),
                    elevation_gain=float(props.get("elevation_gain_ft", 0.0)),
                    duration_min=float(props.get("duration_min", 7.0)),
                    difficulty=props.get("difficulty", "blue"),
                    territory=props.get("territory", "General"),
                    coordinates=coords,
                )
                resort.add_edge(edge)

        return resort


def create_winter_park_resort() -> SkiResortTopology:
    """Instantiates the real-world Winter Park Resort topology dataset."""
    default_geojson = Path(__file__).resolve().parent.parent / "data" / "winter_park_resort.geojson"
    if default_geojson.exists():
        return SkiResortTopology.from_geojson(default_geojson)

    # Fallback programmatic construction if file moved
    resort = SkiResortTopology("Winter Park Resort, Colorado")
    # Base Nodes
    resort.add_node(AlpineNode("WP_BASE", "Winter Park Base Village", 39.8869, -105.7625, 9000.0, 2743.2, "Winter Park", "base_area"))
    resort.add_node(AlpineNode("MJ_BASE", "Mary Jane Base", 39.8680, -105.7711, 9450.0, 2880.4, "Mary Jane", "base_area"))
    resort.add_node(AlpineNode("SUNSPOT", "Sunspot Mountaintop Lodge", 39.8805, -105.7760, 10700.0, 3261.4, "Winter Park", "junction_summit"))
    resort.add_node(AlpineNode("MJ_SUMMIT", "Lunch Rock / Mary Jane Summit", 39.8580, -105.7830, 11200.0, 3413.8, "Mary Jane", "summit"))
    resort.add_node(AlpineNode("PARSENN_SUMMIT", "Parsenn Bowl Summit (Panoramic Top)", 39.8510, -105.7920, 12060.0, 3675.9, "Parsenn Bowl", "summit"))
    resort.add_node(AlpineNode("TIMBERLINE", "Timberline Saddle / Pano Base", 39.8620, -105.7870, 10420.0, 3176.0, "Parsenn Bowl", "lift_terminal"))
    resort.add_node(AlpineNode("VASQUEZ_SUMMIT", "Vasquez Ridge Summit", 39.8730, -105.7920, 10700.0, 3261.4, "Vasquez Ridge", "summit"))
    resort.add_node(AlpineNode("VASQUEZ_BASE", "Vasquez Ridge Base", 39.8850, -105.7860, 9150.0, 2788.9, "Vasquez Ridge", "lift_terminal"))
    resort.add_node(AlpineNode("EAGLE_WIND_SUMMIT", "Eagle Wind Summit", 39.8550, -105.7760, 11000.0, 3352.8, "Eagle Wind", "summit"))
    resort.add_node(AlpineNode("EAGLE_WIND_BASE", "Eagle Wind Basin Base", 39.8490, -105.7790, 10250.0, 3124.2, "Eagle Wind", "lift_terminal"))

    # Lifts
    resort.add_edge(AlpineEdge("WP_BASE", "SUNSPOT", "lift", "The_Gondola_Express", 0.0, 1700.0, 7.0, "lift", "Winter Park"))
    resort.add_edge(AlpineEdge("MJ_BASE", "MJ_SUMMIT", "lift", "Super_Gauge_Express", 0.0, 1750.0, 7.5, "lift", "Mary Jane"))
    resort.add_edge(AlpineEdge("TIMBERLINE", "PARSENN_SUMMIT", "lift", "Panoramic_Express", 0.0, 1640.0, 8.0, "lift", "Parsenn Bowl"))
    resort.add_edge(AlpineEdge("VASQUEZ_BASE", "VASQUEZ_SUMMIT", "lift", "Wild_Spur_Express", 0.0, 1550.0, 7.0, "lift", "Vasquez Ridge"))

    # Runs
    resort.add_edge(AlpineEdge("SUNSPOT", "WP_BASE", "run", "Cranmer", 1700.0, 0.0, 7.0, "blue", "Winter Park"))
    resort.add_edge(AlpineEdge("SUNSPOT", "WP_BASE", "run", "Hughes", 1700.0, 0.0, 6.0, "black", "Winter Park"))
    resort.add_edge(AlpineEdge("MJ_SUMMIT", "MJ_BASE", "run", "Outhouse_Moguls", 1750.0, 0.0, 8.5, "black", "Mary Jane"))
    resort.add_edge(AlpineEdge("MJ_SUMMIT", "TIMBERLINE", "run", "Timberline_Cutoff", 780.0, 0.0, 4.0, "blue", "Mary Jane"))
    resort.add_edge(AlpineEdge("PARSENN_SUMMIT", "MJ_SUMMIT", "run", "Edelweiss", 860.0, 0.0, 5.0, "blue", "Parsenn Bowl"))
    resort.add_edge(AlpineEdge("VASQUEZ_SUMMIT", "VASQUEZ_BASE", "run", "Stagecoach", 1550.0, 0.0, 7.0, "blue", "Vasquez Ridge"))

    return resort


def create_sample_resort() -> SkiResortTopology:
    """Returns a sample resort topology (alias to Winter Park)."""
    return create_winter_park_resort()
