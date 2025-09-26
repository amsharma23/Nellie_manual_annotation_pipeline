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
    print("\nAnalyzing fission/fusion events...")
    events = analyze_timeseries_events(df, distance_threshold)

    # Print detailed results
    print("\n" + "="*50)
    print("FISSION/FUSION EVENT ANALYSIS RESULTS")
    print("="*50)

    stats = events['summary_statistics']
    print(f"\nSUMMARY STATISTICS:")
    print(f"  Tip-to-Junction events (fusion): {stats['total_tip_to_junction']}")
    print(f"  Junction-to-Tip events (fission): {stats['total_junction_to_tip']}")
    print(f"  Junction breakage events: {stats['total_junction_breakage']}")
    print(f"  Node appearances (extrusion): {stats['total_appeared_nodes']}")
    print(f"  Node disappearances (retraction): {stats['total_disappeared_nodes']}")
    print(f"  Component fusions: {stats['total_component_fusions']}")
    print(f"  Component fissions: {stats['total_component_fissions']}")

    # Show some example events
    if events['tip_to_junction_events']:
        print(f"\nExample TIP-TO-JUNCTION events:")
        for i, event in enumerate(events['tip_to_junction_events'][:3]):  # Show first 3
            print(f"  Event {i+1}: {event['timepoint_1']} → {event['timepoint_2']}")
            print(f"    Position: {event['position_t1']} → {event['position_t2']}")
            print(f"    Degree change: +{event['degree_change']}")

    if events['junction_to_tip_events']:
        print(f"\nExample JUNCTION-TO-TIP events:")
        for i, event in enumerate(events['junction_to_tip_events'][:3]):  # Show first 3
            print(f"  Event {i+1}: {event['timepoint_1']} → {event['timepoint_2']}")
            print(f"    Position: {event['position_t1']} → {event['position_t2']}")
            print(f"    Degree change: {event['degree_change']}")

    if events['node_appearance_events']:
        print(f"\nExample NODE APPEARANCE events:")
        for i, event in enumerate(events['node_appearance_events'][:3]):  # Show first 3
            print(f"  Event {i+1}: New node at timepoint {event['timepoint']}")
            print(f"    Position: {event['position']}, Degree: {event['degree']}")

    # Save results if output folder specified
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)

        # Save summary statistics
        summary_df = pd.DataFrame([stats])
        summary_df.to_csv(os.path.join(output_folder, 'event_summary.csv'), index=False)

        # Save detailed events
        if events['tip_to_junction_events']:
            tj_df = pd.DataFrame(events['tip_to_junction_events'])
            tj_df.to_csv(os.path.join(output_folder, 'tip_to_junction_events.csv'), index=False)

        if events['junction_to_tip_events']:
            jt_df = pd.DataFrame(events['junction_to_tip_events'])
            jt_df.to_csv(os.path.join(output_folder, 'junction_to_tip_events.csv'), index=False)

        if events['junction_breakage_events']:
            jb_df = pd.DataFrame(events['junction_breakage_events'])
            jb_df.to_csv(os.path.join(output_folder, 'junction_breakage_events.csv'), index=False)

        if events['node_appearance_events']:
            na_df = pd.DataFrame(events['node_appearance_events'])
            na_df.to_csv(os.path.join(output_folder, 'node_appearance_events.csv'), index=False)

        if events['node_disappearance_events']:
            nd_df = pd.DataFrame(events['node_disappearance_events'])
            nd_df.to_csv(os.path.join(output_folder, 'node_disappearance_events.csv'), index=False)

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