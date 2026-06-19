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
        # Dimension resolutions (µm)
        self.z_resolution = 0.292
        self.y_resolution = 0.11
        self.x_resolution = 0.11
        # Dynamics analysis parameters
        self.distance_threshold = 5.0  # pixels - spatial matching threshold for nodes
        self.persistence_window = 1    # frames - validation window for events
        # 4D time series state (populated when a Time Series is viewed as a 4D stack)
        self.timepoint_paths = []        # list[str]: nellie_output_path per frame, indexed by T
        self.ts_per_frame = []           # list[dict]: cached _load_frame_data output per frame
        self.is_timeseries_4d = False    # True while the 4D stacked view is active
        self.skeleton_coords_per_frame = []  # list[np.ndarray (N_t, 3)]: per-frame skeleton voxels
        # 4D Stack state (single 4D OME-TIFF processed natively in one Nellie run)
        self.loaded_file = None          # str: path to the selected 4D .ome.tif
        self.is_4d_stack = False         # True when the active 4D view came from a single 4D stack
        self.single_output_path = None   # str: the one nellie_necessities folder holding 4D outputs
        self.frame_csv_paths = []        # list[str]: per-frame extracted CSV path inside single_output_path
        self.pixel_class_basename = None # str: basename (no ext) of the 4D pixel-class file; drives per-frame CSV names

    @property
    def visualization_scale(self):
        """Calculate [Z, Y, X] scale for napari visualization.

        Z is scaled relative to Y to account for anisotropic voxel sizes.
        Larger Z voxels need to be stretched in the display.
        """
        z_scale = self.z_resolution / self.y_resolution if self.y_resolution > 0 else 1.0
        return [z_scale, 1, 1]

    def reset(self):
        """Reset all state variables to their initial values.

        Note: Resolution settings are NOT reset as they are user preferences
        that should persist across folder changes.
        """
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
        self.timepoint_paths = []
        self.ts_per_frame = []
        self.is_timeseries_4d = False
        self.skeleton_coords_per_frame = []
        self.loaded_file = None
        self.is_4d_stack = False
        self.single_output_path = None
        self.frame_csv_paths = []
        self.pixel_class_basename = None

app_state = AppState()