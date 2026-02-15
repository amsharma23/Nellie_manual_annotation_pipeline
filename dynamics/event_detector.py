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
from app_state import app_state


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


def has_dynamics_data(df):
    """Check if DataFrame has dynamics columns (convergence_raw, divergence_raw)."""
    return 'convergence_raw' in df.columns and 'divergence_raw' in df.columns


def are_nodes_adjacent(df, idx1, idx2):
    """
    Check if two nodes are neighbors based on adjacency lists.

    Args:
        df: DataFrame containing node data
        idx1: Index of first node in DataFrame
        idx2: Index of second node in DataFrame

    Returns:
        True if nodes are adjacent (either lists the other as neighbor)
    """
    node1_id = df.iloc[idx1]['node']
    node2_id = df.iloc[idx2]['node']

    adj1 = parse_adjacencies(df.iloc[idx1]['adjacencies'])
    adj2 = parse_adjacencies(df.iloc[idx2]['adjacencies'])

    # Check if either node lists the other as neighbor
    return node2_id in adj1 or node1_id in adj2


def find_node_at_position(df, pos, distance_threshold, z_scale):
    """
    Find a node in DataFrame that matches the given position within threshold.

    Args:
        df: DataFrame with pos_x, pos_y, pos_z columns
        pos: [x, y, z] position to search for
        distance_threshold: Maximum distance to consider a match
        z_scale: Z-axis scaling factor

    Returns:
        Index of matching node or None if not found
    """
    if df.empty:
        return None

    target = np.array(pos, dtype=float)
    if target.size >= 3:
        target[2] = target[2] * z_scale

    for idx in range(len(df)):
        node_pos = np.array([df.iloc[idx]['pos_x'], df.iloc[idx]['pos_y'], df.iloc[idx]['pos_z']], dtype=float)
        if node_pos.size >= 3:
            node_pos[2] = node_pos[2] * z_scale

        dist = np.linalg.norm(target - node_pos)
        if dist <= distance_threshold:
            return idx

    return None


def check_node_exists_in_frames(combined_df, pos, timepoints, distance_threshold, z_scale):
    """
    Check if a node exists at the given position across multiple timepoints.

    Args:
        combined_df: Full timeseries DataFrame
        pos: [x, y, z] position to check
        timepoints: List of timepoints to check
        distance_threshold: Spatial matching threshold
        z_scale: Z-axis scaling factor

    Returns:
        True if node exists in ALL specified timepoints
    """
    for tp in timepoints:
        df_tp = combined_df[combined_df['time_point'] == tp]
        if df_tp.empty:
            return False

        found = find_node_at_position(df_tp, pos, distance_threshold, z_scale)
        if found is None:
            return False

    return True


def check_node_absent_in_frames(combined_df, pos, timepoints, distance_threshold, z_scale):
    """
    Check if a node is absent at the given position across multiple timepoints.

    Args:
        combined_df: Full timeseries DataFrame
        pos: [x, y, z] position to check
        timepoints: List of timepoints to check
        distance_threshold: Spatial matching threshold
        z_scale: Z-axis scaling factor

    Returns:
        True if node is absent in ALL specified timepoints
    """
    for tp in timepoints:
        df_tp = combined_df[combined_df['time_point'] == tp]
        if df_tp.empty:
            continue  # Empty frame counts as absent

        found = find_node_at_position(df_tp, pos, distance_threshold, z_scale)
        if found is not None:
            return False

    return True


def match_nodes_spatially(df_t1, df_t2, distance_threshold=2.0, z_scale: float = None):
    """
    Match nodes between two timepoints based on spatial proximity.
    Now allows one-to-many matching: each node in t1 can match multiple nodes in t2.

    Args:
        df_t1: DataFrame for timepoint 1
        df_t2: DataFrame for timepoint 2
        distance_threshold: Maximum distance to consider nodes as the same
        z_scale: Scaling factor for z-dimension (uses app_state resolutions if None)

    Returns:
        Dictionary mapping indices in df_t1 to list of indices in df_t2
    """
    if df_t1.empty or df_t2.empty:
        return {}

    # Use app_state resolutions if z_scale not provided
    if z_scale is None:
        z_scale = app_state.z_resolution / app_state.y_resolution if app_state.y_resolution > 0 else 1.0

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


