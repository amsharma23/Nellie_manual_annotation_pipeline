#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2025-10-24

Topology-driven event inference: Infer events from topology changes.
This reverses the typical approach by starting from actual topology changes
and solving for event counts that explain the observed changes.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.optimize import linprog, minimize
import ast


def calculate_degree_from_adjacencies(adj_str):
    """Calculate node degree from adjacency list string."""
    try:
        if isinstance(adj_str, str):
            adj_list = ast.literal_eval(adj_str)
        elif isinstance(adj_str, list):
            adj_list = adj_str
        else:
            return 0
        return len(adj_list)
    except:
        return 0


def calculate_topology_metrics(df: pd.DataFrame) -> Dict[str, int]:
    """Calculate topology metrics for a single timepoint."""
    df = df.copy()
    df['degree'] = df['adjacencies'].apply(calculate_degree_from_adjacencies)

    num_tips = (df['degree'] == 1).sum()
    num_junctions = (df['degree'] >= 3).sum()
    num_components = df['component_num'].nunique() if 'component_num' in df.columns else 0

    return {
        'num_tips': num_tips,
        'num_junctions': num_junctions,
        'num_components': num_components
    }


def infer_events_from_topology_change(
    delta_tips: int,
    delta_junctions: int,
    detected_events: Optional[Dict[str, int]] = None,
    method: str = 'minimize_discrepancy'
) -> Dict[str, any]:
    """
    Infer event counts from topology changes using optimization.

    Event topology effects:
    1. Tip-edge fusion: Δtips = -1, Δjunctions = +1
    2. Junction breakage: Δtips = +1, Δjunctions = -1
    3. Tip-tip fusion: Δtips = -2, Δjunctions = 0
    4. Tip-tip fission: Δtips = +2, Δjunctions = 0
    5. Extrusion: Δtips = +1, Δjunctions = +1
    6. Retraction: Δtips = -1, Δjunctions = -1

    System of equations:
    -n1 + n2 - 2*n3 + 2*n4 + n5 - n6 = Δtips
     n1 - n2 + 0*n3 + 0*n4 + n5 - n6 = Δjunctions

    Where n1, n2, ..., n6 are event counts.

    Args:
        delta_tips: Actual change in number of tips
        delta_junctions: Actual change in number of junctions
        detected_events: Optional dict with detected event counts to use as priors
        method: 'minimize_total' or 'minimize_discrepancy'

    Returns:
        Dictionary with inferred event counts and quality metrics
    """

    # Define the topology effect matrix
    # Rows: [delta_tips, delta_junctions]
    # Cols: [n1, n2, n3, n4, n5, n6] = [tip-edge fusion, junction breakage, tip-tip fusion, tip-tip fission, extrusion, retraction]
    A = np.array([
        [-1,  1, -2,  2,  1, -1],  # Tips equation
        [ 1, -1,  0,  0,  1, -1]   # Junctions equation
    ])

    b = np.array([delta_tips, delta_junctions])

    if method == 'minimize_total':
        # Objective: minimize total number of events
        # This finds the sparsest solution (fewest total events)
        c = np.ones(6)  # Coefficients for objective function

        # Solve using linear programming (minimize c^T x subject to Ax = b, x >= 0)
        result = linprog(
            c=c,
            A_eq=A,
            b_eq=b,
            bounds=[(0, None)] * 6,  # All event counts must be non-negative
            method='highs'
        )

        if result.success:
            inferred_counts = np.round(result.x).astype(int)
        else:
            # If no exact solution, use least squares
            inferred_counts = np.maximum(0, np.linalg.lstsq(A, b, rcond=None)[0]).round().astype(int)

    elif method == 'minimize_discrepancy' and detected_events is not None:
        # Objective: minimize discrepancy from detected events
        # This adjusts detected events to match topology changes

        detected_vector = np.array([
            detected_events.get('tip_edge_fusion', 0),
            detected_events.get('junction_breakage', 0),
            detected_events.get('tip_tip_fusion', 0),
            detected_events.get('tip_tip_fission', 0),
            detected_events.get('extrusion', 0),
            detected_events.get('retraction', 0)
        ])

        def objective(x):
            # Minimize squared difference from detected events
            return np.sum((x - detected_vector) ** 2)

        def constraint_tips(x):
            return A[0] @ x - b[0]

        def constraint_junctions(x):
            return A[1] @ x - b[1]

        constraints = [
            {'type': 'eq', 'fun': constraint_tips},
            {'type': 'eq', 'fun': constraint_junctions}
        ]

        bounds = [(0, None)] * 6

        result = minimize(
            objective,
            x0=detected_vector,
            bounds=bounds,
            constraints=constraints,
            method='SLSQP'
        )

        if result.success:
            inferred_counts = np.round(result.x).astype(int)
        else:
            # Fallback to detected events if optimization fails
            inferred_counts = detected_vector

    else:
        # Default: least squares solution
        inferred_counts = np.maximum(0, np.linalg.lstsq(A, b, rcond=None)[0]).round().astype(int)

    # Verify the solution
    predicted_delta_tips = A[0] @ inferred_counts
    predicted_delta_junctions = A[1] @ inferred_counts

    residual_tips = abs(predicted_delta_tips - delta_tips)
    residual_junctions = abs(predicted_delta_junctions - delta_junctions)

    return {
        'inferred_event_counts': {
            'tip_edge_fusion': int(inferred_counts[0]),
            'junction_breakage': int(inferred_counts[1]),
            'tip_tip_fusion': int(inferred_counts[2]),
            'tip_tip_fission': int(inferred_counts[3]),
            'extrusion': int(inferred_counts[4]),
            'retraction': int(inferred_counts[5])
        },
        'topology_match': {
            'actual_delta_tips': delta_tips,
            'actual_delta_junctions': delta_junctions,
            'predicted_delta_tips': int(predicted_delta_tips),
            'predicted_delta_junctions': int(predicted_delta_junctions),
            'residual_tips': int(residual_tips),
            'residual_junctions': int(residual_junctions),
            'perfect_match': (residual_tips == 0 and residual_junctions == 0)
        },
        'optimization_method': method
    }


