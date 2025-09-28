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
                    else:
                        colors.append('green')  # Junction nodes
                        
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