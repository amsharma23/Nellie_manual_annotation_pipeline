#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 16:58:26 2025

@author: amansharma
"""

"""
State management for the Nellie Napari plugin.
"""

class AppState:
    def __init__(self):
        self.loaded_folder = None
        self.folder_type = "Single TIFF"
        self.current_extracted_file = ""
        self.nellie_output_path = None
        self.raw_layer = None
        self.skeleton_layer = None
        self.points_layer = None
        self.highlighted_layer = None
        self.node_path = None
        self.node_dataframe = None
        self.slider_images = []
        self.current_image_index = 0  # Current image index
        self.image_sets_keys = []
        self.image_sets = {}
        self.editable_node_positions = []
        self.selected_node_position = None
        self.graph_image_path = ""
        # Dynamics analysis
        self.combined_timeseries_df = None
        self.dynamics_events = None
        self.dynamics_analysis_results = None
        # Skeleton coordinates for point insertion
        self.skeleton_coords = None

    def reset(self):
        """Reset all state variables to their initial values."""
        self.loaded_folder = None
        self.current_extracted_file = ""
        self.nellie_output_path = None
        self.raw_layer = None
        self.skeleton_layer = None
        self.points_layer = None
        self.highlighted_layer = None
        self.node_path = None
        self.node_dataframe = None
        self.slider_images = []
        self.current_image_index = 0
        self.image_sets_keys = []
        self.image_sets = {}
        self.editable_node_positions = []
        self.selected_node_position = None
        self.graph_image_path = ""
        self.combined_timeseries_df = None
        self.dynamics_events = None
        self.dynamics_analysis_results = None
        self.skeleton_coords = None

app_state = AppState()