def infer_events_for_timeseries(
    combined_df: pd.DataFrame,
    detected_events: Optional[Dict] = None,
    method: str = 'minimize_discrepancy'
) -> pd.DataFrame:
    """
    Infer events for each transition in a time series.

    Args:
        combined_df: Combined DataFrame from timeseries_reader
        detected_events: Optional dict from analyze_timeseries_events
        method: Optimization method

    Returns:
        DataFrame with inferred event counts per transition
    """
    time_points = sorted(combined_df['time_point'].unique())

    results = []

    for i in range(len(time_points) - 1):
        t1, t2 = time_points[i], time_points[i + 1]

        df_t1 = combined_df[combined_df['time_point'] == t1]
        df_t2 = combined_df[combined_df['time_point'] == t2]

        metrics_t1 = calculate_topology_metrics(df_t1)
        metrics_t2 = calculate_topology_metrics(df_t2)

        delta_tips = metrics_t2['num_tips'] - metrics_t1['num_tips']
        delta_junctions = metrics_t2['num_junctions'] - metrics_t1['num_junctions']

        # Infer events for this transition
        inference = infer_events_from_topology_change(
            delta_tips,
            delta_junctions,
            detected_events=detected_events.get('event_counts') if detected_events else None,
            method=method
        )

        result_row = {
            'transition': f'{t1}->{t2}',
            'time_point_1': t1,
            'time_point_2': t2,
            'delta_tips': delta_tips,
            'delta_junctions': delta_junctions,
            **inference['inferred_event_counts'],
            'perfect_match': inference['topology_match']['perfect_match'],
            'residual_tips': inference['topology_match']['residual_tips'],
            'residual_junctions': inference['topology_match']['residual_junctions']
        }

        results.append(result_row)

    return pd.DataFrame(results)


