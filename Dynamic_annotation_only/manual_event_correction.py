#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual annotation of dynamic events (standalone).

Interactive tools to add an event at the selected skeleton point, delete the
selected event, and show event info. Events are stored as per-type CSVs in the
per-dataset annotation folder (app_state.loaded_folder).
"""
import os
import numpy as np
import pandas as pd
from typing import Optional, Dict, Tuple

from app_state import app_state
from loader import load_dynamics_events_layer_4d


# Event type definitions with colors. Each event stores a single representative
# 'position' (one of the nodes involved).
EVENT_TYPES = {
    'tip_edge_fusion': {
        'name': 'Tip-Edge Fusion',
        'color': '#FFC04D',
        'csv_file': 'tip_edge_fusion_events.csv',
    },
    'junction_breakage': {
        'name': 'Junction Breakage',
        'color': '#E67300',
        'csv_file': 'junction_breakage_events.csv',
    },
    'tip_tip_fusion': {
        'name': 'Tip-Tip Fusion',
        'color': '#B57EDC',
        'csv_file': 'tip_tip_fusion_events.csv',
    },
    'tip_tip_fission': {
        'name': 'Tip-Tip Fission',
        'color': '#6A2C91',
        'csv_file': 'tip_tip_fission_events.csv',
    },
    'extrusion': {
        'name': 'Extrusion',
        'color': '#4FD0C4',
        'csv_file': 'extrusion_events.csv',
    },
    'retraction': {
        'name': 'Retraction',
        'color': '#157A6E',
        'csv_file': 'retraction_events.csv',
    },
}


def _refresh_events_layer(viewer):
    """Rebuild the 4D Dynamic Events layer from the saved CSVs."""
    load_dynamics_events_layer_4d(viewer)


def find_selected_event(viewer) -> Optional[Tuple[str, int, np.ndarray, str]]:
    """Return (event_type_key, csv_row_index, position, csv_file) for the single
    selected Dynamic Events point, or None.
    """
    if 'Dynamic Events' not in viewer.layers:
        return None

    events_layer = viewer.layers['Dynamic Events']
    selected_indices = list(events_layer.selected_data)
    if len(selected_indices) != 1:
        return None

    selected_idx = selected_indices[0]
    event_type = events_layer.properties['event_type'][selected_idx]
    position = events_layer.data[selected_idx]
    csv_row_idx = events_layer.properties.get(
        'csv_row_index', [None] * len(events_layer.data)
    )[selected_idx]
    csv_file = events_layer.properties.get(
        'csv_file', [None] * len(events_layer.data)
    )[selected_idx]

    event_type_key = None
    for key, config in EVENT_TYPES.items():
        if config['name'] == event_type:
            event_type_key = key
            break
    if event_type_key is None:
        return None

    return (event_type_key, csv_row_idx, position, csv_file)


def delete_selected_event(viewer, widget) -> bool:
    """Delete the currently selected event from its CSV."""
    selection = find_selected_event(viewer)
    if selection is None:
        widget.log_status("No event selected. Select a single event point to delete.")
        return False

    event_type_key, csv_row_idx, position, csv_file = selection
    csv_path = os.path.join(app_state.loaded_folder, csv_file)
    if not os.path.exists(csv_path):
        widget.log_status(f"Event file not found: {csv_path}")
        return False

    df = pd.read_csv(csv_path)
    if csv_row_idx is None or csv_row_idx >= len(df):
        widget.log_status("Could not identify event in CSV file.")
        return False

    df = df.drop(df.index[csv_row_idx])
    df.to_csv(csv_path, index=False)
    widget.log_status(
        f"Deleted {EVENT_TYPES[event_type_key]['name']} event at position {position}"
    )
    _refresh_events_layer(viewer)
    return True


def _selected_skeleton_position(viewer):
    """Return [z, y, x] of the single selected Skeleton point, or None.

    The Skeleton layer stores [t, z, y, x] in 4D; the leading T is stripped so
    the returned position is always 3D [z, y, x].
    """
    if 'Skeleton' not in viewer.layers:
        return None
    skel = viewer.layers['Skeleton']
    selected = list(skel.selected_data)
    if len(selected) != 1:
        return None
    coord = np.asarray(skel.data[selected[0]], dtype=float)
    return coord[-3:]


def create_event_data(event_type_key: str, position: np.ndarray,
                      current_timepoint: int) -> Dict:
    """Build the CSV row dict for a new event.

    Stores position as [x, y, z] (loader reverses it back to [z, y, x]).
    """
    pos_storage = [float(position[2]), float(position[1]), float(position[0])]
    event_data = {
        'position': pos_storage,
        'timepoint_1': current_timepoint - 1 if current_timepoint > 1 else current_timepoint,
        'timepoint_2': current_timepoint,
    }
    if event_type_key in ['tip_edge_fusion', 'junction_breakage']:
        event_data['degree_t1'] = 1 if event_type_key == 'tip_edge_fusion' else 3
        event_data['degree_t2'] = 3 if event_type_key == 'tip_edge_fusion' else 1
    else:
        event_data['distance'] = 0.0
    return event_data


def add_event_at_skeleton_point(viewer, widget, event_type_key: str,
                                current_timepoint: int) -> bool:
    """Add a new event at the single selected Skeleton point."""
    if event_type_key not in EVENT_TYPES:
        widget.log_status(f"Invalid event type: {event_type_key}")
        return False

    position = _selected_skeleton_position(viewer)
    if position is None:
        widget.log_status(
            "Select exactly 1 point on the Skeleton layer, then press the event key."
        )
        return False

    event_data = create_event_data(event_type_key, position, current_timepoint)
    csv_path = os.path.join(app_state.loaded_folder, EVENT_TYPES[event_type_key]['csv_file'])
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        df = pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([event_data])], ignore_index=True)
    df.to_csv(csv_path, index=False)

    widget.log_status(
        f"Added {EVENT_TYPES[event_type_key]['name']} event at position {position} "
        f"(timepoint {current_timepoint})"
    )
    _refresh_events_layer(viewer)
    return True


def show_event_info(viewer, widget):
    """Log info about the currently selected event."""
    selection = find_selected_event(viewer)
    if selection is None:
        widget.log_status("No event selected.")
        return

    event_type_key, csv_row_idx, position, csv_file = selection
    csv_path = os.path.join(app_state.loaded_folder, EVENT_TYPES[event_type_key]['csv_file'])
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if csv_row_idx is not None and csv_row_idx < len(df):
            event_data = df.iloc[csv_row_idx]
            widget.log_status(
                f"Selected: {EVENT_TYPES[event_type_key]['name']} | "
                f"Timepoint: {event_data.get('timepoint_2', 'N/A')} | "
                f"Position: {position}"
            )
            return
    widget.log_status(f"Selected: {EVENT_TYPES[event_type_key]['name']} at {position}")
