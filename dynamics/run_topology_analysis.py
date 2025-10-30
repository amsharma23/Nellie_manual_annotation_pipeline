#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2025-10-24

@author: amansharma

Comprehensive script to run both traditional event detection and topology-driven analysis.
This helps identify discrepancies and validate event classifications.
"""

import sys
import os
import pandas as pd
from timeseries_reader_with_dynamics import read_timeseries_csvs
from event_detector import analyze_timeseries_events
from topology_reconciliation import reconcile_topology_and_events, print_reconciliation_report
from topology_driven_inference import (
    infer_events_for_timeseries,
    compare_detected_vs_inferred,
    print_inference_report
)


def run_comprehensive_analysis(base_folder: str, distance_threshold: float = 5.0, output_folder: str = None):
    """
    Run comprehensive topology and event analysis.

    This performs three analyses:
    1. Traditional event detection (spatial matching)
    2. Topology reconciliation (compare detected events to actual topology changes)
    3. Topology-driven inference (infer events from topology changes)

    Args:
        base_folder: Path to time series folder
        distance_threshold: Spatial matching threshold
        output_folder: Optional output folder (defaults to base_folder)
    """
    if output_folder is None:
        output_folder = base_folder

    os.makedirs(output_folder, exist_ok=True)

    print("="*80)
    print("COMPREHENSIVE TOPOLOGY & EVENT ANALYSIS")
    print("="*80)
    print(f"Base folder: {base_folder}")
    print(f"Distance threshold: {distance_threshold}")
    print(f"Output folder: {output_folder}")

    # Step 1: Load data
    print("\n" + "="*80)
    print("STEP 1: LOADING TIME SERIES DATA")
    print("="*80)
    combined_df = read_timeseries_csvs(base_folder)
    print(f"Loaded {len(combined_df)} nodes across {combined_df['time_point'].nunique()} time points")

    # Step 2: Traditional event detection
    print("\n" + "="*80)
    print("STEP 2: TRADITIONAL EVENT DETECTION (Spatial Matching)")
    print("="*80)
    detected_events = analyze_timeseries_events(combined_df, distance_threshold)

    print("\nDetected Event Summary:")
    stats = detected_events['summary_statistics']
    for event_type, count in stats.items():
        print(f"  {event_type:30s}: {count:4d}")
    print(f"  {'Total events':30s}: {sum(stats.values()):4d}")

    # Save detected events
    summary_df = pd.DataFrame([stats])
    summary_df.to_csv(os.path.join(output_folder, 'detected_events_summary.csv'), index=False)

    # Step 3: Topology reconciliation
    print("\n" + "="*80)
    print("STEP 3: TOPOLOGY RECONCILIATION")
    print("="*80)
    reconciliation = reconcile_topology_and_events(combined_df, detected_events)
    print_reconciliation_report(reconciliation)

    # Save reconciliation results
    reconciliation['summary'].to_csv(
        os.path.join(output_folder, 'topology_reconciliation_summary.csv'),
        index=False
    )
    reconciliation['actual_changes_by_transition'].to_csv(
        os.path.join(output_folder, 'topology_changes_by_transition.csv'),
        index=False
    )

    # Step 4: Topology-driven inference
    print("\n" + "="*80)
    print("STEP 4: TOPOLOGY-DRIVEN EVENT INFERENCE")
    print("="*80)

    # Try both methods
    print("\nMethod 1: Minimize Discrepancy (adjust detected events to match topology)")
    inferred_df_discrepancy = infer_events_for_timeseries(
        combined_df,
        detected_events={'event_counts': detected_events['summary_statistics']},
        method='minimize_discrepancy'
    )
    comparison_df_discrepancy = compare_detected_vs_inferred(detected_events, inferred_df_discrepancy)
    print_inference_report(inferred_df_discrepancy, comparison_df_discrepancy)

    print("\n" + "-"*80)
    print("\nMethod 2: Minimize Total Events (find sparsest solution)")
    inferred_df_total = infer_events_for_timeseries(
        combined_df,
        detected_events=None,
        method='minimize_total'
    )
    comparison_df_total = compare_detected_vs_inferred(detected_events, inferred_df_total)
    print_inference_report(inferred_df_total, comparison_df_total)

    # Save topology-driven inference results
    inferred_df_discrepancy.to_csv(
        os.path.join(output_folder, 'topology_inferred_events_minimize_discrepancy.csv'),
        index=False
    )
    comparison_df_discrepancy.to_csv(
        os.path.join(output_folder, 'comparison_minimize_discrepancy.csv'),
        index=False
    )
    inferred_df_total.to_csv(
        os.path.join(output_folder, 'topology_inferred_events_minimize_total.csv'),
        index=False
    )
    comparison_df_total.to_csv(
        os.path.join(output_folder, 'comparison_minimize_total.csv'),
        index=False
    )

    # Step 5: Summary
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_folder}/")
    print("\nGenerated files:")
    print("  1. detected_events_summary.csv - Traditional event detection results")
    print("  2. topology_reconciliation_summary.csv - Reconciliation summary")
    print("  3. topology_changes_by_transition.csv - Actual topology changes")
    print("  4. topology_inferred_events_minimize_discrepancy.csv - Inferred events (method 1)")
    print("  5. comparison_minimize_discrepancy.csv - Comparison (method 1)")
    print("  6. topology_inferred_events_minimize_total.csv - Inferred events (method 2)")
    print("  7. comparison_minimize_total.csv - Comparison (method 2)")

    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)

    # Analyze discrepancies
    summary = reconciliation['summary']
    tips_row = summary[summary['metric'] == 'Tips'].iloc[0]
    junctions_row = summary[summary['metric'] == 'Junctions'].iloc[0]

    print("\n1. Topology Reconciliation:")
    print(f"   - Tips: {tips_row['percent_explained']:.1f}% explained by detected events")
    print(f"   - Junctions: {junctions_row['percent_explained']:.1f}% explained by detected events")

    if abs(tips_row['discrepancy']) > 0 or abs(junctions_row['discrepancy']) > 0:
        print("\n   ⚠ Discrepancies detected! This suggests:")
        print("     - Mis-segmentations in image processing")
        print("     - Missing event classifications")
        print("     - Spurious event detections")

    print("\n2. Topology-Driven Inference:")
    print("   - Method 1 (minimize discrepancy): Adjusts detected events to match topology")
    print("   - Method 2 (minimize total): Finds minimal set of events explaining topology")

    total_diff = comparison_df_discrepancy['difference'].abs().sum()
    print(f"\n   - Total event count difference (method 1): {total_diff}")

    print("\n3. Recommendations:")
    if tips_row['percent_explained'] < 90 or junctions_row['percent_explained'] < 90:
        print("   ⚠ Low explanation rate (<90%). Consider:")
        print("     - Reviewing segmentation quality")
        print("     - Adding new event classifications")
        print("     - Adjusting distance_threshold parameter")
    else:
        print("   ✓ Good explanation rate (>90%). Events well-calibrated to topology!")

    print("\n" + "="*80)

    return {
        'combined_df': combined_df,
        'detected_events': detected_events,
        'reconciliation': reconciliation,
        'inferred_discrepancy': inferred_df_discrepancy,
        'inferred_total': inferred_df_total,
        'comparison_discrepancy': comparison_df_discrepancy,
        'comparison_total': comparison_df_total
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_topology_analysis.py <base_folder_path> [distance_threshold] [output_folder]")
        print("\nExample:")
        print("  python run_topology_analysis.py /path/to/time_series/")
        print("  python run_topology_analysis.py /path/to/time_series/ 5.0 /path/to/output/")
        sys.exit(1)

    base_folder = sys.argv[1]
    distance_threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    output_folder = sys.argv[3] if len(sys.argv) > 3 else None

    results = run_comprehensive_analysis(base_folder, distance_threshold, output_folder)
