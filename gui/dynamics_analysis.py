#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 2025

@author: amansharma

Dynamics analysis integration for the GUI.
"""

import os
import pandas as pd
from app_state import app_state
from dynamics.timeseries_reader import read_timeseries_csvs
from dynamics.analyze_events import analyze_events_from_csv


def analyze_dynamics_clicked(widget):
    """
    Handle analyze dynamics button click.

    First checks if combined_timeseries_adjacency.csv exists in loaded folder.
    If not, calls timeseries_reader first, then analyze_events.

    Args:
        widget: The FileLoaderWidget instance
    """
    if not app_state.loaded_folder:
        widget.log_status("No folder selected. Please browse to a time series folder first.")
        return

    if app_state.folder_type != "Time Series":
        widget.log_status("Dynamics analysis only available for Time Series data.")
        return

    widget.log_status("Starting dynamics analysis...")

    try:
        # Check if combined CSV already exists
        combined_csv_path = os.path.join(app_state.loaded_folder, "combined_timeseries_adjacency.csv")

        if os.path.exists(combined_csv_path):
            widget.log_status(f"Found existing combined CSV: {combined_csv_path}")
            # Load existing combined data
            app_state.combined_timeseries_df = pd.read_csv(combined_csv_path)
            widget.log_status(f"Loaded {len(app_state.combined_timeseries_df)} rows from existing CSV")
        else:
            widget.log_status("Combined CSV not found. Reading individual time series files...")
            # Call timeseries_reader to create combined CSV
            app_state.combined_timeseries_df = read_timeseries_csvs(app_state.loaded_folder)

            if app_state.combined_timeseries_df.empty:
                widget.log_status("No time series data found in the selected folder.")
                return

            # Save the combined CSV for future use
            app_state.combined_timeseries_df.to_csv(combined_csv_path, index=False)
            widget.log_status(f"Created combined CSV: {combined_csv_path}")

        # Now run the dynamics analysis using the CSV file
        widget.log_status("Analyzing network dynamics events...")

        # Get distance threshold from GUI (default 5.0 for now)
        distance_threshold = getattr(widget, 'distance_threshold', 5.0)

        # Run event analysis using the CSV file
        app_state.dynamics_events = analyze_events_from_csv(
            combined_csv_path,
            distance_threshold=distance_threshold
        )

        widget.log_status("Dynamics analysis completed successfully!")

    except Exception as e:
        widget.log_status(f"Error during dynamics analysis: {str(e)}")
        print(f"Dynamics analysis error: {e}")