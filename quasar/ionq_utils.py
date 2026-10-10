"""IonQ simulator and hardware integration utilities.

Adheres to Qollab Hackathon single-job execution constraints and native gate transpilation:
- Native Trapped-Ion basis: R_XX (Mølmer-Sørensen), R_z, R_y, R_x.
- Single-job batch execution on Qollab free simulators.
- Single-circuit composition for IonQ backends ('put everything an IonQ run measures into one circuit').
"""

from typing import Any, Dict, List, Tuple
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit.quantum_info import hellinger_fidelity
from qiskit_aer import AerSimulator


class IonQBackendAdapter:
    """Helper to adapt Qiskit QAOA circuits for IonQ Trapped-Ion simulators and devices."""

    # Native gate basis for IonQ systems (Mølmer-Sørensen entangling gates + single-qubit rotations)
    IONQ_BASIS_GATES = ["rxx", "rz", "ry", "rx", "measure"]

    @classmethod
    def transpile_for_ionq(
        cls, circuit: QuantumCircuit, optimization_level: int = 3
    ) -> QuantumCircuit:
        """Transpiles a QAOA circuit into the IonQ native trapped-ion gate basis.
        
        Replaces standard CNOT/CZ ladders with direct all-to-all R_XX interactions,
        significantly reducing circuit depth and eliminating SWAP overhead.
        """
        transpiled_qc = transpile(
            circuit,
            basis_gates=cls.IONQ_BASIS_GATES,
            optimization_level=optimization_level,
        )
        return transpiled_qc

    @classmethod
    def verify_transpilation_fidelity(
        cls, original_circuit: QuantumCircuit, ionq_circuit: QuantumCircuit, shots: int = 4096
    ) -> Tuple[float, Dict[str, Any]]:
        """Verifies that the IonQ R_XX transpiled circuit produces identical measurement statistics.
        
        Computes Hellinger fidelity and Total Variation Distance between native Qiskit
        and IonQ R_XX transpiled implementations.
        """
        sim = AerSimulator()
        res_orig = sim.run(original_circuit, shots=shots).result().get_counts()
        res_ionq = sim.run(ionq_circuit, shots=shots).result().get_counts()

        fidelity = float(hellinger_fidelity(res_orig, res_ionq))

        # Total variation distance: 0.5 * sum |p1(x) - p2(x)|
        all_keys = set(res_orig.keys()) | set(res_ionq.keys())
        tvd = 0.5 * sum(
            abs(res_orig.get(k, 0) / shots - res_ionq.get(k, 0) / shots) for k in all_keys
        )

        metrics = {
            "hellinger_fidelity": fidelity,
            "total_variation_distance": tvd,
            "original_gate_counts": dict(original_circuit.count_ops()),
            "ionq_gate_counts": dict(ionq_circuit.count_ops()),
            "original_depth": original_circuit.depth(),
            "ionq_depth": ionq_circuit.depth(),
        }
        return fidelity, metrics

    @classmethod
    def bundle_single_job_list(
        cls, circuits: List[QuantumCircuit]
    ) -> List[QuantumCircuit]:
        """Prepares a multi-circuit batch executed within a single backend.run() call.
        
        Complies with Qollab local free simulator specifications:
        'Local simulators accept as many jobs per run as you send.'
        """
        return list(circuits)

    @classmethod
    def bundle_unified_single_circuit(
        cls, circuits: List[QuantumCircuit], prefix: str = "exp"
    ) -> QuantumCircuit:
        """Composes multiple circuits into ONE unified QuantumCircuit with disjoint registers.
        
        Strictly satisfies the IonQ simulator constraint on Qollab:
        'IonQ backends accept one per run, so put everything an IonQ run measures into one circuit.'
        """
        if not circuits:
            raise ValueError("No circuits provided to bundle.")
        if len(circuits) == 1:
            return circuits[0]

        # Construct unified circuit with disjoint quantum and classical registers
        q_regs = []
        c_regs = []
        for i, circ in enumerate(circuits):
            q_regs.append(QuantumRegister(circ.num_qubits, f"q_{prefix}_{i}"))
            c_regs.append(ClassicalRegister(circ.num_clbits, f"c_{prefix}_{i}"))

        unified_qc = QuantumCircuit(*q_regs, *c_regs)

        for i, circ in enumerate(circuits):
            q_reg = q_regs[i]
            c_reg = c_regs[i]
            # Copy circuit operations
            unified_qc.compose(
                circ,
                qubits=list(q_reg),
                clbits=list(c_reg),
                inplace=True,
            )

        return unified_qc

    @classmethod
    def demux_unified_counts(
        cls, counts: Dict[str, int], num_circuits: int
    ) -> List[Dict[str, int]]:
        """Demultiplexes space-separated measurement keys from a unified single circuit."""
        sub_counts: List[Dict[str, int]] = [{} for _ in range(num_circuits)]

        for key, count in counts.items():
            # Qiskit space-separates classical registers in reverse order: reg_{N-1} ... reg_0
            tokens = key.split(" ")
            # Reverse tokens to match circuit index 0, 1, ...
            tokens = list(reversed(tokens))
            for i in range(min(num_circuits, len(tokens))):
                sub_counts[i][tokens[i]] = sub_counts[i].get(tokens[i], 0) + count

        return sub_counts
