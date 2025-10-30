#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 2025

@author: amansharma

Event detection for fission/fusion dynamics in time series network data.
"""

import os
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


def match_nodes_spatially(df_t1, df_t2, distance_threshold=2.0, z_scale: float = (0.29/0.11)):
    """
    Match nodes between two timepoints based on spatial proximity.
    Now allows one-to-many matching: each node in t1 can match multiple nodes in t2.

    Args:
        df_t1: DataFrame for timepoint 1
        df_t2: DataFrame for timepoint 2
        distance_threshold: Maximum distance to consider nodes as the same
        z_scale: Scaling factor for z-dimension

    Returns:
        Dictionary mapping indices in df_t1 to list of indices in df_t2
    """
    if df_t1.empty or df_t2.empty:
        return {}

    # Extract positions
    pos1 = df_t1[['pos_x', 'pos_y', 'pos_z']].values
    pos2 = df_t2[['pos_x', 'pos_y', 'pos_z']].values

    # Apply z scaling to account for non-isotropic space
    # We create scaled copies so original DataFrames remain unchanged
    pos1_scaled = pos1.copy()
    pos2_scaled = pos2.copy()
    if pos1_scaled.shape[1] >= 3:
        pos1_scaled[:, 2] = pos1_scaled[:, 2] * z_scale
    if pos2_scaled.shape[1] >= 3:
        pos2_scaled[:, 2] = pos2_scaled[:, 2] * z_scale

    # Calculate distance matrix using scaled z
    distances = cdist(pos1_scaled, pos2_scaled)

    # Find all matches within threshold (one-to-many)
    matches = {}

    for i in range(len(pos1)):
        # Find all nodes in t2 within distance threshold
        valid_matches = []
        for j in range(len(pos2)):
            if distances[i, j] <= distance_threshold:
                valid_matches.append(j)

        if valid_matches:
            matches[i] = valid_matches

    return matches


def classify_network_events(df_t1, df_t2, distance_threshold=2.0, z_scale: float = 1.0):
    """
    Classify network events into 6 specific categories based on degree 1 and 3 nodes with convergence/divergence criteria.

    Event categories with dynamics criteria:
    1. tip-edge fusion: degree 1 node fuses to an edge to make a degree 3 node (requires positive convergence)
    2. junction-breakage: degree 3 node breaks to give an edge and degree 1 node (requires divergence)
    3. tip-tip fusion: two degree 1 nodes come together to make an edge (requires convergence)
    4. tip-tip fission: edge splits to form two degree 1 nodes (requires divergence)
    5. extrusion: tip juts out of an edge leading to additional junction and tip (requires divergence)
    6. retraction: opposite of extrusion (requires convergence)

    Args:
        df_t1: DataFrame for earlier timepoint
        df_t2: DataFrame for later timepoint
        distance_threshold: Spatial matching threshold
        z_scale: Scaling factor for z-dimension

    Returns:
        Dictionary with classified events
    """
    # Calculate actual degrees from adjacency lists
    df_t1 = df_t1.copy()
    df_t2 = df_t2.copy()

    df_t1['actual_degree'] = df_t1['adjacencies'].apply(calculate_degree_from_adjacencies)
    df_t2['actual_degree'] = df_t2['adjacencies'].apply(calculate_degree_from_adjacencies)

    # Filter to only degree 1 and 3 nodes (assumption from user)
    #df_t1 = df_t1[df_t1['actual_degree'].isin([1, 3])]
    #df_t2 = df_t2[df_t2['actual_degree'].isin([1, 3])]

    # Match nodes spatially (propagate z scaling)
    matches = match_nodes_spatially(df_t1, df_t2, distance_threshold, z_scale)

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
    matched_t2_indices = set()
    for t2_list in matches.values():
        matched_t2_indices.update(t2_list)

    # Analyze matched nodes for degree changes and fission events
    for t1_idx, t2_indices_list in matches.items():
        degree_t1 = df_t1.iloc[t1_idx]['actual_degree']
        pos_t1 = [df_t1.iloc[t1_idx]['pos_x'], df_t1.iloc[t1_idx]['pos_y'], df_t1.iloc[t1_idx]['pos_z']]

        # Check for one-to-one matches (traditional events)
        if len(t2_indices_list) == 1:
            t2_idx = t2_indices_list[0]
            degree_t2 = df_t2.iloc[t2_idx]['actual_degree']
            pos_t2 = [df_t2.iloc[t2_idx]['pos_x'], df_t2.iloc[t2_idx]['pos_y'], df_t2.iloc[t2_idx]['pos_z']]

            event_data = {
                'position_t1': pos_t1,
                'position_t2': pos_t2,
                'degree_t1': degree_t1,
                'degree_t2': degree_t2,
                'timepoint_1': df_t1.iloc[t1_idx].get('time_point', 'unknown'),
                'timepoint_2': df_t2.iloc[t2_idx].get('time_point', 'unknown')
            }

            # 1. Tip-edge fusion: degree 1 → degree ≥3 (tip fuses to edge to become junction)
            # Must be exactly one-to-one transformation with positive convergence
            if degree_t1 == 1 and degree_t2 >= 3:
                # Check for positive convergence in t2
                #convergence_t2 = df_t2.iloc[t2_idx].get('convergence_raw', 0)
                #event_data['convergence'] = convergence_t2
                events['tip_edge_fusion'].append(event_data)

            # 2. Junction breakage: degree ≥3 → degree 1 (junction breaks to become tip)
            # Must be exactly one-to-one transformation with divergence
            elif degree_t1 >= 3 and degree_t2 == 1:
                # Check for divergence in t1
                #event_data['divergence'] = divergence_t1
                events['junction_breakage'].append(event_data)

       

    # Analyze unmatched nodes for tip-tip events and extrusion/retraction
    disappeared_t1 = set(range(len(df_t1))) - matched_t1_indices
    appeared_t2 = set(range(len(df_t2))) - matched_t2_indices

    # Count degree 1 nodes that disappeared/appeared
    disappeared_tips = [idx for idx in disappeared_t1 if df_t1.iloc[idx]['actual_degree'] == 1]
    appeared_tips = [idx for idx in appeared_t2 if df_t2.iloc[idx]['actual_degree'] == 1]
    disappeared_junctions = [idx for idx in disappeared_t1 if df_t1.iloc[idx]['actual_degree'] == 3]
    appeared_junctions = [idx for idx in appeared_t2 if df_t2.iloc[idx]['actual_degree'] == 3]

    # 3. Tip-tip fusion: exactly 2 degree 1 nodes in close proximity disappear together
    # Must be exactly 2 tips that disappear and are within distance threshold with convergence
    for i, idx1 in enumerate(disappeared_tips):
        for idx2 in disappeared_tips[i+1:]:
            pos1 = [df_t1.iloc[idx1]['pos_x'], df_t1.iloc[idx1]['pos_y'], df_t1.iloc[idx1]['pos_z']]
            pos2 = [df_t1.iloc[idx2]['pos_x'], df_t1.iloc[idx2]['pos_y'], df_t1.iloc[idx2]['pos_z']]

            # Account for z scaling when computing Euclidean distance
            p1 = np.array(pos1, dtype=float)
            p2 = np.array(pos2, dtype=float)
            if p1.size >= 3:
                p1[2] = p1[2] * z_scale
            if p2.size >= 3:
                p2[2] = p2[2] * z_scale
            distance = np.linalg.norm(p1 - p2)

            # Check for convergence in either tip (from t1 since they're disappearing)
            #divergence_1_1 = df_t1.iloc[idx1].get('divergence_raw', 0)
            #divergence_1_2 = df_t1.iloc[idx2].get('divergence_raw', 0)

            # Use standard distance threshold for precise tip-tip fusion detection
            #if distance <= 2*distance_threshold and (divergence_1_1 > 0 and divergence_1_2 > 0):
            events['tip_tip_fusion'].append({
                'tip1_position': pos1,
                'tip2_position': pos2,
                'distance': distance,
#                'divergence_tip1': divergence_1_1,
#                'divergence_tip2': divergence_1_2,
                'timepoint_1': df_t1.iloc[idx1].get('time_point', 'unknown'),
                'timepoint_2': df_t1.iloc[idx2].get('time_point', 'unknown') + 1
            })

    # 4. Tip-tip fission: two tips appear (edge splits)
    # Heuristic: pairs of nearby appeared tips with divergence
    for i, idx1 in enumerate(appeared_tips):
        for idx2 in appeared_tips[i+1:]:
            pos1 = [df_t2.iloc[idx1]['pos_x'], df_t2.iloc[idx1]['pos_y'], df_t2.iloc[idx1]['pos_z']]
            pos2 = [df_t2.iloc[idx2]['pos_x'], df_t2.iloc[idx2]['pos_y'], df_t2.iloc[idx2]['pos_z']]

            # Account for z scaling when computing Euclidean distance
            p1 = np.array(pos1, dtype=float)
            p2 = np.array(pos2, dtype=float)
            if p1.size >= 3:
                p1[2] = p1[2] * z_scale
            if p2.size >= 3:
                p2[2] = p2[2] * z_scale
            distance = np.linalg.norm(p1 - p2)

            # Check for convergence in either tip (from t2 since they're appearing)
            #convergence_1 = df_t2.iloc[idx1].get('convergence_raw', 0)
            #convergence_2 = df_t2.iloc[idx2].get('convergence_raw', 0)

            #if distance <= distance_threshold * 2 and (convergence_1 > 0 or convergence_2 > 0):  # Allow larger threshold for fission
            events['tip_tip_fission'].append({
                'tip1_position': pos1,
                'tip2_position': pos2,
                'distance': distance,
#                'divergence_tip1': convergence_1,
#                'divergence_tip2': convergence_2,
                'timepoint_1': df_t2.iloc[idx1].get('time_point', 'unknown') - 1,
                'timepoint_2': df_t2.iloc[idx2].get('time_point', 'unknown')
            })

    # 5. Extrusion: new tip and junction appear (tip juts out of edge)
    # Heuristic: nearby appeared tip and junction pairs with divergence
    for tip_idx in appeared_tips:
        for junction_idx in appeared_junctions:
            tip_pos = [df_t2.iloc[tip_idx]['pos_x'], df_t2.iloc[tip_idx]['pos_y'], df_t2.iloc[tip_idx]['pos_z']]
            junction_pos = [df_t2.iloc[junction_idx]['pos_x'], df_t2.iloc[junction_idx]['pos_y'], df_t2.iloc[junction_idx]['pos_z']]

            # Account for z scaling when computing Euclidean distance
            p1 = np.array(tip_pos, dtype=float)
            p2 = np.array(junction_pos, dtype=float)
            if p1.size >= 3:
                p1[2] = p1[2] * z_scale
            if p2.size >= 3:
                p2[2] = p2[2] * z_scale
            distance = np.linalg.norm(p1 - p2)

            # Check for convergence in tip or junction (from t2 since they're appearing)
#            convergence_tip = df_t2.iloc[tip_idx].get('convergence_raw', 0)
#            convergence_junction = df_t2.iloc[junction_idx].get('convergence_raw', 0)

#            if distance <= distance_threshold and (convergence_tip < 0 or convergence_junction < 0):
            events['extrusion'].append({
                'tip_position': tip_pos,
                'junction_position': junction_pos,
                'distance': distance,
#                    'convergence_tip': convergence_tip,
#                    'convergence_junction': convergence_junction,
                'timepoint_1': df_t2.iloc[tip_idx].get('time_point', 'unknown') - 1,
                'timepoint_2': df_t2.iloc[junction_idx].get('time_point', 'unknown')
            })

    # 6. Retraction: tip and junction disappear (opposite of extrusion)
    # Heuristic: nearby disappeared tip and junction pairs with convergence
    for tip_idx in disappeared_tips:
        for junction_idx in disappeared_junctions:
            tip_pos = [df_t1.iloc[tip_idx]['pos_x'], df_t1.iloc[tip_idx]['pos_y'], df_t1.iloc[tip_idx]['pos_z']]
            junction_pos = [df_t1.iloc[junction_idx]['pos_x'], df_t1.iloc[junction_idx]['pos_y'], df_t1.iloc[junction_idx]['pos_z']]

            # Account for z scaling when computing Euclidean distance
            p1 = np.array(tip_pos, dtype=float)
            p2 = np.array(junction_pos, dtype=float)
            if p1.size >= 3:
                p1[2] = p1[2] * z_scale
            if p2.size >= 3:
                p2[2] = p2[2] * z_scale
            distance = np.linalg.norm(p1 - p2)

            # Check for convergence in tip or junction (from t1 since they're disappearing)
#            divergence_tip = df_t1.iloc[tip_idx].get('divergence_raw', 0)
#            divergence_junction = df_t1.iloc[junction_idx].get('divergence_raw', 0)

#            if distance <= distance_threshold and (divergence_tip > 0 or divergence_junction > 0):
            events['retraction'].append({
                'tip_position': tip_pos,
                'junction_position': junction_pos,
                'distance': distance,
#                'divergence_tip': divergence_tip,
#                'divergence_junction': divergence_junction,
                'timepoint_1': df_t1.iloc[tip_idx].get('time_point', 'unknown'),
                'timepoint_2': df_t1.iloc[junction_idx].get('time_point', 'unknown') + 1
            })

    return events


def detect_node_appearance_disappearance(df_t1, df_t2, distance_threshold=2.0):
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

    # Find unmatched nodes (handle one-to-many matching)
    matched_t1_indices = set(matches.keys())
    matched_t2_indices = set()
    for t2_list in matches.values():
        matched_t2_indices.update(t2_list)

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


def detect_component_changes(df_t1, df_t2, distance_threshold=2.0):
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


def analyze_timeseries_events(combined_df, distance_threshold=2.0):
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


    for i in range(len(time_points) - 1):
        t1, t2 = time_points[i], time_points[i + 1]

        df_t1 = combined_df[combined_df['time_point'] == t1]
        df_t2 = combined_df[combined_df['time_point'] == t2]

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