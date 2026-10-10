"""Comprehensive verification of Classical Greedy & Simulated Annealing baselines on Winter Park Resort."""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from quasar.graph import create_winter_park_resort
from quasar.qaoa_router import AlpineQAOARouter
from quasar.classical_benchmarks import (
    GreedyTrajectoryRouter,
    GreedyKnapsackRouter,
    SimulatedAnnealingTrajectoryRouter,
    QUBOSimulatedAnnealingRouter,
)


def verify_winter_park_baselines():
    print("=" * 90)
    print("QUASAR CLASSICAL BASELINES VERIFICATION: WINTER PARK RESORT, COLORADO")
    print("Comparing Continuous Trajectory Greedy vs. Simulated Annealing vs. Knapsack Heuristics")
    print("=" * 90)

    # 1. Load Winter Park Topology
    resort = create_winter_park_resort()
    edges = resort.get_edges_list()
    runs = [e for e in edges if e.edge_type == "run"]
    lifts = [e for e in edges if e.edge_type == "lift"]

    print(f"\nResort Dataset: {resort.name}")
    print(f"  • Total Decision Landmarks / Junctions: {len(resort.graph.nodes)}")
    print(f"  • Total Chairlifts / Gondolas:           {len(lifts)}")
    print(f"  • Total Downhill Ski Trails:            {len(runs)}")
    print(f"  • Total Theoretical Available Descent:   {sum(r.vertical_drop for r in runs):,.0f} ft")

    # Time budget scenarios to verify
    test_budgets = [60.0, 120.0, 240.0]

    for budget in test_budgets:
        hours = budget / 60.0
        print("\n" + "#" * 90)
        print(f"SCENARIO: {hours:.1f}-HOUR TIME BUDGET ({budget:.0f} Minutes) - START AT WINTER PARK BASE")
        print("#" * 90)

        # Baseline 1: Continuous Trajectory Greedy
        greedy_traj = GreedyTrajectoryRouter(resort, start_node="WP_BASE", target_time_min=budget)
        res_greedy_traj = greedy_traj.solve()

        # Baseline 2: Continuous Trajectory Simulated Annealing
        sa_traj = SimulatedAnnealingTrajectoryRouter(
            resort,
            start_node="WP_BASE",
            target_time_min=budget,
            n_iterations=6000,
            t_initial=250.0,
            cooling_rate=0.998,
            seed=42,
        )
        res_sa_traj = sa_traj.solve()

        # Baseline 3: Unconstrained Greedy Knapsack (Theoretical ceiling)
        greedy_knap = GreedyKnapsackRouter(edges, target_time_min=budget)
        res_greedy_knap = greedy_knap.solve()

        # Baseline 4: QUBO Simulated Annealing (on candidate edges)
        # Build compact QUBO for vector annealing
        qaoa_router = AlpineQAOARouter(
            resort,
            candidate_edges=edges,
            target_time_min=budget,
            weight_vertical=1.0,
            penalty_duplicate=100.0,
            penalty_time=2.5,
        )
        sa_qubo = QUBOSimulatedAnnealingRouter(
            qaoa_router.qubo_matrix,
            qaoa_router.linear_terms,
            edges,
            n_iterations=5000,
            seed=42,
        )
        res_sa_qubo = sa_qubo.solve()

        # Print Comparison Table
        results = [res_greedy_traj, res_sa_traj, res_sa_qubo, res_greedy_knap]
        print(f"\n{'Algorithm Baseline':<36} | {'Vertical (ft)':<13} | {'Time (min)':<10} | {'Uniqueness %':<12} | {'Segments':<8} | {'Continuous?':<11} | {'Runtime (ms)':<12}")
        print("-" * 115)
        for r in results:
            cont_str = "YES" if r.is_continuous_path else "NO (Vector)"
            print(
                f"{r.method_name:<36} | {r.vertical_drop_ft if hasattr(r, 'vertical_drop_ft') else r.total_vertical_ft:>11,.0f} ft | "
                f"{r.total_time_min:>8.1f} m | {r.run_uniqueness_ratio * 100:>10.1f}% | "
                f"{len(r.selected_edges):>8d} | {cont_str:<11} | {r.runtime_sec * 1000:>10.2f} ms"
            )

        # Print Details of Best Continuous Trajectory
        best_continuous = res_sa_traj if res_sa_traj.total_vertical_ft >= res_greedy_traj.total_vertical_ft else res_greedy_traj
        print(f"\n>>> Best Physical Continuous Route ({best_continuous.method_name}):")
        accum_vert = 0.0
        for i, edge in enumerate(best_continuous.selected_edges, 1):
            accum_vert += edge.vertical_drop
            direction = "Downhill Run" if edge.edge_type == "run" else "Uphill Lift"
            print(
                f"    {i:2d}. [{direction:<12}] {edge.name:<25} ({edge.u:<14} -> {edge.v:<14}) | "
                f"Vert: {edge.vertical_drop:>4.0f}ft | Elev Gain: {edge.elevation_gain:>4.0f}ft | Time: {edge.duration_min:>4.1f}m"
            )
        print(f"    ==> Total Vertical Descent: {best_continuous.total_vertical_ft:,.0f} ft in {best_continuous.total_time_min:.1f} minutes.")
        print(f"    ==> Run Uniqueness: {best_continuous.run_uniqueness_ratio * 100:.1f}% unique trails skied.")

    print("\n" + "=" * 90)
    print("VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 90)


if __name__ == "__main__":
    verify_winter_park_baselines()
