#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2025-10-24

Topology reconciliation: Compare actual topology changes vs. expected from detected events.
This helps identify discrepancies from mis-segmentations or missing event classifications.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
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
    """
    Calculate topology metrics for a single timepoint.

    Args:
        df: DataFrame with adjacency information for one timepoint

    Returns:
        Dictionary with num_tips, num_junctions, num_components
    """
    # Calculate degrees
    df = df.copy()
    df['degree'] = df['adjacencies'].apply(calculate_degree_from_adjacencies)

    # Count tips (degree 1) and junctions (degree 3+)
    num_tips = (df['degree'] == 1).sum()
    num_junctions = (df['degree'] >= 3).sum()

    # Count components
    num_components = df['component_num'].nunique() if 'component_num' in df.columns else 0

    return {
        'num_tips': num_tips,
        'num_junctions': num_junctions,
        'num_components': num_components
    }


def calculate_actual_topology_changes(combined_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate actual topology changes between consecutive timepoints.

    Args:
        combined_df: Combined DataFrame from timeseries_reader

    Returns:
        DataFrame with columns: time_point, delta_tips, delta_junctions, delta_components
    """
    time_points = sorted(combined_df['time_point'].unique())

    changes = []

    for i in range(len(time_points) - 1):
        t1, t2 = time_points[i], time_points[i + 1]

        df_t1 = combined_df[combined_df['time_point'] == t1]
        df_t2 = combined_df[combined_df['time_point'] == t2]

        metrics_t1 = calculate_topology_metrics(df_t1)
        metrics_t2 = calculate_topology_metrics(df_t2)

        changes.append({
            'transition': f'{t1}->{t2}',
            'time_point_1': t1,
            'time_point_2': t2,
            'tips_t1': metrics_t1['num_tips'],
            'tips_t2': metrics_t2['num_tips'],
            'delta_tips': metrics_t2['num_tips'] - metrics_t1['num_tips'],
            'junctions_t1': metrics_t1['num_junctions'],
            'junctions_t2': metrics_t2['num_junctions'],
            'delta_junctions': metrics_t2['num_junctions'] - metrics_t1['num_junctions'],
            'components_t1': metrics_t1['num_components'],
            'components_t2': metrics_t2['num_components'],
            'delta_components': metrics_t2['num_components'] - metrics_t1['num_components']
        })

    return pd.DataFrame(changes)


def calculate_expected_topology_changes(events_dict: Dict) -> Dict[str, Tuple[int, int]]:
    """
    Calculate expected topology changes from detected events.

    Event type topology effects:
    1. Tip-edge fusion: Δtips = -1, Δjunctions = +1
    2. Junction breakage: Δtips = +1, Δjunctions = -1
    3. Tip-tip fusion: Δtips = -2, Δjunctions = 0 
    4. Tip-tip fission: Δtips = +2, Δjunctions = 0 
    5. Extrusion: Δtips = +1, Δjunctions = +1
    6. Retraction: Δtips = -1, Δjunctions = -1

    Args:
        events_dict: Dictionary from analyze_timeseries_events

    Returns:
        Dictionary with total expected delta_tips and delta_junctions
    """
    stats = events_dict.get('summary_statistics', {})

    # Count each event type
    n_tip_edge_fusion = stats.get('total_tip_edge_fusion', 0)
    n_junction_breakage = stats.get('total_junction_breakage', 0)
    n_tip_tip_fusion = stats.get('total_tip_tip_fusion', 0)
    n_tip_tip_fission = stats.get('total_tip_tip_fission', 0)
    n_extrusion = stats.get('total_extrusion', 0)
    n_retraction = stats.get('total_retraction', 0)

    # Calculate expected changes
    expected_delta_tips = (
        -1 * n_tip_edge_fusion +
        1 * n_junction_breakage +
        -2 * n_tip_tip_fusion +
        2 * n_tip_tip_fission +
        1 * n_extrusion +
        -1 * n_retraction
    )

    expected_delta_junctions = (
        1 * n_tip_edge_fusion +
        -1 * n_junction_breakage +
        0 * n_tip_tip_fusion +  
        0 * n_tip_tip_fission + 
        1 * n_extrusion +
        -1 * n_retraction
    )

    return {
        'expected_delta_tips': expected_delta_tips,
        'expected_delta_junctions': expected_delta_junctions,
        'event_counts': {
            'tip_edge_fusion': n_tip_edge_fusion,
            'junction_breakage': n_junction_breakage,
            'tip_tip_fusion': n_tip_tip_fusion,
            'tip_tip_fission': n_tip_tip_fission,
            'extrusion': n_extrusion,
            'retraction': n_retraction
        }
    }


def reconcile_topology_and_events(combined_df: pd.DataFrame, events_dict: Dict) -> pd.DataFrame:
    """
    Reconcile actual topology changes with expected changes from detected events.

    Args:
        combined_df: Combined DataFrame from timeseries_reader
        events_dict: Dictionary from analyze_timeseries_events

    Returns:
        DataFrame with reconciliation results showing discrepancies
    """
    # Get actual changes
    actual_changes_df = calculate_actual_topology_changes(combined_df)

    # Get expected changes (total across all transitions)
    expected = calculate_expected_topology_changes(events_dict)

    # Calculate total actual changes
    total_actual_delta_tips = actual_changes_df['delta_tips'].sum()
    total_actual_delta_junctions = actual_changes_df['delta_junctions'].sum()

    # Calculate discrepancies
    discrepancy_tips = total_actual_delta_tips - expected['expected_delta_tips']
    discrepancy_junctions = total_actual_delta_junctions - expected['expected_delta_junctions']

    # Create summary
    summary = {
        'metric': ['Tips', 'Junctions'],
        'actual_change': [total_actual_delta_tips, total_actual_delta_junctions],
        'expected_from_events': [expected['expected_delta_tips'], expected['expected_delta_junctions']],
        'discrepancy': [discrepancy_tips, discrepancy_junctions],
        'percent_explained': [
            100 * expected['expected_delta_tips'] / total_actual_delta_tips if total_actual_delta_tips != 0 else 0,
            100 * expected['expected_delta_junctions'] / total_actual_delta_junctions if total_actual_delta_junctions != 0 else 0
        ]
    }

    summary_df = pd.DataFrame(summary)

    return {
        'summary': summary_df,
        'actual_changes_by_transition': actual_changes_df,
        'expected_totals': expected,
        'event_counts': expected['event_counts']
    }


def print_reconciliation_report(reconciliation: Dict):
    """
    Print a detailed reconciliation report.

    Args:
        reconciliation: Output from reconcile_topology_and_events
    """
    print("\n" + "="*70)
    print("TOPOLOGY RECONCILIATION REPORT")
    print("="*70)

    print("\n1. DETECTED EVENT COUNTS:")
    print("-" * 50)
    for event_type, count in reconciliation['event_counts'].items():
        print(f"  {event_type:25s}: {count:4d}")

    print("\n2. TOPOLOGY CHANGES SUMMARY:")
    print("-" * 50)
    summary_df = reconciliation['summary']
    for _, row in summary_df.iterrows():
        print(f"\n  {row['metric']}:")
        print(f"    Actual change:          {row['actual_change']:+6.0f}")
        print(f"    Expected from events:   {row['expected_from_events']:+6.0f}")
        print(f"    Discrepancy:            {row['discrepancy']:+6.0f}")
        print(f"    Percent explained:      {row['percent_explained']:6.1f}%")

    print("\n3. CHANGES BY TRANSITION:")
    print("-" * 50)
    changes_df = reconciliation['actual_changes_by_transition']
    print(changes_df[['transition', 'delta_tips', 'delta_junctions', 'delta_components']].to_string(index=False))

    print("\n4. INTERPRETATION:")
    print("-" * 50)
    summary_df = reconciliation['summary']
    for _, row in summary_df.iterrows():
        metric = row['metric']
        discrepancy = row['discrepancy']
        if abs(discrepancy) < 0.1:
            print(f"  {metric}: ✓ Events fully explain topology changes")
        elif discrepancy > 0:
            print(f"  {metric}: ⚠ {abs(discrepancy):.0f} more {metric.lower()} than events predict")
            print(f"           → Possible missing events or mis-segmentation")
        else:
            print(f"  {metric}: ⚠ {abs(discrepancy):.0f} fewer {metric.lower()} than events predict")
            print(f"           → Possible spurious event detection")

    print("\n" + "="*70)


if __name__ == "__main__":
    import sys
    from .timeseries_reader_with_dynamics import read_timeseries_csvs_with_dynamics
    from .event_detector import analyze_timeseries_events

    if len(sys.argv) < 2:
        print("Usage: python topology_reconciliation.py <base_folder_path> [distance_threshold]")
        sys.exit(1)

    base_folder = sys.argv[1]
    distance_threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0

    print("Loading time series data...")
    combined_df = read_timeseries_csvs_with_dynamics(base_folder)

    print("Detecting events...")
    events = analyze_timeseries_events(combined_df, distance_threshold)

    print("Reconciling topology changes with detected events...")
    reconciliation = reconcile_topology_and_events(combined_df, events)

    print_reconciliation_report(reconciliation)

    # Save to CSV
    output_folder = base_folder
    reconciliation['summary'].to_csv(f'{output_folder}/topology_reconciliation_summary.csv', index=False)
    reconciliation['actual_changes_by_transition'].to_csv(f'{output_folder}/topology_changes_by_transition.csv', index=False)
    print(f"\nResults saved to {output_folder}/")