def compare_detected_vs_inferred(
    detected_events: Dict,
    inferred_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compare detected events vs. topology-inferred events.

    Args:
        detected_events: Dictionary from analyze_timeseries_events
        inferred_df: DataFrame from infer_events_for_timeseries

    Returns:
        Comparison DataFrame
    """
    event_types = [
        'tip_edge_fusion',
        'junction_breakage',
        'tip_tip_fusion',
        'tip_tip_fission',
        'extrusion',
        'retraction'
    ]

    comparison = []

    for event_type in event_types:
        detected_count = detected_events.get('summary_statistics', {}).get(f'total_{event_type}', 0)
        inferred_count = inferred_df[event_type].sum()

        comparison.append({
            'event_type': event_type,
            'detected': detected_count,
            'inferred_from_topology': inferred_count,
            'difference': inferred_count - detected_count,
            'percent_difference': 100 * (inferred_count - detected_count) / detected_count if detected_count > 0 else np.inf
        })

    return pd.DataFrame(comparison)


def print_inference_report(inferred_df: pd.DataFrame, comparison_df: Optional[pd.DataFrame] = None):
    """
    Print a detailed inference report.

    Args:
        inferred_df: DataFrame from infer_events_for_timeseries
        comparison_df: Optional comparison DataFrame
    """
    print("\n" + "="*70)
    print("TOPOLOGY-DRIVEN EVENT INFERENCE REPORT")
    print("="*70)

    print("\n1. INFERRED EVENTS BY TRANSITION:")
    print("-" * 70)
    display_cols = [
        'transition', 'delta_tips', 'delta_junctions',
        'tip_edge_fusion', 'junction_breakage', 'tip_tip_fusion',
        'tip_tip_fission', 'extrusion', 'retraction'
    ]
    print(inferred_df[display_cols].to_string(index=False))

    print("\n2. TOPOLOGY MATCH QUALITY:")
    print("-" * 70)
    perfect_matches = inferred_df['perfect_match'].sum()
    total_transitions = len(inferred_df)
    print(f"  Perfect matches: {perfect_matches}/{total_transitions} transitions")
    print(f"  Success rate: {100 * perfect_matches / total_transitions:.1f}%")

    if inferred_df['residual_tips'].sum() > 0 or inferred_df['residual_junctions'].sum() > 0:
        print(f"\n  Total residual tips: {inferred_df['residual_tips'].sum()}")
        print(f"  Total residual junctions: {inferred_df['residual_junctions'].sum()}")

    print("\n3. TOTAL INFERRED EVENTS:")
    print("-" * 70)
    event_types = [
        'tip_edge_fusion', 'junction_breakage', 'tip_tip_fusion',
        'tip_tip_fission', 'extrusion', 'retraction'
    ]
    for event_type in event_types:
        total = inferred_df[event_type].sum()
        print(f"  {event_type:25s}: {total:4d}")

    if comparison_df is not None:
        print("\n4. COMPARISON: DETECTED vs. INFERRED:")
        print("-" * 70)
        for _, row in comparison_df.iterrows():
            print(f"\n  {row['event_type']}:")
            print(f"    Detected:     {row['detected']:4d}")
            print(f"    Inferred:     {row['inferred_from_topology']:4d}")
            print(f"    Difference:   {row['difference']:+4d}")
            if np.isfinite(row['percent_difference']):
                print(f"    % Difference: {row['percent_difference']:+6.1f}%")

    print("\n" + "="*70)


if __name__ == "__main__":
    import sys
    from .timeseries_reader_with_dynamics import read_timeseries_csvs_with_dynamics
    from .event_detector import analyze_timeseries_events

    if len(sys.argv) < 2:
        print("Usage: python topology_driven_inference.py <base_folder_path> [method]")
        print("  method: 'minimize_total' or 'minimize_discrepancy' (default)")
        sys.exit(1)

    base_folder = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else 'minimize_discrepancy'

    print("Loading time series data...")
    combined_df = read_timeseries_csvs_with_dynamics(base_folder)

    print("Detecting events using spatial matching...")
    detected_events = analyze_timeseries_events(combined_df, distance_threshold=5.0)

    print(f"\nInferring events from topology changes (method: {method})...")
    inferred_df = infer_events_for_timeseries(combined_df, detected_events, method=method)

    print("\nComparing detected vs. inferred events...")
    comparison_df = compare_detected_vs_inferred(detected_events, inferred_df)

    print_inference_report(inferred_df, comparison_df)

    # Save results
    output_folder = base_folder
    inferred_df.to_csv(f'{output_folder}/topology_inferred_events.csv', index=False)
    comparison_df.to_csv(f'{output_folder}/detected_vs_inferred_comparison.csv', index=False)
    print(f"\nResults saved to {output_folder}/")
