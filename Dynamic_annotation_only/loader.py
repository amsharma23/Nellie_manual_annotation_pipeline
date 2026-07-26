#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Loading helpers for the standalone Dynamic-Event Annotation tool.

Loads a raw 4D OME-TIFF and a skeleton (pixel-class) 4D OME-TIFF as napari
layers, and renders saved event CSVs as a single 4D points layer. No network
generation and no Nellie dependency.
"""
import os
import ast
import numpy as np
import pandas as pd
from tifffile import imread
from napari.utils.notifications import show_info, show_error

from app_state import app_state


def load_two_file_4d(raw_path, skel_path):
    """Load a raw 4D OME-TIFF and a skeleton 4D OME-TIFF.

    Both must be shaped (T, Z, Y, X) with matching T/Z/Y/X. The skeleton is any
    label/binary image; its non-zero voxels become the Skeleton points layer.

    Returns a dict with:
        raw_4d      : np.ndarray (T, Z, Y, X)
        skel_points : np.ndarray (N, 4), columns [t, z, y, x]
        face_colors : list[str], length N (all 'red')
        num_t       : int
    Or None on failure (an error notification is shown).
    """
    if not raw_path or not os.path.exists(raw_path):
        show_error(f"Raw stack not found: {raw_path}")
        return None
    if not skel_path or not os.path.exists(skel_path):
        show_error(f"Skeleton stack not found: {skel_path}")
        return None

    raw_4d = imread(raw_path)
    skel_4d = imread(skel_path)

    if raw_4d.ndim != 4:
        show_error(
            f"Expected a 4D raw image (T, Z, Y, X) but got shape {raw_4d.shape}."
        )
        return None
    if skel_4d.ndim != 4:
        show_error(
            f"Expected a 4D skeleton image (T, Z, Y, X) but got shape {skel_4d.shape}."
        )
        return None
    if skel_4d.shape[0] != raw_4d.shape[0]:
        show_error(
            f"Timepoint mismatch: raw has {raw_4d.shape[0]} frames, skeleton has "
            f"{skel_4d.shape[0]}."
        )
        return None
    if skel_4d.shape[1:] != raw_4d.shape[1:]:
        show_error(
            f"Spatial-shape mismatch: raw {raw_4d.shape[1:]} vs skeleton "
            f"{skel_4d.shape[1:]}."
        )
        return None

    num_t = raw_4d.shape[0]

    # Build 4D skeleton points: for each frame, prefix non-zero (z,y,x) with t.
    parts = []
    for t in range(num_t):
        sc = np.transpose(np.nonzero(skel_4d[t]))  # (N_t, 3) ints
        if len(sc) == 0:
            continue
        t_col = np.full((sc.shape[0], 1), t, dtype=sc.dtype)
        parts.append(np.hstack([t_col, sc]))
    if parts:
        skel_points = np.concatenate(parts, axis=0)
    else:
        skel_points = np.zeros((0, 4), dtype=int)

    face_colors = ['red'] * len(skel_points)

    return {
        'raw_4d': raw_4d,
        'skel_points': skel_points,
        'face_colors': face_colors,
        'num_t': num_t,
    }


# ----- Event rendering (saved CSVs -> a single 4D points layer) -----

EVENT_CSV_CONFIG = {
    'tip_edge_fusion_events.csv': {'color': '#FFC04D', 'name': 'Tip-Edge Fusion'},
    'junction_breakage_events.csv': {'color': '#E67300', 'name': 'Junction Breakage'},
    'tip_tip_fusion_events.csv': {'color': '#B57EDC', 'name': 'Tip-Tip Fusion'},
    'tip_tip_fission_events.csv': {'color': '#6A2C91', 'name': 'Tip-Tip Fission'},
    'extrusion_events.csv': {'color': '#4FD0C4', 'name': 'Extrusion'},
    'retraction_events.csv': {'color': '#157A6E', 'name': 'Retraction'},
}


def parse_position(position):
    """Parse a stored position into napari [z, y, x], or None.

    Stored positions are [x, y, z]; napari wants [z, y, x].
    """
    try:
        if isinstance(position, str):
            position = ast.literal_eval(position)
        if isinstance(position, (list, tuple)) and len(position) >= 3:
            return [float(position[2]), float(position[1]), float(position[0])]
    except Exception:
        pass
    return None


def extract_event_points(df, config, csv_file):
    """Yield (point[z,y,x], color, properties) for each row of an event CSV."""
    points, colors, properties = [], [], []
    for row_idx, row in df.iterrows():
        if 'timepoint_2' not in row:
            continue
        tp2 = row['timepoint_2']
        pos = None
        if 'position' in row and pd.notna(row.get('position')):
            pos = parse_position(row['position'])
        if pos is None:
            continue
        points.append(pos)
        colors.append(config['color'])
        properties.append({
            'event_type': config['name'],
            'timepoint': tp2,
            'csv_row_index': row_idx,
            'csv_file': csv_file,
        })
    return points, colors, properties


def load_dynamics_events_layer_4d(viewer):
    """Render all saved event CSVs as one 4D points layer (T, Z, Y, X).

    napari's native T-slider then filters them per frame. No-op if no events.
    """
    if not app_state.loaded_folder:
        return False

    folder = app_state.loaded_folder
    all_points, all_colors, all_properties = [], [], []

    try:
        for csv_file, config in EVENT_CSV_CONFIG.items():
            csv_path = os.path.join(folder, csv_file)
            if not os.path.exists(csv_path):
                continue
            df = pd.read_csv(csv_path)
            if df.empty:
                continue
            pts, cols, props = extract_event_points(df, config, csv_file)
            for pt, col, prop in zip(pts, cols, props):
                tp = prop.get('timepoint')
                if tp is None:
                    continue
                # Stored timepoint is 1-indexed; napari's T axis is 0-indexed.
                t_idx = int(tp) - 1
                all_points.append([t_idx, pt[0], pt[1], pt[2]])
                all_colors.append(col)
                all_properties.append(prop)

        # Always replace the layer so deletions are reflected.
        if "Dynamic Events" in [layer.name for layer in viewer.layers]:
            viewer.layers.remove("Dynamic Events")

        if not all_points:
            return False

        points_array = np.array(all_points)
        properties_dict = {
            'event_type': [p['event_type'] for p in all_properties],
            'timepoint': [p['timepoint'] for p in all_properties],
            'csv_row_index': [p['csv_row_index'] for p in all_properties],
            'csv_file': [p['csv_file'] for p in all_properties],
        }
        scale_4d = [1] + list(app_state.visualization_scale)

        viewer.add_points(
            points_array,
            properties=properties_dict,
            face_color=all_colors,
            size=8,
            opacity=0.5,
            scale=scale_4d,
            name="Dynamic Events",
        )
        show_info(f"Loaded {len(all_points)} dynamic events across all timepoints.")
        return True

    except Exception as e:
        show_error(f"Error loading dynamics events (4D): {e}")
        return False
