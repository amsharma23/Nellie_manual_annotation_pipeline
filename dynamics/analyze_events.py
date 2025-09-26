#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 2025

@author: amansharma

Analyze fission/fusion events from combined timeseries adjacency CSV.
"""

import pandas as pd
import os
from .event_detector import analyze_timeseries_events


def analyze_events_from_csv(csv_path, distance_threshold=5.0, output_folder=None):
    """
    Analyze events from a combined timeseries adjacency CSV file.

    Args:
        csv_path: Path to the combined_timeseries_adjacency.csv file
        distance_threshold: Spatial matching threshold for nodes
        output_folder: Optional folder to save results

    Returns:
        Dictionary with all detected events and summary statistics
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    print(f"Loading combined timeseries data from: {csv_path}")
    df = pd.read_csv(csv_path)

    print(f"Loaded {len(df)} rows across {df['time_point'].nunique()} time points")
    print(f"Time points: {sorted(df['time_point'].unique())}")

    # Analyze events
    print("\nAnalyzing network dynamics events using 6-category classification...")
    events = analyze_timeseries_events(df, distance_threshold)

    # Print detailed results
    print("\n" + "="*50)
    print("NETWORK DYNAMICS EVENT ANALYSIS RESULTS")
    print("6-Category Classification (Degree 1 & 3 Nodes Only)")
    print("="*50)

    stats = events['summary_statistics']
    print(f"\nSUMMARY STATISTICS:")
    print(f"  1. Tip-edge fusion: {stats['total_tip_edge_fusion']}")
    print(f"  2. Junction breakage: {stats['total_junction_breakage']}")
    print(f"  3. Tip-tip fusion: {stats['total_tip_tip_fusion']}")
    print(f"  4. Tip-tip fission: {stats['total_tip_tip_fission']}")
    print(f"  5. Extrusion: {stats['total_extrusion']}")
    print(f"  6. Retraction: {stats['total_retraction']}")

    total_events = sum(stats.values())
    print(f"\nTotal events detected: {total_events}")

    # Show some example events
    if events['tip_edge_fusion_events']:
        print(f"\nExample TIP-EDGE FUSION events:")
        for i, event in enumerate(events['tip_edge_fusion_events'][:3]):  # Show first 3
            print(f"  Event {i+1}: {event['timepoint_1']} → {event['timepoint_2']}")
            print(f"    Position: {event['position_t1']} → {event['position_t2']}")
            print(f"    Degree change: {event['degree_t1']} → {event['degree_t2']}")

    if events['junction_breakage_events']:
        print(f"\nExample JUNCTION BREAKAGE events:")
        for i, event in enumerate(events['junction_breakage_events'][:3]):  # Show first 3
            print(f"  Event {i+1}: {event['timepoint_1']} → {event['timepoint_2']}")
            print(f"    Position: {event['position_t1']} → {event['position_t2']}")
            print(f"    Degree change: {event['degree_t1']} → {event['degree_t2']}")

    if events['tip_tip_fusion_events']:
        print(f"\nExample TIP-TIP FUSION events:")
        for i, event in enumerate(events['tip_tip_fusion_events'][:3]):  # Show first 3
            print(f"  Event {i+1}: At timepoint {event['timepoint']}")
            print(f"    Tip positions: {event['tip1_position']} & {event['tip2_position']}")
            print(f"    Distance: {event['distance']:.2f}")

    if events['tip_tip_fission_events']:
        print(f"\nExample TIP-TIP FISSION events:")
        for i, event in enumerate(events['tip_tip_fission_events'][:3]):  # Show first 3
            print(f"  Event {i+1}: At timepoint {event['timepoint']}")
            print(f"    Tip positions: {event['tip1_position']} & {event['tip2_position']}")
            print(f"    Distance: {event['distance']:.2f}")

    if events['extrusion_events']:
        print(f"\nExample EXTRUSION events:")
        for i, event in enumerate(events['extrusion_events'][:3]):  # Show first 3
            print(f"  Event {i+1}: At timepoint {event['timepoint']}")
            print(f"    Tip: {event['tip_position']}, Junction: {event['junction_position']}")
            print(f"    Distance: {event['distance']:.2f}")

    if events['retraction_events']:
        print(f"\nExample RETRACTION events:")
        for i, event in enumerate(events['retraction_events'][:3]):  # Show first 3
            print(f"  Event {i+1}: At timepoint {event['timepoint']}")
            print(f"    Tip: {event['tip_position']}, Junction: {event['junction_position']}")
            print(f"    Distance: {event['distance']:.2f}")

    # Save results if output folder specified
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)

        # Save summary statistics
        summary_df = pd.DataFrame([stats])
        summary_df.to_csv(os.path.join(output_folder, 'event_summary.csv'), index=False)

        # Save detailed events for each category
        if events['tip_edge_fusion_events']:
            tef_df = pd.DataFrame(events['tip_edge_fusion_events'])
            tef_df.to_csv(os.path.join(output_folder, 'tip_edge_fusion_events.csv'), index=False)

        if events['junction_breakage_events']:
            jb_df = pd.DataFrame(events['junction_breakage_events'])
            jb_df.to_csv(os.path.join(output_folder, 'junction_breakage_events.csv'), index=False)

        if events['tip_tip_fusion_events']:
            ttf_df = pd.DataFrame(events['tip_tip_fusion_events'])
            ttf_df.to_csv(os.path.join(output_folder, 'tip_tip_fusion_events.csv'), index=False)

        if events['tip_tip_fission_events']:
            ttfi_df = pd.DataFrame(events['tip_tip_fission_events'])
            ttfi_df.to_csv(os.path.join(output_folder, 'tip_tip_fission_events.csv'), index=False)

        if events['extrusion_events']:
            ext_df = pd.DataFrame(events['extrusion_events'])
            ext_df.to_csv(os.path.join(output_folder, 'extrusion_events.csv'), index=False)

        if events['retraction_events']:
            ret_df = pd.DataFrame(events['retraction_events'])
            ret_df.to_csv(os.path.join(output_folder, 'retraction_events.csv'), index=False)

        print(f"\nResults saved to: {output_folder}")

    return events


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_events.py <path_to_combined_timeseries_adjacency.csv> [output_folder] [distance_threshold]")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    distance_threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

    try:
        events = analyze_events_from_csv(csv_path, distance_threshold, output_folder)
    except Exception as e:
        print(f"Error: {e}")