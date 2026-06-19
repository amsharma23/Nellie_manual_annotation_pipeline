#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 2025

@author: amansharma

Time series adjacency list with dynamics CSV reader for analyzing network dynamics with divergence/convergence data.
"""

import os
import re
import pandas as pd
from natsort import natsorted
import glob
from typing import Optional


def read_4d_stack_csvs(nellie_output_path: str) -> pd.DataFrame:
    """Read per-frame adjacency CSVs from a single 4D-stack output folder.

    4D Stack mode writes one network per timepoint into the single
    ``nellie_necessities`` folder as ``{base}_t{idx:04d}_adjacency_list.csv``
    (and, if present, ``..._adjacency_list_with_dynamics.csv``). This collects
    them, tags each with ``time_point = idx + 1`` (1-indexed, matching the
    numbered-folder Time Series convention and the manual event keys), and
    concatenates into one DataFrame.

    Args:
        nellie_output_path: the single nellie_necessities folder.

    Returns:
        Combined DataFrame (same shape as `read_timeseries_csvs`).
    """
    if not nellie_output_path or not os.path.exists(nellie_output_path):
        raise FileNotFoundError(f"4D output folder not found: {nellie_output_path}")

    def _t_of(path):
        m = re.search(r'_t(\d+)_adjacency_list', os.path.basename(path))
        return int(m.group(1)) if m else None

    # Prefer the dynamics variant per frame; fall back to plain adjacency.
    chosen = {}
    for p in glob.glob(os.path.join(nellie_output_path, '*_t*_adjacency_list.csv')):
        t = _t_of(p)
        if t is not None:
            chosen[t] = p
    for p in glob.glob(os.path.join(nellie_output_path, '*_t*_adjacency_list_with_dynamics.csv')):
        t = _t_of(p)
        if t is not None:
            chosen[t] = p  # override with the dynamics-augmented CSV

    if not chosen:
        print("No per-frame adjacency CSVs found in", nellie_output_path)
        return pd.DataFrame()

    all_data = []
    for t in sorted(chosen):
        try:
            df = pd.read_csv(chosen[t])
            df['time_point'] = t + 1  # 1-indexed
            all_data.append(df)
            print(f"  Loaded {len(df)} nodes for frame t={t} (time_point {t + 1})")
        except Exception as e:
            print(f"  Error reading {chosen[t]}: {e}")

    if not all_data:
        return pd.DataFrame()

    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"\nCombined 4D-stack database: {len(combined_df)} rows across "
          f"{len(all_data)} timepoints")
    return combined_df


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
        if not dynamics_files and not adjacency_files:
            print(f"  No adjacency list with dynamics CSV found")
            continue
        elif len(dynamics_files) > 1:
            print(f"  Multiple dynamics CSVs found, using first: {dynamics_files[0]}")

        if dynamics_files:
            csv_path = dynamics_files[0]
        elif adjacency_files:
            print(f"  No dynamics CSV found, falling back to adjacency list CSV")
            csv_path = adjacency_files[0]

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