def classify_network_events(df_t1, df_t2, distance_threshold=2.0, z_scale: float = None,
                            combined_df=None, persistence_window=1):
    """
    Classify network events into 6 specific categories based on degree 1 and 3 nodes with convergence/divergence criteria.

    Event categories with dynamics criteria:
    1. tip-edge fusion: degree 1 node fuses to an edge to make a degree 3 node (requires positive convergence)
    2. junction-breakage: degree 3 node breaks to give an edge and degree 1 node (requires divergence)
    3. tip-tip fusion: two degree 1 nodes come together to make an edge (requires convergence)
    4. tip-tip fission: edge splits to form two degree 1 nodes (requires divergence)
    5. extrusion: tip juts out of an edge leading to additional junction and tip (requires divergence)
    6. retraction: opposite of extrusion (requires convergence)

    Node persistence validation (if combined_df provided and persistence_window > 1):
    - For disappearing nodes: must exist for persistence_window frames BEFORE the event
    - For appearing nodes: must persist for persistence_window frames AFTER the event

    Args:
        df_t1: DataFrame for earlier timepoint
        df_t2: DataFrame for later timepoint
        distance_threshold: Spatial matching threshold
        z_scale: Scaling factor for z-dimension (uses app_state resolutions if None)
        combined_df: Full timeseries DataFrame for node persistence checking (optional)
        persistence_window: Number of frames nodes must exist before/after event (default 1 = no checking)

    Returns:
        Dictionary with classified events
    """
    # Use app_state resolutions if z_scale not provided
    if z_scale is None:
        z_scale = app_state.z_resolution / app_state.y_resolution if app_state.y_resolution > 0 else 1.0

    # Check if dynamics data is available for strict validation
    use_dynamics = has_dynamics_data(df_t1) and has_dynamics_data(df_t2)

    # Get timepoint values for persistence checking
    t1_timepoint = df_t1.iloc[0].get('time_point', None) if len(df_t1) > 0 else None
    t2_timepoint = df_t2.iloc[0].get('time_point', None) if len(df_t2) > 0 else None

    # Calculate frames to check for persistence
    use_persistence = combined_df is not None and persistence_window > 1 and t1_timepoint is not None and t2_timepoint is not None
    if use_persistence:
        all_timepoints = sorted(combined_df['time_point'].unique())
        # Frames before t1 (where disappearing nodes should exist)
        frames_before = [tp for tp in all_timepoints if t1_timepoint - persistence_window < tp < t1_timepoint]
        # Frames after t2 (where appearing nodes should persist)
        frames_after = [tp for tp in all_timepoints if t2_timepoint < tp <= t2_timepoint + persistence_window]

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
                # Check for positive convergence in t2 (strict mode)
                if use_dynamics:
                    convergence_t2 = df_t2.iloc[t2_idx].get('convergence_raw', 0)
                    if convergence_t2 <= 0:
                        continue  # Skip - no convergence signal
                    event_data['convergence'] = convergence_t2
                # Persistence check: tip (degree 1) must have existed before, junction must persist after
                if use_persistence:
                    if frames_before and not check_node_exists_in_frames(combined_df, pos_t1, frames_before, distance_threshold, z_scale):
                        continue  # Tip didn't exist long enough before fusion
                    if frames_after and not check_node_exists_in_frames(combined_df, pos_t2, frames_after, distance_threshold, z_scale):
                        continue  # Junction doesn't persist after fusion
                events['tip_edge_fusion'].append(event_data)

            # 2. Junction breakage: degree ≥3 → degree 1 (junction breaks to become tip)
            # Must be exactly one-to-one transformation with divergence
            elif degree_t1 >= 3 and degree_t2 == 1:
                # Check for divergence in t1 (strict mode)
                if use_dynamics:
                    divergence_t1 = df_t1.iloc[t1_idx].get('divergence_raw', 0)
                    if divergence_t1 <= 0:
                        continue  # Skip - no divergence signal
                    event_data['divergence'] = divergence_t1
                # Persistence check: junction must have existed before, tip must persist after
                if use_persistence:
                    if frames_before and not check_node_exists_in_frames(combined_df, pos_t1, frames_before, distance_threshold, z_scale):
                        continue  # Junction didn't exist long enough before breakage
                    if frames_after and not check_node_exists_in_frames(combined_df, pos_t2, frames_after, distance_threshold, z_scale):
                        continue  # Tip doesn't persist after breakage
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
    # Must be exactly 2 tips that disappear and are within distance threshold with divergence
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

            # Distance filter: tips must be within 2x threshold to fuse
            if distance > distance_threshold * 2:
                continue

            # Check for divergence in both tips (strict mode - from t1 since they're disappearing)
            if use_dynamics:
                divergence_1 = df_t1.iloc[idx1].get('divergence_raw', 0)
                divergence_2 = df_t1.iloc[idx2].get('divergence_raw', 0)
                if divergence_1 <= 0 or divergence_2 <= 0:
                    continue  # Skip - both tips need divergence signal

            # Persistence check: both tips must have existed before fusion, both absent after
            if use_persistence:
                if frames_before:
                    if not check_node_exists_in_frames(combined_df, pos1, frames_before, distance_threshold, z_scale):
                        continue  # Tip 1 didn't exist long enough
                    if not check_node_exists_in_frames(combined_df, pos2, frames_before, distance_threshold, z_scale):
                        continue  # Tip 2 didn't exist long enough
                if frames_after:
                    if not check_node_absent_in_frames(combined_df, pos1, frames_after, distance_threshold, z_scale):
                        continue  # Tip 1 reappears after fusion (not a real fusion)
                    if not check_node_absent_in_frames(combined_df, pos2, frames_after, distance_threshold, z_scale):
                        continue  # Tip 2 reappears after fusion (not a real fusion)

            event_data = {
                'tip1_position': pos1,
                'tip2_position': pos2,
                'distance': distance,
                'timepoint_1': df_t1.iloc[idx1].get('time_point', 'unknown'),
                'timepoint_2': df_t1.iloc[idx1].get('time_point', 'unknown') + 1
            }
            if use_dynamics:
                event_data['divergence_tip1'] = divergence_1
                event_data['divergence_tip2'] = divergence_2
            events['tip_tip_fusion'].append(event_data)

    # 4. Tip-tip fission: two tips appear (edge splits)
    # Heuristic: pairs of nearby appeared tips with convergence (moving apart)
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

            # Distance filter: tips must be within 2x threshold for fission
            if distance > distance_threshold * 2:
                continue

            # Check for convergence in either tip (strict mode - from t2 since they're appearing)
            if use_dynamics:
                convergence_1 = df_t2.iloc[idx1].get('convergence_raw', 0)
                convergence_2 = df_t2.iloc[idx2].get('convergence_raw', 0)
                if convergence_1 <= 0 and convergence_2 <= 0:
                    continue  # Skip - at least one tip needs convergence signal

            # Persistence check: both tips must be absent before, and persist after fission
            if use_persistence:
                if frames_before:
                    if not check_node_absent_in_frames(combined_df, pos1, frames_before, distance_threshold, z_scale):
                        continue  # Tip 1 existed before (not a new fission)
                    if not check_node_absent_in_frames(combined_df, pos2, frames_before, distance_threshold, z_scale):
                        continue  # Tip 2 existed before (not a new fission)
                if frames_after:
                    if not check_node_exists_in_frames(combined_df, pos1, frames_after, distance_threshold, z_scale):
                        continue  # Tip 1 doesn't persist after fission
                    if not check_node_exists_in_frames(combined_df, pos2, frames_after, distance_threshold, z_scale):
                        continue  # Tip 2 doesn't persist after fission

            event_data = {
                'tip1_position': pos1,
                'tip2_position': pos2,
                'distance': distance,
                'timepoint_1': df_t2.iloc[idx1].get('time_point', 'unknown') - 1,
                'timepoint_2': df_t2.iloc[idx1].get('time_point', 'unknown')
            }
            if use_dynamics:
                event_data['convergence_tip1'] = convergence_1
                event_data['convergence_tip2'] = convergence_2
            events['tip_tip_fission'].append(event_data)

    # 5. Extrusion: new tip and junction appear (tip juts out of edge)
    # Heuristic: nearby appeared tip and junction pairs that are adjacent, with negative convergence
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

            # Distance filter: tip and junction must be close
            if distance > distance_threshold:
                continue

            # Adjacency validation: tip must be connected to junction
            if not are_nodes_adjacent(df_t2, tip_idx, junction_idx):
                continue

            # Check for negative convergence in tip or junction (strict mode - material extending out)
            if use_dynamics:
                convergence_tip = df_t2.iloc[tip_idx].get('convergence_raw', 0)
                convergence_junction = df_t2.iloc[junction_idx].get('convergence_raw', 0)
                if convergence_tip >= 0 and convergence_junction >= 0:
                    continue  # Skip - need negative convergence (extension)

            # Persistence check: only junction (tip moves too fast for reliable tracking)
            if use_persistence:
                if frames_before:
                    if not check_node_absent_in_frames(combined_df, junction_pos, frames_before, distance_threshold, z_scale):
                        continue  # Junction existed before (not a new extrusion)
                if frames_after:
                    if not check_node_exists_in_frames(combined_df, junction_pos, frames_after, distance_threshold, z_scale):
                        continue  # Junction doesn't persist after extrusion

            event_data = {
                'tip_position': tip_pos,
                'junction_position': junction_pos,
                'distance': distance,
                'timepoint_1': df_t2.iloc[tip_idx].get('time_point', 'unknown') - 1,
                'timepoint_2': df_t2.iloc[tip_idx].get('time_point', 'unknown')
            }
            if use_dynamics:
                event_data['convergence_tip'] = convergence_tip
                event_data['convergence_junction'] = convergence_junction
            events['extrusion'].append(event_data)

    # 6. Retraction: tip and junction disappear (opposite of extrusion)
    # Heuristic: nearby disappeared tip and junction pairs that were adjacent, with positive divergence
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

            # Distance filter: tip and junction must be close
            if distance > distance_threshold:
                continue

            # Adjacency validation: tip must have been connected to junction
            if not are_nodes_adjacent(df_t1, tip_idx, junction_idx):
                continue

            # Check for positive divergence in tip or junction (strict mode - material pulling back)
            if use_dynamics:
                divergence_tip = df_t1.iloc[tip_idx].get('divergence_raw', 0)
                divergence_junction = df_t1.iloc[junction_idx].get('divergence_raw', 0)
                if divergence_tip <= 0 and divergence_junction <= 0:
                    continue  # Skip - need positive divergence (retraction)

            # Persistence check: only junction (tip moves too fast for reliable tracking)
            if use_persistence:
                if frames_before:
                    if not check_node_exists_in_frames(combined_df, junction_pos, frames_before, distance_threshold, z_scale):
                        continue  # Junction didn't exist long enough before retraction
                if frames_after:
                    if not check_node_absent_in_frames(combined_df, junction_pos, frames_after, distance_threshold, z_scale):
                        continue  # Junction reappears after retraction (not a real retraction)

            event_data = {
                'tip_position': tip_pos,
                'junction_position': junction_pos,
                'distance': distance,
                'timepoint_1': df_t1.iloc[tip_idx].get('time_point', 'unknown'),
                'timepoint_2': df_t1.iloc[tip_idx].get('time_point', 'unknown') + 1
            }
            if use_dynamics:
                event_data['divergence_tip'] = divergence_tip
                event_data['divergence_junction'] = divergence_junction
            events['retraction'].append(event_data)

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


