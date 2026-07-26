#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
State for the standalone Dynamic-Event Annotation tool.

This is a stripped-down version of the full Nellie pipeline's AppState: it keeps
only what dynamic-event annotation needs (loaded paths, resolutions, and the
4D-view flag). No network, no Nellie processing, no automated dynamics analysis.
"""


class AppState:
    def __init__(self):
        # Paths of the two loaded 4D OME-TIFFs
        self.raw_path = None
        self.skel_path = None
        # Folder where event CSVs are written (a per-dataset subfolder)
        self.loaded_folder = None
        # Napari layers
        self.raw_layer = None
        self.skeleton_layer = None
        # Number of timepoints in the loaded stack
        self.num_t = 0
        # Always True once a 4D stack is viewed; the event code branches on it.
        self.is_timeseries_4d = False
        # Dimension resolutions (µm)
        self.z_resolution = 0.292
        self.y_resolution = 0.11
        self.x_resolution = 0.11

    @property
    def visualization_scale(self):
        """Return [Z, Y, X] scale for napari display.

        Z is scaled relative to Y to account for anisotropic voxels.
        """
        z_scale = self.z_resolution / self.y_resolution if self.y_resolution > 0 else 1.0
        return [z_scale, 1, 1]

    def reset(self):
        """Reset per-dataset state. Resolutions persist (user preference)."""
        self.raw_path = None
        self.skel_path = None
        self.loaded_folder = None
        self.raw_layer = None
        self.skeleton_layer = None
        self.num_t = 0
        self.is_timeseries_4d = False


app_state = AppState()
