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


def detect_tip_junction_events(df_t1, df_t2, distance_threshold=5.0):
    """
    Detect tip-junction conversion events between two timepoints.

    Args:
        df_t1: DataFrame for earlier timepoint
        df_t2: DataFrame for later timepoint
        distance_threshold: Spatial matching threshold

    Returns:
        Dictionary with tip→junction and junction→tip events
    """
    # Calculate actual degrees from adjacency lists
    df_t1 = df_t1.copy()
    df_t2 = df_t2.copy()

    df_t1['actual_degree'] = df_t1['adjacencies'].apply(calculate_degree_from_adjacencies)
    df_t2['actual_degree'] = df_t2['adjacencies'].apply(calculate_degree_from_adjacencies)

    # Match nodes spatially
    matches = match_nodes_spatially(df_t1, df_t2, distance_threshold)

    events = {
        'tip_to_junction': [],
        'junction_to_tip': [],
        'junction_breakage': []
    }

    for t1_idx, t2_idx in matches.items():
        degree_t1 = df_t1.iloc[t1_idx]['actual_degree']
        degree_t2 = df_t2.iloc[t2_idx]['actual_degree']

        pos_t1 = [df_t1.iloc[t1_idx]['pos_x'], df_t1.iloc[t1_idx]['pos_y'], df_t1.iloc[t1_idx]['pos_z']]
        pos_t2 = [df_t2.iloc[t2_idx]['pos_x'], df_t2.iloc[t2_idx]['pos_y'], df_t2.iloc[t2_idx]['pos_z']]

        # Tip to junction (fusion event)
        if degree_t1 == 1 and degree_t2 >= 3:
            events['tip_to_junction'].append({
                'position_t1': pos_t1,
                'position_t2': pos_t2,
                'degree_change': degree_t2 - degree_t1,
                'timepoint_1': df_t1.iloc[t1_idx].get('time_point', 'unknown'),
                'timepoint_2': df_t2.iloc[t2_idx].get('time_point', 'unknown')
            })

        # Junction to tip (potential breakage)
        elif degree_t1 >= 3 and degree_t2 == 1:
            events['junction_to_tip'].append({
                'position_t1': pos_t1,
                'position_t2': pos_t2,
                'degree_change': degree_t2 - degree_t1,
                'timepoint_1': df_t1.iloc[t1_idx].get('time_point', 'unknown'),
                'timepoint_2': df_t2.iloc[t2_idx].get('time_point', 'unknown')
            })

        # Junction breakage (degree reduction but still junction)
        elif degree_t1 >= 3 and degree_t2 >= 3 and degree_t2 < degree_t1:
            events['junction_breakage'].append({
                'position_t1': pos_t1,
                'position_t2': pos_t2,
                'degree_change': degree_t2 - degree_t1,
                'degree_t1': degree_t1,
                'degree_t2': degree_t2,
                'timepoint_1': df_t1.iloc[t1_idx].get('time_point', 'unknown'),
                'timepoint_2': df_t2.iloc[t2_idx].get('time_point', 'unknown')
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
    Analyze all events across the entire time series.

    Args:
        combined_df: Combined DataFrame from timeseries_reader
        distance_threshold: Spatial matching threshold

    Returns:
        Dictionary with all detected events
    """
    time_points = sorted(combined_df['time_point'].unique())

    all_events = {
        'tip_to_junction_events': [],
        'junction_to_tip_events': [],
        'junction_breakage_events': [],
        'node_appearance_events': [],
        'node_disappearance_events': [],
        'component_changes': []
    }

    summary_stats = {
        'total_tip_to_junction': 0,
        'total_junction_to_tip': 0,
        'total_junction_breakage': 0,
        'total_appeared_nodes': 0,
        'total_disappeared_nodes': 0,
        'total_component_fusions': 0,
        'total_component_fissions': 0
    }

    print(f"Analyzing events across {len(time_points)} time points...")

    for i in range(len(time_points) - 1):
        t1, t2 = time_points[i], time_points[i + 1]

        df_t1 = combined_df[combined_df['time_point'] == t1]
        df_t2 = combined_df[combined_df['time_point'] == t2]

        print(f"Comparing timepoints {t1} → {t2}")

        # Detect tip-junction events
        tj_events = detect_tip_junction_events(df_t1, df_t2, distance_threshold)
        all_events['tip_to_junction_events'].extend(tj_events['tip_to_junction'])
        all_events['junction_to_tip_events'].extend(tj_events['junction_to_tip'])
        all_events['junction_breakage_events'].extend(tj_events['junction_breakage'])

        # Detect appearance/disappearance
        ad_events = detect_node_appearance_disappearance(df_t1, df_t2, distance_threshold)
        all_events['node_appearance_events'].extend(ad_events['appeared_nodes'])
        all_events['node_disappearance_events'].extend(ad_events['disappeared_nodes'])

        # Detect component changes
        comp_events = detect_component_changes(df_t1, df_t2, distance_threshold)
        all_events['component_changes'].append({
            'timepoint_transition': f"{t1}→{t2}",
            **comp_events
        })

        # Update summary stats
        summary_stats['total_tip_to_junction'] += len(tj_events['tip_to_junction'])
        summary_stats['total_junction_to_tip'] += len(tj_events['junction_to_tip'])
        summary_stats['total_junction_breakage'] += len(tj_events['junction_breakage'])
        summary_stats['total_appeared_nodes'] += len(ad_events['appeared_nodes'])
        summary_stats['total_disappeared_nodes'] += len(ad_events['disappeared_nodes'])
        summary_stats['total_component_fusions'] += comp_events['component_fusion']
        summary_stats['total_component_fissions'] += comp_events['component_fission']

    all_events['summary_statistics'] = summary_stats

    return all_events


if __name__ == "__main__":
    import sys
    from .timeseries_reader import read_timeseries_csvs

    if len(sys.argv) > 1:
        base_folder = sys.argv[1]

        print("Loading time series data...")
        df = read_timeseries_csvs(base_folder)

        print("Analyzing events...")
        events = analyze_timeseries_events(df)

        print("\n=== EVENT DETECTION SUMMARY ===")
        stats = events['summary_statistics']
        for event_type, count in stats.items():
            print(f"{event_type}: {count}")

    else:
        print("Usage: python event_detector.py <base_folder_path>")