#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 2025

@author: amansharma

Event detection for fission/fusion dynamics in time series network data.
"""

import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
from typing import List, Dict, Tuple, Optional
import ast


def parse_adjacencies(adj_str):
    """Parse adjacency list string to get list of neighbor IDs."""
    try:
        if isinstance(adj_str, str):
            # Handle string representation of list
            return ast.literal_eval(adj_str)
        elif isinstance(adj_str, list):
            return adj_str
        else:
            return []
    except:
        return []


def calculate_degree_from_adjacencies(adj_str):
    """Calculate node degree from adjacency list."""
    adj_list = parse_adjacencies(adj_str)
    return len(adj_list)


def match_nodes_spatially(df_t1, df_t2, distance_threshold=5.0):
    """
    Match nodes between two timepoints based on spatial proximity.

    Args:
        df_t1: DataFrame for timepoint 1
        df_t2: DataFrame for timepoint 2
        distance_threshold: Maximum distance to consider nodes as the same

    Returns:
        Dictionary mapping indices in df_t1 to indices in df_t2
    """
    if df_t1.empty or df_t2.empty:
        return {}

    # Extract positions
    pos1 = df_t1[['pos_x', 'pos_y', 'pos_z']].values
    pos2 = df_t2[['pos_x', 'pos_y', 'pos_z']].values

    # Calculate distance matrix
    distances = cdist(pos1, pos2)

    # Find best matches
    matches = {}
    used_t2_indices = set()

    for i in range(len(pos1)):
        # Find closest node in t2 that hasn't been matched yet
        valid_distances = distances[i].copy()
        valid_distances[list(used_t2_indices)] = np.inf

        min_dist_idx = np.argmin(valid_distances)
        min_dist = valid_distances[min_dist_idx]

        if min_dist <= distance_threshold:
            matches[i] = min_dist_idx
            used_t2_indices.add(min_dist_idx)

    return matches


def classify_network_events(df_t1, df_t2, distance_threshold=5.0):
    """
    Classify network events into 6 specific categories based on degree 1 and 3 nodes.

    Event categories:
    1. tip-edge fusion: degree 1 node fuses to an edge to make a degree 3 node
    2. junction-breakage: degree 3 node breaks to give an edge and degree 1 node
    3. tip-tip fusion: two degree 1 nodes come together to make an edge
    4. tip-tip fission: edge splits to form two degree 1 nodes
    5. extrusion: tip juts out of an edge leading to additional junction and tip
    6. retraction: opposite of extrusion

    Args:
        df_t1: DataFrame for earlier timepoint
        df_t2: DataFrame for later timepoint
        distance_threshold: Spatial matching threshold

    Returns:
        Dictionary with classified events
    """
    # Calculate actual degrees from adjacency lists
    df_t1 = df_t1.copy()
    df_t2 = df_t2.copy()

    df_t1['actual_degree'] = df_t1['adjacencies'].apply(calculate_degree_from_adjacencies)
    df_t2['actual_degree'] = df_t2['adjacencies'].apply(calculate_degree_from_adjacencies)

    # Filter to only degree 1 and 3 nodes (assumption from user)
    df_t1 = df_t1[df_t1['actual_degree'].isin([1, 3])]
    df_t2 = df_t2[df_t2['actual_degree'].isin([1, 3])]

    # Match nodes spatially
    matches = match_nodes_spatially(df_t1, df_t2, distance_threshold)

    events = {
        'tip_edge_fusion': [],
        'junction_breakage': [],
        'tip_tip_fusion': [],
        'tip_tip_fission': [],
        'extrusion': [],
        'retraction': []
    }

    # Track matched nodes to identify appearance/disappearance
    matched_t1_indices = set(matches.keys())
    matched_t2_indices = set(matches.values())

    # Analyze matched nodes for degree changes
    for t1_idx, t2_idx in matches.items():
        degree_t1 = df_t1.iloc[t1_idx]['actual_degree']
        degree_t2 = df_t2.iloc[t2_idx]['actual_degree']

        pos_t1 = [df_t1.iloc[t1_idx]['pos_x'], df_t1.iloc[t1_idx]['pos_y'], df_t1.iloc[t1_idx]['pos_z']]
        pos_t2 = [df_t2.iloc[t2_idx]['pos_x'], df_t2.iloc[t2_idx]['pos_y'], df_t2.iloc[t2_idx]['pos_z']]

        event_data = {
            'position_t1': pos_t1,
            'position_t2': pos_t2,
            'degree_t1': degree_t1,
            'degree_t2': degree_t2,
            'timepoint_1': df_t1.iloc[t1_idx].get('time_point', 'unknown'),
            'timepoint_2': df_t2.iloc[t2_idx].get('time_point', 'unknown')
        }

        # 1. Tip-edge fusion: degree 1 → degree 3 (tip fuses to edge)
        if degree_t1 == 1 and degree_t2 == 3:
            events['tip_edge_fusion'].append(event_data)

        # 2. Junction breakage: degree 3 → degree 1 (junction breaks)
        elif degree_t1 == 3 and degree_t2 == 1:
            events['junction_breakage'].append(event_data)

    # Analyze unmatched nodes for tip-tip events and extrusion/retraction
    disappeared_t1 = set(range(len(df_t1))) - matched_t1_indices
    appeared_t2 = set(range(len(df_t2))) - matched_t2_indices

    # Count degree 1 nodes that disappeared/appeared
    disappeared_tips = [idx for idx in disappeared_t1 if df_t1.iloc[idx]['actual_degree'] == 1]
    appeared_tips = [idx for idx in appeared_t2 if df_t2.iloc[idx]['actual_degree'] == 1]
    disappeared_junctions = [idx for idx in disappeared_t1 if df_t1.iloc[idx]['actual_degree'] == 3]
    appeared_junctions = [idx for idx in appeared_t2 if df_t2.iloc[idx]['actual_degree'] == 3]

    # 3. Tip-tip fusion: two tips disappear (merge into edge between junctions)
    # Heuristic: pairs of nearby disappeared tips
    for i, idx1 in enumerate(disappeared_tips):
        for idx2 in disappeared_tips[i+1:]:
            pos1 = [df_t1.iloc[idx1]['pos_x'], df_t1.iloc[idx1]['pos_y'], df_t1.iloc[idx1]['pos_z']]
            pos2 = [df_t1.iloc[idx2]['pos_x'], df_t1.iloc[idx2]['pos_y'], df_t1.iloc[idx2]['pos_z']]

            distance = np.linalg.norm(np.array(pos1) - np.array(pos2))
            if distance <= distance_threshold * 2:  # Allow larger threshold for fusion
                events['tip_tip_fusion'].append({
                    'tip1_position': pos1,
                    'tip2_position': pos2,
                    'distance': distance,
                    'timepoint': df_t1.iloc[idx1].get('time_point', 'unknown')
                })

    # 4. Tip-tip fission: two tips appear (edge splits)
    # Heuristic: pairs of nearby appeared tips
    for i, idx1 in enumerate(appeared_tips):
        for idx2 in appeared_tips[i+1:]:
            pos1 = [df_t2.iloc[idx1]['pos_x'], df_t2.iloc[idx1]['pos_y'], df_t2.iloc[idx1]['pos_z']]
            pos2 = [df_t2.iloc[idx2]['pos_x'], df_t2.iloc[idx2]['pos_y'], df_t2.iloc[idx2]['pos_z']]

            distance = np.linalg.norm(np.array(pos1) - np.array(pos2))
            if distance <= distance_threshold * 2:  # Allow larger threshold for fission
                events['tip_tip_fission'].append({
                    'tip1_position': pos1,
                    'tip2_position': pos2,
                    'distance': distance,
                    'timepoint': df_t2.iloc[idx1].get('time_point', 'unknown')
                })

    # 5. Extrusion: new tip and junction appear (tip juts out of edge)
    # Heuristic: nearby appeared tip and junction pairs
    for tip_idx in appeared_tips:
        for junction_idx in appeared_junctions:
            tip_pos = [df_t2.iloc[tip_idx]['pos_x'], df_t2.iloc[tip_idx]['pos_y'], df_t2.iloc[tip_idx]['pos_z']]
            junction_pos = [df_t2.iloc[junction_idx]['pos_x'], df_t2.iloc[junction_idx]['pos_y'], df_t2.iloc[junction_idx]['pos_z']]

            distance = np.linalg.norm(np.array(tip_pos) - np.array(junction_pos))
            if distance <= distance_threshold:
                events['extrusion'].append({
                    'tip_position': tip_pos,
                    'junction_position': junction_pos,
                    'distance': distance,
                    'timepoint': df_t2.iloc[tip_idx].get('time_point', 'unknown')
                })

    # 6. Retraction: tip and junction disappear (opposite of extrusion)
    # Heuristic: nearby disappeared tip and junction pairs
    for tip_idx in disappeared_tips:
        for junction_idx in disappeared_junctions:
            tip_pos = [df_t1.iloc[tip_idx]['pos_x'], df_t1.iloc[tip_idx]['pos_y'], df_t1.iloc[tip_idx]['pos_z']]
            junction_pos = [df_t1.iloc[junction_idx]['pos_x'], df_t1.iloc[junction_idx]['pos_y'], df_t1.iloc[junction_idx]['pos_z']]

            distance = np.linalg.norm(np.array(tip_pos) - np.array(junction_pos))
            if distance <= distance_threshold:
                events['retraction'].append({
                    'tip_position': tip_pos,
                    'junction_position': junction_pos,
                    'distance': distance,
                    'timepoint': df_t1.iloc[tip_idx].get('time_point', 'unknown')
                })

    return events


def detect_node_appearance_disappearance(df_t1, df_t2, distance_threshold=5.0):
    """
    Detect nodes that appear or disappear between timepoints.

    Args:
        df_t1: DataFrame for earlier timepoint
        df_t2: DataFrame for later timepoint
        distance_threshold: Spatial matching threshold

    Returns:
        Dictionary with appearing and disappearing nodes
    """
    matches = match_nodes_spatially(df_t1, df_t2, distance_threshold)

    # Find unmatched nodes
    matched_t1_indices = set(matches.keys())
    matched_t2_indices = set(matches.values())

    disappeared_indices = set(range(len(df_t1))) - matched_t1_indices
    appeared_indices = set(range(len(df_t2))) - matched_t2_indices

    events = {
        'appeared_nodes': [],
        'disappeared_nodes': []
    }

    # Disappeared nodes
    for idx in disappeared_indices:
        node = df_t1.iloc[idx]
        events['disappeared_nodes'].append({
            'position': [node['pos_x'], node['pos_y'], node['pos_z']],
            'degree': calculate_degree_from_adjacencies(node['adjacencies']),
            'timepoint': node.get('time_point', 'unknown')
        })

    # Appeared nodes
    for idx in appeared_indices:
        node = df_t2.iloc[idx]
        events['appeared_nodes'].append({
            'position': [node['pos_x'], node['pos_y'], node['pos_z']],
            'degree': calculate_degree_from_adjacencies(node['adjacencies']),
            'timepoint': node.get('time_point', 'unknown')
        })

    return events


def detect_component_changes(df_t1, df_t2, distance_threshold=5.0):
    """
    Detect changes in connected components between timepoints.

    Args:
        df_t1: DataFrame for earlier timepoint
        df_t2: DataFrame for later timepoint
        distance_threshold: Spatial matching threshold

    Returns:
        Dictionary with component fusion/fission events
    """
    events = {
        'component_fusion': 0,
        'component_fission': 0,
        'net_component_change': 0
    }

    # Count components at each timepoint
    if 'component_num' in df_t1.columns and 'component_num' in df_t2.columns:
        num_components_t1 = df_t1['component_num'].nunique()
        num_components_t2 = df_t2['component_num'].nunique()

        net_change = num_components_t2 - num_components_t1
        events['net_component_change'] = net_change

        # Infer fusion/fission from net change
        if net_change < 0:
            events['component_fusion'] = abs(net_change)
        elif net_change > 0:
            events['component_fission'] = net_change

    return events


def analyze_timeseries_events(combined_df, distance_threshold=5.0):
    """
    Analyze all events across the entire time series using the 6-category classification.

    Args:
        combined_df: Combined DataFrame from timeseries_reader
        distance_threshold: Spatial matching threshold

    Returns:
        Dictionary with all detected events classified into 6 categories
    """
    time_points = sorted(combined_df['time_point'].unique())

    all_events = {
        'tip_edge_fusion_events': [],
        'junction_breakage_events': [],
        'tip_tip_fusion_events': [],
        'tip_tip_fission_events': [],
        'extrusion_events': [],
        'retraction_events': []
    }

    summary_stats = {
        'total_tip_edge_fusion': 0,
        'total_junction_breakage': 0,
        'total_tip_tip_fusion': 0,
        'total_tip_tip_fission': 0,
        'total_extrusion': 0,
        'total_retraction': 0
    }

    print(f"Analyzing events across {len(time_points)} time points...")
    print("Event categories:")
    print("1. Tip-edge fusion: degree 1 node fuses to edge → degree 3 node")
    print("2. Junction breakage: degree 3 node breaks → degree 1 node + edge")
    print("3. Tip-tip fusion: two degree 1 nodes merge → edge")
    print("4. Tip-tip fission: edge splits → two degree 1 nodes")
    print("5. Extrusion: tip juts out from edge → new tip + junction")
    print("6. Retraction: tip retracts into edge → tip + junction disappear")
    print()

    for i in range(len(time_points) - 1):
        t1, t2 = time_points[i], time_points[i + 1]

        df_t1 = combined_df[combined_df['time_point'] == t1]
        df_t2 = combined_df[combined_df['time_point'] == t2]

        print(f"Comparing timepoints {t1} → {t2}")

        # Classify events using new system
        events = classify_network_events(df_t1, df_t2, distance_threshold)

        # Extend event lists
        all_events['tip_edge_fusion_events'].extend(events['tip_edge_fusion'])
        all_events['junction_breakage_events'].extend(events['junction_breakage'])
        all_events['tip_tip_fusion_events'].extend(events['tip_tip_fusion'])
        all_events['tip_tip_fission_events'].extend(events['tip_tip_fission'])
        all_events['extrusion_events'].extend(events['extrusion'])
        all_events['retraction_events'].extend(events['retraction'])

        # Update summary stats
        summary_stats['total_tip_edge_fusion'] += len(events['tip_edge_fusion'])
        summary_stats['total_junction_breakage'] += len(events['junction_breakage'])
        summary_stats['total_tip_tip_fusion'] += len(events['tip_tip_fusion'])
        summary_stats['total_tip_tip_fission'] += len(events['tip_tip_fission'])
        summary_stats['total_extrusion'] += len(events['extrusion'])
        summary_stats['total_retraction'] += len(events['retraction'])

        # Print immediate results for this timepoint transition
        print(f"  Tip-edge fusion: {len(events['tip_edge_fusion'])}")
        print(f"  Junction breakage: {len(events['junction_breakage'])}")
        print(f"  Tip-tip fusion: {len(events['tip_tip_fusion'])}")
        print(f"  Tip-tip fission: {len(events['tip_tip_fission'])}")
        print(f"  Extrusion: {len(events['extrusion'])}")
        print(f"  Retraction: {len(events['retraction'])}")

    all_events['summary_statistics'] = summary_stats

    return all_events


if __name__ == "__main__":
    import sys
    from .timeseries_reader import read_timeseries_csvs

    if len(sys.argv) > 1:
        base_folder = sys.argv[1]

        print("Loading time series data...")
        df = read_timeseries_csvs(base_folder)

        print("Analyzing events using 6-category classification...")
        events = analyze_timeseries_events(df)

        print("\n=== EVENT DETECTION SUMMARY ===")
        print("Based on degree 1 (tips) and degree 3 (junctions) nodes only")
        print()
        stats = events['summary_statistics']
        for event_type, count in stats.items():
            print(f"{event_type}: {count}")

        # Show total events
        total_events = sum(stats.values())
        print(f"\nTotal events detected: {total_events}")

    else:
        print("Usage: python event_detector.py <base_folder_path>")