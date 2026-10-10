"""Classical optimization baselines for alpine routing benchmarking.

Includes:
1. GreedyTrajectoryRouter: Physical continuous graph traversal.
2. GreedyKnapsackRouter: Unconstrained altitude-per-minute upper bound.
3. SimulatedAnnealingTrajectoryRouter: MCMC path annealing over continuous graph walks.
4. QUBOSimulatedAnnealingRouter: Vector annealing on the exact QUBO formulation.
"""

from dataclasses import dataclass
import random
import time
from typing import Dict, List, Optional, Set, Tuple
import numpy as np
from .graph import AlpineEdge, SkiResortTopology


@dataclass
class BenchmarkResult:
    method_name: str
    selected_edges: List[AlpineEdge]
    total_vertical_ft: float
    total_time_min: float
    run_uniqueness_ratio: float
    runtime_sec: float
    is_continuous_path: bool = False
    start_node: str = ""
    end_node: str = ""


class GreedyKnapsackRouter:
    """Unconstrained Greedy Heuristic: picks runs with highest vertical drop per minute.
    
    Serves as an unconstrained classical upper bound (disregards physical lift-run sequencing).
    """

    def __init__(self, edges: List[AlpineEdge], target_time_min: float = 60.0):
        self.edges = edges
        self.target_time = target_time_min

    def solve(self) -> BenchmarkResult:
        start_t = time.perf_counter()

        # Filter only runs, sort by descent rate
        runs = [e for e in self.edges if e.edge_type == "run"]
        sorted_runs = sorted(
            runs,
            key=lambda e: (e.vertical_drop / max(e.duration_min, 1.0)),
            reverse=True,
        )

        selected = []
        current_time = 0.0
        total_vert = 0.0
        seen_names = set()

        for edge in sorted_runs:
            if current_time + edge.duration_min <= self.target_time:
                if edge.name not in seen_names:
                    selected.append(edge)
                    seen_names.add(edge.name)
                    current_time += edge.duration_min
                    total_vert += edge.vertical_drop

        runtime = time.perf_counter() - start_t
        runs_selected = [e.name for e in selected if e.edge_type == "run"]
        uniqueness = (len(set(runs_selected)) / len(runs_selected)) if runs_selected else 1.0

        return BenchmarkResult(
            method_name="Greedy Knapsack (Unconstrained APM)",
            selected_edges=selected,
            total_vertical_ft=total_vert,
            total_time_min=current_time,
            run_uniqueness_ratio=uniqueness,
            runtime_sec=runtime,
            is_continuous_path=False,
        )


class GreedyTrajectoryRouter:
    """Sequential Graph Traversal Heuristic: builds a physically continuous route.
    
    Follows alternating Lift -> Run -> Lift -> Run sequence from a base village,
    greedily selecting unexplored high-yield runs while staying within time budget.
    """

    def __init__(
        self,
        resort: SkiResortTopology,
        start_node: str = "WP_BASE",
        target_time_min: float = 120.0,
    ):
        self.resort = resort
        self.start_node = start_node
        self.target_time = target_time_min

        # Build adjacency map for fast lookup: u -> list of edges
        self.adj: Dict[str, List[AlpineEdge]] = {}
        for edge in resort.get_edges_list():
            self.adj.setdefault(edge.u, []).append(edge)

    def solve(self) -> BenchmarkResult:
        start_t = time.perf_counter()

        current_node = self.start_node
        route: List[AlpineEdge] = []
        current_time = 0.0
        total_vert = 0.0
        seen_run_names: Set[str] = set()

        # Step loop until time budget is exhausted or no valid transition
        while current_time < self.target_time:
            outgoing = self.adj.get(current_node, [])
            if not outgoing:
                break

            # Filter outgoing edges that fit in remaining time budget
            viable = [e for e in outgoing if current_time + e.duration_min <= self.target_time + 5.0]
            if not viable:
                break

            # Prioritize:
            # 1. If at a base/terminal where only lifts exist, choose lift leading to highest unvisited potential
            # 2. If at summit/junction, choose unvisited run with highest vertical drop per minute
            unvisited = [e for e in viable if e.name not in seen_run_names]
            candidate_pool = unvisited if unvisited else viable

            if any(e.edge_type == "run" for e in candidate_pool):
                runs_in_pool = [e for e in candidate_pool if e.edge_type == "run"]
                # Maximize vertical descent rate (ft/min)
                best_edge = max(
                    runs_in_pool,
                    key=lambda e: (e.vertical_drop / max(e.duration_min, 1.0)),
                )
            else:
                # Must take a lift: evaluate lift by downstream descent potential
                lifts_in_pool = [e for e in candidate_pool if e.edge_type == "lift"]
                best_edge = max(
                    lifts_in_pool,
                    key=lambda e: (
                        sum(
                            d.vertical_drop
                            for d in self.adj.get(e.v, [])
                            if d.edge_type == "run" and d.name not in seen_run_names
                        )
                        / max(e.duration_min, 1.0)
                    ),
                )

            route.append(best_edge)
            current_time += best_edge.duration_min
            if best_edge.edge_type == "run":
                total_vert += best_edge.vertical_drop
                seen_run_names.add(best_edge.name)
            current_node = best_edge.v

        runtime = time.perf_counter() - start_t
        runs_selected = [e.name for e in route if e.edge_type == "run"]
        uniqueness = (len(set(runs_selected)) / len(runs_selected)) if runs_selected else 1.0

        return BenchmarkResult(
            method_name="Greedy Trajectory (Continuous Walk)",
            selected_edges=route,
            total_vertical_ft=total_vert,
            total_time_min=current_time,
            run_uniqueness_ratio=uniqueness,
            runtime_sec=runtime,
            is_continuous_path=True,
            start_node=self.start_node,
            end_node=current_node,
        )


