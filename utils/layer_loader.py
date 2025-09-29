#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 17:14:32 2025

@author: amansharma
"""
from tifffile import imread
import os
from napari.utils.notifications import show_info, show_warning, show_error
from .adjacency_reader import adjacency_to_extracted
import pandas as pd
from app_state import app_state
import numpy as np
from .parsing import get_float_pos_comma
import glob

def load_image_and_skeleton(nellie_output_path):
    """Load raw image and skeleton from Nellie output directory.
    
    Args:
        nellie_output_path (str): Path to Nellie output directory
        
    Returns:
        tuple: (raw_image, skeleton_image, face_colors, positions, colors)
    """
    try:
        # Find relevant files in the output directory
        tif_files = os.listdir(nellie_output_path)
        
        # Find raw image file (channel 0)
        raw_files = [f for f in tif_files if f.endswith('-ch0.ome.tif')]
        if not raw_files:
            show_error("No raw image file found in the output directory: " + nellie_output_path)
            return None, None, [], [], []
            
        raw_file = raw_files[0]
        basename = raw_file.split(".")[0]
        
        # Find skeleton image file
        skel_files = [f for f in tif_files if f.endswith('-ch0-im_pixel_class.ome.tif')]
        if not skel_files:
            show_error("No skeleton file found in the output directory")
            return None, None, [], [], []
        else:
            app_state.nellie_output_path = nellie_output_path
            
        skel_file = skel_files[0]
        
        # Get full paths
        raw_im_path = os.path.join(nellie_output_path, raw_file)
        skel_im_path = os.path.join(nellie_output_path, skel_file)
        
        # Check for node data file
        node_path_extracted = os.path.join(nellie_output_path, f"{basename}_extracted.csv")
        adjacency_path = os.path.join(nellie_output_path, f"{basename}_adjacency_list.csv")
        app_state.node_path = node_path_extracted
        
        # Load images
        raw_im = imread(raw_im_path)
        skel_im = imread(skel_im_path)
        skel_im = np.transpose(np.nonzero(skel_im))
        
        # Default all points to red
        face_color_arr = ['red' for _ in range(len(skel_im))]
        
        #Check if an adjaceny list exists and convert to extracted csv if so
        if os.path.exists(adjacency_path) and not os.path.exists(node_path_extracted):
            adjacency_to_extracted(node_path_extracted,adjacency_path)
        
        if os.path.exists(adjacency_path) and os.path.exists(node_path_extracted):
            node_df = pd.read_csv(node_path_extracted)
            # normalize legacy column name 'Node ID' to 'node'
            if 'Node ID' in node_df.columns:
                node_df.rename(columns={'Node ID': 'node'}, inplace=True)
            # ensure a 'node' column exists (create from index if missing)
            if 'node' not in node_df.columns:
                node_df = node_df.reset_index(drop=True)
                node_df['node'] = node_df.index + 1
            # coerce to int for consistency
            try:
                node_df['node'] = node_df['node'].astype(int)
            except Exception:
                pass
            app_state.node_dataframe = node_df            
            if node_df.empty or pd.isna(node_df.index.max()):
                adjacency_to_extracted(node_path_extracted,adjacency_path)
        
        # Process extracted nodes if available
        if os.path.exists(node_path_extracted):
            node_df = pd.read_csv(node_path_extracted)
            # normalize legacy column name 'Node ID' to 'node'
            if 'Node ID' in node_df.columns:
                node_df.rename(columns={'Node ID': 'node'}, inplace=True)
            if 'node' not in node_df.columns:
                node_df = node_df.reset_index(drop=True)
                node_df['node'] = node_df.index + 1
            try:
                node_df['node'] = node_df['node'].astype(int)
            except Exception:
                pass
            app_state.node_dataframe = node_df
            
            if not node_df.empty and not pd.isna(node_df.index.max()):
                # Extract node positions and degrees
                pos_extracted = node_df['Position(ZXY)'].values
                show_info(f"Extracted positions: {pos_extracted}")
                
                deg_extracted = node_df['Degree of Node'].values.astype(int)
                positions = [get_float_pos_comma(el) for el in pos_extracted]
                # Generate colors based on node degree
                colors = []
                for i, degree in enumerate(deg_extracted):
                    if degree == 1:
                        colors.append('blue')  # Endpoint nodes
                    elif degree == 0:
                        colors.append('white')  # Isolated nodes
                    elif degree == 2:
                        colors.append('magenta')  
                    else:
                        colors.append('green')  # Junction nodes
                #Map skeleton points to node colors if they match positions   
                position_color_map = {}
                for i,pos in enumerate(positions):
                    position_color_map[tuple(pos)] = colors[i]
                #update face colors for skeleton points that match node positions
                for i, point in enumerate(skel_im):
                    point_tuple = tuple(point)
                    if point_tuple in position_color_map:
                        face_color_arr[i] = position_color_map[point_tuple]

                return raw_im, skel_im, face_color_arr, positions, colors
                
            else:
                # Create empty dataframe if no data
                app_state.node_dataframe = pd.DataFrame(columns=['node','Degree of Node', 'Position(ZXY)'])
                app_state.node_dataframe.to_csv(node_path_extracted, index=False)
                return raw_im, skel_im, face_color_arr, [], []
        else:
            # Create new node file if none exists
            app_state.node_dataframe = pd.DataFrame(columns=['node','Degree of Node', 'Position(ZXY)'])
            app_state.node_dataframe.to_csv(node_path_extracted, index=False)
            return raw_im, skel_im, face_color_arr, [], []
            
    except Exception as e:
        show_error(f"Error loading image and skeleton: {str(e)}")
        return None, None, [], [], []


def load_dynamics_events_layer(viewer, current_timepoint=None):
    """
    Load dynamic events as color-coded points layer in the Napari viewer.

    Args:
        viewer: Napari viewer instance
        current_timepoint: Current timepoint to filter events (optional)

    Returns:
        bool: True if events were loaded successfully, False otherwise
    """
    if not app_state.loaded_folder:
        return False

    # Look for dynamics analysis results CSV files directly in loaded folder
    dynamics_folder = app_state.loaded_folder

    # Define event types and their colors (avoiding network node colors: blue, white, magenta, green, red)
    event_types = {
        'tip_edge_fusion_events.csv': {'color': 'gold', 'name': 'Tip-Edge Fusion'},
        'junction_breakage_events.csv': {'color': 'darkorange', 'name': 'Junction Breakage'},
        'tip_tip_fusion_events.csv': {'color': 'purple', 'name': 'Tip-Tip Fusion'},
        'tip_tip_fission_events.csv': {'color': 'turquoise', 'name': 'Tip-Tip Fission'},
        'extrusion_events.csv': {'color': 'lime', 'name': 'Extrusion'},
        'retraction_events.csv': {'color': 'olive', 'name': 'Retraction'}
    }

    all_points = []
    all_colors = []
    all_properties = []

    try:
        for csv_file, config in event_types.items():
            csv_path = os.path.join(dynamics_folder, csv_file)

            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)

                if df.empty:
                    continue

                # Extract points and filter by timepoint if specified
                points, colors, properties = extract_event_points(df, config, current_timepoint)

                all_points.extend(points)
                all_colors.extend(colors)
                all_properties.extend(properties)

        if all_points:
            # Remove existing dynamics events layer if it exists
            layer_names = [layer.name for layer in viewer.layers]
            if "Dynamic Events" in layer_names:
                viewer.layers.remove("Dynamic Events")

            # Add new points layer
            points_array = np.array(all_points)
            properties_dict = {
                'event_type': [prop['event_type'] for prop in all_properties],
                'timepoint': [prop['timepoint'] for prop in all_properties]
            }

            viewer.add_points(
                points_array,
                properties=properties_dict,
                face_color=all_colors,
                size=8,
                opacity=0.5,
                name="Dynamic Events"
            )

            show_info(f"Loaded {len(all_points)} dynamic events for timepoint {current_timepoint if current_timepoint else 'all'}")
            return True

    except Exception as e:
        show_error(f"Error loading dynamics events: {str(e)}")
        return False

    return False


def extract_event_points(df, config, current_timepoint=None):
    """
    Extract points from event DataFrame based on event type structure.

    Args:
        df: Event DataFrame
        config: Event configuration (color, name)
        current_timepoint: Current timepoint to filter by

    Returns:
        tuple: (points, colors, properties)
    """
    points = []
    colors = []
    properties = []

    for _, row in df.iterrows():
        event_points = []
        event_timepoint = None

        # Handle different event structures - always use timepoint_2
        if 'position_t1' in row and 'position_t2' in row:
            # Events with two timepoints (tip-edge fusion, junction breakage)
            if 'timepoint_2' in row:
                timepoint_2 = row['timepoint_2']
                if current_timepoint is None or current_timepoint == timepoint_2:
                    pos_2 = parse_position(row['position_t2'])
                    if pos_2:
                        event_points.append(pos_2)
                        event_timepoint = timepoint_2

        elif 'tip1_position' in row and 'tip2_position' in row:
            # Tip-tip events
            if 'timepoint_2' in row:
                timepoint_2 = row['timepoint_2']
                if current_timepoint is None or current_timepoint == timepoint_2:
                    pos_1 = parse_position(row['tip1_position'])
                    pos_2 = parse_position(row['tip2_position'])
                    if pos_1 and pos_2:
                        event_points.extend([pos_1, pos_2])
                        event_timepoint = timepoint_2

        elif 'tip_position' in row and 'junction_position' in row:
            # Extrusion/retraction events
            if 'timepoint_2' in row:
                timepoint_2 = row['timepoint_2']
                if current_timepoint is None or current_timepoint == timepoint_2:
                    tip_pos = parse_position(row['tip_position'])
                    junction_pos = parse_position(row['junction_position'])
                    if tip_pos and junction_pos:
                        event_points.extend([tip_pos, junction_pos])
                        event_timepoint = timepoint_2

        # Add points to lists
        for point in event_points:
            points.append(point)
            colors.append(config['color'])
            properties.append({
                'event_type': config['name'],
                'timepoint': event_timepoint
            })

    return points, colors, properties


def parse_position(position):
    """
    Parse position from various formats (list, string, etc.)

    Args:
        position: Position data in various formats

    Returns:
        list: [z, y, x] coordinates or None if parsing fails
    """
    try:
        if isinstance(position, str):
            # Handle string representation of list
            import ast
            position = ast.literal_eval(position)

        if isinstance(position, (list, tuple)) and len(position) >= 3:
            # Return as [z, y, x] for Napari
            return [float(position[2]), float(position[1]), float(position[0])]

    except Exception:
        pass

    return None