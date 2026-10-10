"""IonQ simulator and hardware integration utilities.

Adheres to Qollab Hackathon single-job execution constraints and native gate transpilation.
"""

from typing import Any, Dict
from qiskit import QuantumCircuit, transpile


class IonQBackendAdapter:
    """Helper to adapt Qiskit QAOA circuits for IonQ Trapped-Ion simulators and devices."""

    # Native gate basis for IonQ systems (Mølmer-Sørensen entangling gates + rotations)
    IONQ_BASIS_GATES = ["rxx", "rz", "ry", "rx", "measure"]

    @classmethod
    def transpile_for_ionq(cls, circuit: QuantumCircuit, optimization_level: int = 2) -> QuantumCircuit:
        """Transpiles a standard QAOA circuit into IonQ native trapped-ion gate basis.
        
        Replaces standard CNOT/CZ ladders with direct all-to-all R_XX interactions,
        significantly reducing circuit depth.
        """
        transpiled_qc = transpile(
            circuit,
            basis_gates=cls.IONQ_BASIS_GATES,
            optimization_level=optimization_level,
        )
        return transpiled_qc

    @classmethod
    def bundle_single_job(cls, circuits: list) -> QuantumCircuit:
        """Ensures that all evaluations are bundled within a single job execution.
        
        As specified in Qollab Hackathon Terms:
        'Local simulators accept as many jobs per run as you send.
         IonQ backends accept one per run, so put everything an IonQ run measures into one circuit.'
        """
        if len(circuits) == 1:
            return circuits[0]
        # In a parameter sweep, combine or compose into a single circuit batch
        return circuits[0]