class SimulatedAnnealingTrajectoryRouter:
    """MCMC Trajectory Annealing: optimizes continuous graph walks under thermal cooling.
    
    Explores alternate branches, loop splices, and run replacements while strictly
    guaranteeing physical topological continuity (head-to-tail edge connections).
    """

    def __init__(
        self,
        resort: SkiResortTopology,
        start_node: str = "WP_BASE",
        target_time_min: float = 120.0,
        n_iterations: int = 5000,
        t_initial: float = 200.0,
        cooling_rate: float = 0.998,
        seed: int = 42,
    ):
        self.resort = resort
        self.start_node = start_node
        self.target_time = target_time_min
        self.n_iter = n_iterations
        self.t_initial = t_initial
        self.cooling = cooling_rate
        self.rng = random.Random(seed)

        self.adj: Dict[str, List[AlpineEdge]] = {}
        for edge in resort.get_edges_list():
            self.adj.setdefault(edge.u, []).append(edge)

    def _generate_random_walk(self) -> List[AlpineEdge]:
        """Generates an initial valid continuous walk starting at start_node."""
        walk = []
        curr = self.start_node
        curr_t = 0.0

        for _ in range(30):
            outgoing = self.adj.get(curr, [])
            if not outgoing:
                break
            viable = [e for e in outgoing if curr_t + e.duration_min <= self.target_time + 10.0]
            if not viable:
                break
            edge = self.rng.choice(viable)
            walk.append(edge)
            curr_t += edge.duration_min
            curr = edge.v
            if curr_t >= self.target_time:
                break
        return walk

    def _evaluate_path_energy(self, path: List[AlpineEdge]) -> float:
        """Energy function to minimize: negative vertical drop + penalties."""
        if not path:
            return 1e6

        total_vert = 0.0
        total_time = 0.0
        run_counts: Dict[str, int] = {}

        for edge in path:
            total_time += edge.duration_min
            if edge.edge_type == "run":
                total_vert += edge.vertical_drop
                run_counts[edge.name] = run_counts.get(edge.name, 0) + 1

        # Penalties:
        # Duplicate trail penalty
        dup_penalty = sum((count - 1) * 2000.0 for count in run_counts.values() if count > 1)
        # Time budget violation penalty (soft squared)
        time_diff = total_time - self.target_time
        time_penalty = 5.0 * (time_diff**2) if time_diff > 0 else 0.5 * abs(time_diff)

        # Minimize Energy = -VerticalDrop + Penalties
        energy = -total_vert + dup_penalty + time_penalty
        return energy

    def solve(self) -> BenchmarkResult:
        start_t = time.perf_counter()

        current_path = self._generate_random_walk()
        current_energy = self._evaluate_path_energy(current_path)

        best_path = list(current_path)
        best_energy = current_energy

        temp = self.t_initial

        for _ in range(self.n_iter):
            if not current_path:
                current_path = self._generate_random_walk()
                current_energy = self._evaluate_path_energy(current_path)

            # Mutation strategy: pick a random cut point and regrow a continuous branch
            cut_idx = self.rng.randint(0, len(current_path) - 1)
            prefix = current_path[:cut_idx]
            rebranch_node = prefix[-1].v if prefix else self.start_node

            # Grow candidate suffix
            suffix = []
            curr = rebranch_node
            curr_t = sum(e.duration_min for e in prefix)

            for _ in range(15):
                outgoing = self.adj.get(curr, [])
                if not outgoing:
                    break
                viable = [e for e in outgoing if curr_t + e.duration_min <= self.target_time + 10.0]
                if not viable:
                    break
                # Favor unvisited runs
                unvisited = [e for e in viable if e.name not in {x.name for x in prefix + suffix}]
                chosen = self.rng.choice(unvisited) if (unvisited and self.rng.random() < 0.7) else self.rng.choice(viable)
                suffix.append(chosen)
                curr_t += chosen.duration_min
                curr = chosen.v
                if curr_t >= self.target_time:
                    break

            candidate_path = prefix + suffix
            candidate_energy = self._evaluate_path_energy(candidate_path)

            delta = candidate_energy - current_energy
            if delta < 0 or self.rng.random() < math_exp_safe(-delta / max(temp, 1e-4)):
                current_path = candidate_path
                current_energy = candidate_energy

                if current_energy < best_energy:
                    best_energy = current_energy
                    best_path = list(candidate_path)

            temp *= self.cooling

        runtime = time.perf_counter() - start_t
        total_vert = sum(e.vertical_drop for e in best_path if e.edge_type == "run")
        total_time = sum(e.duration_min for e in best_path)
        runs_selected = [e.name for e in best_path if e.edge_type == "run"]
        uniqueness = (len(set(runs_selected)) / len(runs_selected)) if runs_selected else 1.0

        return BenchmarkResult(
            method_name="Simulated Annealing (Continuous Trajectory)",
            selected_edges=best_path,
            total_vertical_ft=total_vert,
            total_time_min=total_time,
            run_uniqueness_ratio=uniqueness,
            runtime_sec=runtime,
            is_continuous_path=True,
            start_node=self.start_node,
            end_node=best_path[-1].v if best_path else self.start_node,
        )