def analyze_timeseries_events(combined_df, distance_threshold=2.0, persistence_window=1):
    """
    Analyze all events across the entire time series using the 6-category classification.

    Node persistence validation:
    - For disappearing nodes: must exist for persistence_window frames BEFORE the event
    - For appearing nodes: must persist for persistence_window frames AFTER the event

    Args:
        combined_df: Combined DataFrame from timeseries_reader
        distance_threshold: Spatial matching threshold
        persistence_window: Number of frames nodes must exist before/after event (1 = no validation)

    Returns:
        Dictionary with all detected events classified into 6 categories
    """
    time_points = sorted(combined_df['time_point'].unique())

    # Get z_scale from app_state
    z_scale = app_state.z_resolution / app_state.y_resolution if app_state.y_resolution > 0 else 1.0

    all_events = {
        'tip_edge_fusion_events': [],
        'junction_breakage_events': [],
        'tip_tip_fusion_events': [],
        'tip_tip_fission_events': [],
        'extrusion_events': [],
        'retraction_events': []
    }

    # Collect events from each frame transition
    for i in range(len(time_points) - 1):
        t1, t2 = time_points[i], time_points[i + 1]

        df_t1 = combined_df[combined_df['time_point'] == t1]
        df_t2 = combined_df[combined_df['time_point'] == t2]

        # Classify events with node persistence validation
        events = classify_network_events(
            df_t1, df_t2, distance_threshold, z_scale,
            combined_df=combined_df, persistence_window=persistence_window
        )

        # Aggregate events
        all_events['tip_edge_fusion_events'].extend(events['tip_edge_fusion'])
        all_events['junction_breakage_events'].extend(events['junction_breakage'])
        all_events['tip_tip_fusion_events'].extend(events['tip_tip_fusion'])
        all_events['tip_tip_fission_events'].extend(events['tip_tip_fission'])
        all_events['extrusion_events'].extend(events['extrusion'])
        all_events['retraction_events'].extend(events['retraction'])

    # Calculate summary stats
    summary_stats = {
        'total_tip_edge_fusion': len(all_events['tip_edge_fusion_events']),
        'total_junction_breakage': len(all_events['junction_breakage_events']),
        'total_tip_tip_fusion': len(all_events['tip_tip_fusion_events']),
        'total_tip_tip_fission': len(all_events['tip_tip_fission_events']),
        'total_extrusion': len(all_events['extrusion_events']),
        'total_retraction': len(all_events['retraction_events'])
    }

    all_events['summary_statistics'] = summary_stats

    return all_events


if __name__ == "__main__":
    import sys
    from .timeseries_reader import read_timeseries_csvs

    if len(sys.argv) > 1:
        base_folder = sys.argv[1]
        distance_threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
        persistence_window = int(sys.argv[3]) if len(sys.argv) > 3 else 1

        print("Loading time series data...")
        df = read_timeseries_csvs(base_folder)

        print("Analyzing events using 6-category classification...")
        print(f"  Distance threshold: {distance_threshold} px")
        print(f"  Persistence window: {persistence_window} frames")
        events = analyze_timeseries_events(df, distance_threshold, persistence_window)
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
        print("Usage: python event_detector.py <base_folder_path> [distance_threshold] [persistence_window]")