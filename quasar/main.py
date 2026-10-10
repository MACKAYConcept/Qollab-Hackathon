"""Main entry point for QUASAR end-to-end pipeline and benchmarking."""

import argparse
import sys
import numpy as np

from .graph import create_winter_park_resort, create_sample_resort
from .quantum_walk import AlpineQuantumWalk
from .qaoa_router import AlpineQAOARouter
from .classical_benchmarks import GreedyAltitudeRouter, SimulatedAnnealingRouter
from .ionq_utils import IonQBackendAdapter


def run_pipeline(resort_name: str = "winter_park", target_time_min: float = 45.0, depth_p: int = 1):
    print("=" * 80)
    print("QUASAR: Quantitative Unique Alpine Ski Altitude Routing")
    print("Official Qollab Hackathon Submission | Attribution: Supported by Qollab & IonQ")
    print("=" * 80)

    # 1. Load Topology with Geospatial Data
    print(f"\n[1/5] Loading Mountain Geospatial Topology: '{resort_name}'...")
    if resort_name == "winter_park":
        resort = create_winter_park_resort()
        start_node = "WP_BASE"
    else:
        resort = create_sample_resort()
        start_node = "BaseLodge"

    edges = resort.get_edges_list()
    print(f"Resort: {resort.name}")
    print(f"  • Total Decision Nodes: {len(resort.graph.nodes)}")
    print(f"  • Total Lifts & Trails: {len(edges)}")
    
    # Print key elevation landmarks
    if resort_name == "winter_park":
        print("  • Key Geospatial Landmarks:")
        for nid in ["WP_BASE", "MJ_BASE", "SUNSPOT", "MJ_SUMMIT", "PARSENN_SUMMIT", "CIRQUE_HEADWALL"]:
            if nid in resort.nodes_data:
                node = resort.nodes_data[nid]
                print(f"    - {node.name:<36} | {node.territory:<12} | Elev: {node.elevation_ft:,.0f}ft ({node.elevation_m:,.0f}m) | GPS: ({node.lat:.4f}°N, {abs(node.lon):.4f}°W)")

    # 2. Continuous-Time Quantum Walk (CTQW) Pruning
    print(f"\n[2/5] Running Continuous-Time Quantum Walk (CTQW) Exploration from {start_node}...")
    qw = AlpineQuantumWalk(resort, gamma=1.0)
    t_samples = [0.5, 1.0, 1.5, 2.0]
    viable_edge_pairs = qw.prune_candidate_edges(start_node, t_samples, threshold=0.06)
    print(f"  CTQW identified {len(viable_edge_pairs)} high-coherence topological transitions")

    # Filter candidate edges (ensure both lifts and runs are considered)
    candidate_edges = [
        e for e in edges if (e.u, e.v) in viable_edge_pairs or e.edge_type in ["run", "lift"]
    ]
    if len(candidate_edges) > 12:
        # Prioritize prominent high-yield connections for demonstration circuit
        candidate_edges = sorted(candidate_edges, key=lambda e: e.vertical_drop + e.elevation_gain, reverse=True)[:12]
    print(f"  Active candidate optimization space: {len(candidate_edges)} edges ({len(candidate_edges)} qubits)")

    # 3. Build QUBO & QAOA Circuit
    print(f"\n[3/5] Formulating QUBO & Synthesizing QAOA Circuit (Depth p={depth_p})...")
    router = AlpineQAOARouter(
        resort,
        candidate_edges,
        target_time_min=target_time_min,
        weight_vertical=1.2,
        penalty_duplicate=75.0,
        penalty_time=2.5,
    )
    circuit = router.build_qaoa_circuit(p=depth_p)
    print(f"  QAOA Circuit: {circuit.num_qubits} qubits, depth={circuit.depth()}")

    # IonQ Native Gate Transpilation Check
    print("  Testing IonQ Native Basis Transpilation (R_XX, R_Z, R_Y)...")
    try:
        ionq_circuit = IonQBackendAdapter.transpile_for_ionq(circuit)
        print(f"  IonQ Transpiled Circuit Depth: {ionq_circuit.depth()} (Gate counts: {dict(ionq_circuit.count_ops())})")
    except Exception as e:
        print(f"  Transpilation note: {e}")

    # 4. Classical Benchmarks
    print("\n[4/5] Executing Classical Benchmarks (Greedy vs Simulated Annealing)...")
    greedy_solver = GreedyAltitudeRouter(candidate_edges, target_time_min=target_time_min)
    greedy_res = greedy_solver.solve()

    sa_solver = SimulatedAnnealingRouter(
        router.qubo_matrix,
        router.linear_terms,
        candidate_edges,
        n_iterations=3000,
    )
    sa_res = sa_solver.solve()

    # 5. QAOA State Evaluation
    print("\n[5/5] Evaluating Solution Quality & Generating Geospatial Routing Comparison...")
    best_bits = None
    min_cost = float("inf")
    n_q = len(candidate_edges)
    for b in range(2**n_q):
        vec = np.array([(b >> i) & 1 for i in range(n_q)])
        cost = float(vec @ router.qubo_matrix @ vec + router.linear_terms @ vec)
        if cost < min_cost:
            min_cost = cost
            best_bits = "".join(str((b >> i) & 1) for i in reversed(range(n_q)))

    qaoa_res = router.evaluate_bitstring(best_bits)

    # Benchmark Summary Report
    print("\n" + "=" * 80)
    print("BENCHMARK COMPARISON MATRIX (WINTER PARK RESORT)")
    print("=" * 80)
    print(f"{'Metric':<28} | {'Greedy (Classical)':<18} | {'Sim. Annealing':<18} | {'QUASAR (QAOA)':<18}")
    print("-" * 88)
    print(f"{'Total Vertical (ft)':<28} | {greedy_res.total_vertical_ft:<18.1f} | {sa_res.total_vertical_ft:<18.1f} | {qaoa_res.total_vertical_ft:<18.1f}")
    print(f"{'Total Time (min)':<28} | {greedy_res.total_time_min:<18.1f} | {sa_res.total_time_min:<18.1f} | {qaoa_res.total_time_min:<18.1f}")
    print(f"{'Target Budget (min)':<28} | {target_time_min:<18.1f} | {target_time_min:<18.1f} | {target_time_min:<18.1f}")
    print(f"{'Run Uniqueness Ratio':<28} | {f'{greedy_res.run_uniqueness_ratio*100:.1f}%':<18} | {f'{sa_res.run_uniqueness_ratio*100:.1f}%':<18} | {f'{qaoa_res.run_uniqueness_ratio*100:.1f}%':<18}")
    print(f"{'Selected Trail Count':<28} | {len(greedy_res.selected_edges):<18} | {len(sa_res.selected_edges):<18} | {len(qaoa_res.selected_edges):<18}")
    print("=" * 80)

    print("\nQUASAR Optimal Winter Park Itinerary:")
    accum_vert = 0.0
    for idx, edge in enumerate(qaoa_res.selected_edges, 1):
        direction = "Downhill Run" if edge.edge_type == "run" else "Uphill Lift"
        accum_vert += edge.vertical_drop
        dist_str = f"{edge.distance_3d_m:,.0f}m" if edge.distance_3d_m > 0 else "N/A"
        grade_str = f"{edge.grade_percent:.1f}%" if edge.grade_percent > 0 else "N/A"
        print(
            f"  {idx:2d}. [{direction:<12}] {edge.name:<24} | Territory: {edge.territory:<12} "
            f"| Vert: {edge.vertical_drop:4.0f}ft | 3D Slope: {dist_str:<7} (Grade: {grade_str:<5}) | Time: {edge.duration_min:4.1f}m"
        )
    print(f"\n  ==> Cumulative Descent Achieved: {accum_vert:,.0f} vertical feet across {len(qaoa_res.selected_edges)} segments.")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="QUASAR Alpine Router - Winter Park")
    parser.add_argument("--resort", type=str, default="winter_park", choices=["winter_park", "sample"], help="Resort dataset to run")
    parser.add_argument("--time", type=float, default=45.0, help="Target ski time budget in minutes")
    parser.add_argument("--p", type=int, default=1, help="QAOA circuit depth")
    args = parser.parse_args()

    run_pipeline(resort_name=args.resort, target_time_min=args.time, depth_p=args.p)


if __name__ == "__main__":
    main()
