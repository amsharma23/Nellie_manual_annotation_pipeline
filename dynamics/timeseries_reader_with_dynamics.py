#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 2025

@author: amansharma

Time series adjacency list with dynamics CSV reader for analyzing network dynamics with divergence/convergence data.
"""

import os
import pandas as pd
from natsort import natsorted
import glob
from typing import Optional


def read_timeseries_csvs(base_folder: str) -> pd.DataFrame:
    """
    Read all adjacency list with dynamics CSVs from time series folders and combine into single DataFrame.

    Looks for *_adjacency_list_with_dynamics.csv files which include divergence and convergence columns.

    Args:
        base_folder: Path to the base folder containing time point subdirectories (1, 2, 3, etc.)

    Returns:
        Combined pandas DataFrame with all adjacency data, dynamics data, and time_point column
    """
    if not os.path.exists(base_folder):
        raise FileNotFoundError(f"Base folder not found: {base_folder}")

    # Find all subdirectories that are numeric (time points)
    subdirs = [d for d in os.listdir(base_folder)
              if os.path.isdir(os.path.join(base_folder, d)) and d.isdigit()]

    time_points = natsorted(subdirs)
    print(f"Found {len(time_points)} time points: {time_points}")

    all_data = []

    for time_point in time_points:
        print(f"Loading adjacency data for time point {time_point}...")

        # Construct path to adjacency CSV
        time_point_path = os.path.join(base_folder, time_point)
        nellie_path = os.path.join(time_point_path, 'nellie_output', 'nellie_necessities')

        if not os.path.exists(nellie_path):
            print(f"  Nellie output path not found: {nellie_path}")
            continue

        # Look for adjacency list with dynamics CSV files
        dynamics_files = glob.glob(os.path.join(nellie_path, '*_adjacency_list_with_dynamics.csv'))
        adjacency_files = glob.glob(os.path.join(nellie_path, '*_adjacency_list.csv'))
        if not dynamics_files:
            print(f"  No adjacency list with dynamics CSV found")
            continue
        elif len(dynamics_files) > 1:
            print(f"  Multiple dynamics CSVs found, using first: {dynamics_files[0]}")

        csv_path = dynamics_files[0]

        # Read the CSV
        try:
            df = pd.read_csv(csv_path)
            # Add time point column
            df['time_point'] = int(time_point)

            all_data.append(df)
            print(f"  Loaded {len(df)} nodes")

        except Exception as e:
            print(f"  Error reading CSV {csv_path}: {str(e)}")
            continue

    if not all_data:
        print("No adjacency data found!")
        return pd.DataFrame()

    # Combine all DataFrames
    combined_df = pd.concat(all_data, ignore_index=True)

    print(f"\nCombined database created with {len(combined_df)} total rows across {len(time_points)} time points")
    print(f"Columns: {combined_df.columns.tolist()}")

    return combined_df


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        base_folder = sys.argv[1]
        df = read_timeseries_csvs(base_folder)
        df.to_csv(os.path.join(base_folder, "combined_timeseries_adjacency_with_dynamics.csv"), index=False)
        print(f"\nFirst few rows:")
        print(df.head())
        print(f"\nDatabase info:")
        print(df.info())
    else:
        print("Usage: python timeseries_reader_with_dynamics.py <base_folder_path>")