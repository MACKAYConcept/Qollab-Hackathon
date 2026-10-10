"""Continuous-Time Quantum Walk (CTQW) on Alpine Graph Topologies with Parameter Calibration."""

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.linalg import expm
from .graph import SkiResortTopology


@dataclass
class CTQWCalibrationResult:
    optimal_gamma: float
    optimal_t: float
    optimal_entropy: float
    optimal_ipr: float
    node_probabilities: Dict[str, float]
    parameter_grid_results: List[Dict[str, float]]
    recommended_threshold: float


class AlpineQuantumWalk:
    """Simulates a Continuous-Time Quantum Walk across the ski resort topology.
    
    Uses unitary evolution under the graph adjacency Hamiltonian to sample
    transition dynamics, hub connectedness, and pathway viability.
    """

    def __init__(self, resort: SkiResortTopology, gamma: float = 1.0):
        self.resort = resort
        self.gamma = gamma
        self.nodes = list(resort.graph.nodes())
        self.n_nodes = len(self.nodes)
        self.node_to_idx = {node: i for i, node in enumerate(self.nodes)}

        # Symmetrized adjacency matrix for coherent bidirectional exploration
        adj = resort.get_adjacency_matrix()
        sym_adj = (adj + adj.T)
        sym_adj[sym_adj > 0] = 1.0
        self.sym_adj = sym_adj
        self._update_hamiltonian(self.gamma)

    def _update_hamiltonian(self, gamma: float):
        """Updates the Hamiltonian with a new coupling rate gamma."""
        self.gamma = gamma
        self.hamiltonian = -self.gamma * self.sym_adj

    def compute_unitary(self, t: float) -> np.ndarray:
        """Computes the unitary evolution operator U(t) = exp(-i * H * t)."""
        return expm(-1j * self.hamiltonian * t)

    def transition_probabilities(self, start_node: str, t: float) -> Dict[str, float]:
        """Calculates transition probabilities from a given start node at time t."""
        if start_node not in self.node_to_idx:
            raise ValueError(f"Start node {start_node} not in graph.")

        idx = self.node_to_idx[start_node]
        psi_0 = np.zeros(self.n_nodes, dtype=complex)
        psi_0[idx] = 1.0

        u_t = self.compute_unitary(t)
        psi_t = u_t @ psi_0
        probs = np.abs(psi_t) ** 2

        return {self.nodes[i]: float(probs[i]) for i in range(self.n_nodes)}

    def compute_diffusion_metrics(self, probs: Dict[str, float]) -> Tuple[float, float]:
        """Computes Shannon Entropy S(t) and Inverse Participation Ratio (IPR).
        
        - Shannon Entropy: S(t) = -sum p_i * log2(p_i). Higher = broader mountain diffusion.
        - IPR: sum p_i^2. Measures localization (1 = localized, 1/N = maximally dispersed).
        """
        p_vals = np.array(list(probs.values()), dtype=float)
        p_vals = np.clip(p_vals, 1e-12, 1.0)
        p_vals = p_vals / np.sum(p_vals)

        shannon_entropy = float(-np.sum(p_vals * np.log2(p_vals)))
        ipr = float(np.sum(p_vals**2))
        return shannon_entropy, ipr

    def calibrate_diffusion(
        self,
        start_node: str = "WP_BASE",
        gamma_values: Optional[List[float]] = None,
        t_values: Optional[List[float]] = None,
    ) -> CTQWCalibrationResult:
        """Performs a grid-search calibration to identify optimal (gamma, t) parameters.
        
        Optimizes for:
        1. High topological diffusion (wavepacket reaches Parsenn Bowl & Mary Jane).
        2. High junction selectivity (sharp contrast between arterial hubs and dead-ends).
        """
        if gamma_values is None:
            gamma_values = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
        if t_values is None:
            t_values = [0.2, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0]

        max_score = -float("inf")
        best_params = {"gamma": 1.0, "t": 1.0, "entropy": 0.0, "ipr": 1.0}
        best_probs = {}
        grid_results = []

        max_possible_entropy = math.log2(self.n_nodes)

        for g in gamma_values:
            self._update_hamiltonian(g)
            for t in t_values:
                probs = self.transition_probabilities(start_node, t)
                entropy, ipr = self.compute_diffusion_metrics(probs)

                # Variance of probabilities measures junction contrast (distinguishing hubs)
                variance = float(np.var(list(probs.values())))

                # Composite score: balance high coverage (entropy) with distinct hub peaks (variance)
                normalized_entropy = entropy / max_possible_entropy
                score = (0.6 * normalized_entropy) + (0.4 * (variance * 10.0))

                grid_entry = {
                    "gamma": g,
                    "t": t,
                    "entropy": entropy,
                    "ipr": ipr,
                    "variance": variance,
                    "score": score,
                }
                grid_results.append(grid_entry)

                if score > max_score:
                    max_score = score
                    best_params = {"gamma": g, "t": t, "entropy": entropy, "ipr": ipr}
                    best_probs = probs

        # Reset Hamiltonian to calibrated optimal gamma
        self._update_hamiltonian(best_params["gamma"])

        # Determine adaptive threshold (mean minus 0.5 standard deviation of non-zero probabilities)
        p_list = list(best_probs.values())
        rec_threshold = float(max(0.04, np.mean(p_list) - 0.5 * np.std(p_list)))

        return CTQWCalibrationResult(
            optimal_gamma=best_params["gamma"],
            optimal_t=best_params["t"],
            optimal_entropy=best_params["entropy"],
            optimal_ipr=best_params["ipr"],
            node_probabilities=best_probs,
            parameter_grid_results=grid_results,
            recommended_threshold=rec_threshold,
        )

    def prune_candidate_edges(
        self, start_node: str, t_steps: List[float], threshold: float = 0.05
    ) -> List[Tuple[str, str]]:
        """Prunes low-probability topological pathways based on quantum walk diffusion."""
        aggregated_probs = {node: 0.0 for node in self.nodes}
        for t in t_steps:
            probs = self.transition_probabilities(start_node, t)
            for node, p in probs.items():
                aggregated_probs[node] += p / len(t_steps)

        active_nodes = {node for node, p in aggregated_probs.items() if p >= threshold}

        viable_edges = []
        for u, v in self.resort.graph.edges():
            if u in active_nodes and v in active_nodes:
                viable_edges.append((u, v))

        return viable_edges