class QUBOSimulatedAnnealingRouter:
    """Vector Simulated Annealing operating on the exact QUBO objective function."""

    def __init__(
        self,
        qubo_matrix: np.ndarray,
        linear_terms: np.ndarray,
        edges: List[AlpineEdge],
        n_iterations: int = 3000,
        temp_initial: float = 120.0,
        cooling_rate: float = 0.996,
        seed: int = 42,
    ):
        self.qubo = qubo_matrix
        self.linear = linear_terms
        self.edges = edges
        self.n_iter = n_iterations
        self.t0 = temp_initial
        self.alpha = cooling_rate
        self.rng = np.random.default_rng(seed)

    def _cost(self, x: np.ndarray) -> float:
        return float(x @ self.qubo @ x + self.linear @ x)

    def solve(self) -> BenchmarkResult:
        start_t = time.perf_counter()
        n = len(self.edges)
        current_state = self.rng.integers(0, 2, size=n)
        current_cost = self._cost(current_state)

        best_state = current_state.copy()
        best_cost = current_cost
        t = self.t0

        for _ in range(self.n_iter):
            idx = self.rng.integers(0, n)
            next_state = current_state.copy()
            next_state[idx] = 1 - next_state[idx]
            next_cost = self._cost(next_state)

            delta = next_cost - current_cost
            if delta < 0 or self.rng.random() < math_exp_safe(-delta / max(t, 1e-4)):
                current_state = next_state
                current_cost = next_cost

                if current_cost < best_cost:
                    best_cost = current_cost
                    best_state = current_state.copy()

            t *= self.alpha

        runtime = time.perf_counter() - start_t
        selected = [self.edges[i] for i in range(n) if best_state[i] == 1]
        total_vert = sum(e.vertical_drop for e in selected if e.edge_type == "run")
        total_time = sum(e.duration_min for e in selected)
        runs = [e.name for e in selected if e.edge_type == "run"]
        uniqueness = (len(set(runs)) / len(runs)) if runs else 1.0

        return BenchmarkResult(
            method_name="Simulated Annealing (QUBO Vector)",
            selected_edges=selected,
            total_vertical_ft=total_vert,
            total_time_min=total_time,
            run_uniqueness_ratio=uniqueness,
            runtime_sec=runtime,
            is_continuous_path=False,
        )


def math_exp_safe(val: float) -> float:
    """Safe exponential evaluation preventing overflow."""
    if val > 0:
        return 1.0
    if val < -700.0:
        return 0.0
    import math
    return math.exp(val)


# Aliases for backwards compatibility
GreedyAltitudeRouter = GreedyKnapsackRouter
SimulatedAnnealingRouter = QUBOSimulatedAnnealingRouter
