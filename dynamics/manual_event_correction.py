#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual correction of dynamic events.

Provides interactive tools to:
- Delete false positive events
- Add missing events
- Change event classifications
- Save corrections to CSV files
"""

import pandas as pd
import numpy as np
import os
from typing import Optional, Dict, List, Tuple
from app_state import app_state
from utils.layer_loader import load_dynamics_events_layer
    

# Event type definitions with colors
EVENT_TYPES = {
    'tip_edge_fusion': {
        'name': 'Tip-Edge Fusion',
        'color': 'gold',
        'csv_file': 'tip_edge_fusion_events.csv',
        'position_fields': ['position_t1', 'position_t2']
    },
    'junction_breakage': {
        'name': 'Junction Breakage',
        'color': 'darkorange',
        'csv_file': 'junction_breakage_events.csv',
        'position_fields': ['position_t1', 'position_t2']
    },
    'tip_tip_fusion': {
        'name': 'Tip-Tip Fusion',
        'color': 'purple',
        'csv_file': 'tip_tip_fusion_events.csv',
        'position_fields': ['tip1_position', 'tip2_position']
    },
    'tip_tip_fission': {
        'name': 'Tip-Tip Fission',
        'color': 'turquoise',
        'csv_file': 'tip_tip_fission_events.csv',
        'position_fields': ['tip1_position', 'tip2_position']
    },
    'extrusion': {
        'name': 'Extrusion',
        'color': 'lime',
        'csv_file': 'extrusion_events.csv',
        'position_fields': ['tip_position', 'junction_position']
    },
    'retraction': {
        'name': 'Retraction',
        'color': 'olive',
        'csv_file': 'retraction_events.csv',
        'position_fields': ['tip_position', 'junction_position']
    }
}


class EventCorrectionState:
    """State management for event corrections."""

    def __init__(self):
        self.selected_event_index = None
        self.selected_event_type = None
        self.current_timepoint = None
        self.add_event_mode = None  # Which event type to add
        self.modifications = []  # Track all modifications for undo

    def reset(self):
        """Reset selection state."""
        self.selected_event_index = None
        self.selected_event_type = None
        self.add_event_mode = None


# Global state for event corrections
event_correction_state = EventCorrectionState()


def find_selected_event(viewer, current_timepoint: int) -> Optional[Tuple[str, int, np.ndarray, str]]:
    """
    Find which event is currently selected in the Dynamic Events layer.

    Args:
        viewer: Napari viewer instance
        current_timepoint: Current timepoint being viewed

    Returns:
        Tuple of (event_type, csv_row_index, position, csv_file) or None if no selection
    """
    if 'Dynamic Events' not in viewer.layers:
        return None

    events_layer = viewer.layers['Dynamic Events']
    selected_indices = list(events_layer.selected_data)

    if len(selected_indices) != 1:
        return None

    selected_idx = selected_indices[0]

    # Get event metadata
    event_type = events_layer.properties['event_type'][selected_idx]
    timepoint = events_layer.properties['timepoint'][selected_idx]
    position = events_layer.data[selected_idx]

    # Find corresponding CSV row index and file
    csv_row_idx = events_layer.properties.get('csv_row_index', [None] * len(events_layer.data))[selected_idx]
    csv_file = events_layer.properties.get('csv_file', [None] * len(events_layer.data))[selected_idx]

    # Map display name back to event type key
    event_type_key = None
    for key, config in EVENT_TYPES.items():
        if config['name'] == event_type:
            event_type_key = key
            break

    if event_type_key is None:
        return None

    return (event_type_key, csv_row_idx, position, csv_file)


def delete_selected_event(viewer, widget, current_timepoint: int) -> bool:
    """
    Delete the currently selected event.

    Args:
        viewer: Napari viewer instance
        widget: Widget for logging status
        current_timepoint: Current timepoint being viewed

    Returns:
        True if event was deleted, False otherwise
    """
    selection = find_selected_event(viewer, current_timepoint)

    if selection is None:
        widget.log_status("No event selected. Please select a single event point to delete.")
        return False

    event_type_key, csv_row_idx, position, csv_file = selection

    # Load the event CSV
    csv_path = os.path.join(app_state.loaded_folder, csv_file)

    if not os.path.exists(csv_path):
        widget.log_status(f"Event file not found: {csv_path}")
        return False

    # Read, delete row, and save
    df = pd.read_csv(csv_path)

    if csv_row_idx is None or csv_row_idx >= len(df):
        widget.log_status("Could not identify event in CSV file.")
        return False

    # Store modification for potential undo
    event_correction_state.modifications.append({
        'action': 'delete',
        'event_type': event_type_key,
        'row_index': csv_row_idx,
        'data': df.iloc[csv_row_idx].to_dict()
    })

    # Delete the row
    df = df.drop(df.index[csv_row_idx])
    df.to_csv(csv_path, index=False)

    widget.log_status(f"Deleted {EVENT_TYPES[event_type_key]['name']} event at position {position}")

    load_dynamics_events_layer(viewer, current_timepoint)

    return True



def add_event_at_cursor(viewer, widget, event_type_key: str, current_timepoint: int) -> bool:
    """
    Add a new event at the current cursor position.

    Args:
        viewer: Napari viewer instance
        widget: Widget for logging status
        event_type_key: Type of event to add (e.g., 'tip_edge_fusion')
        current_timepoint: Current timepoint being viewed

    Returns:
        True if event was added, False otherwise
    """
    if event_type_key not in EVENT_TYPES:
        widget.log_status(f"Invalid event type: {event_type_key}")
        return False

    # Get cursor position
    cursor_pos = viewer.cursor.position

    if cursor_pos is None or len(cursor_pos) < 3:
        widget.log_status("Could not get cursor position. Please move cursor over the image.")
        return False

    # Take only the 3D coordinates (z, y, x)
    position = np.array(cursor_pos[-3:])

    # Create event data
    event_data = create_event_data(event_type_key, position, current_timepoint)

    # Load or create CSV
    csv_path = os.path.join(app_state.loaded_folder, EVENT_TYPES[event_type_key]['csv_file'])

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        df = pd.DataFrame()

    # Add event
    df = pd.concat([df, pd.DataFrame([event_data])], ignore_index=True)
    df.to_csv(csv_path, index=False)

    # Store modification for potential undo
    event_correction_state.modifications.append({
        'action': 'add',
        'event_type': event_type_key,
        'data': event_data
    })

    widget.log_status(f"Added {EVENT_TYPES[event_type_key]['name']} event at position {position}")

    load_dynamics_events_layer(viewer, current_timepoint)

    return True


def create_event_data(event_type_key: str, position: np.ndarray, current_timepoint: int) -> Dict:
    """
    Create event data dictionary for a new event.

    Args:
        event_type_key: Type of event
        position: 3D position [z, y, x]
        current_timepoint: Current timepoint

    Returns:
        Event data dictionary
    """
    # Convert napari position [z, y, x] to storage format [x, y, z]
    pos_storage = [float(position[2]), float(position[1]), float(position[0])]

    event_data = {
        'timepoint_1': current_timepoint - 1 if current_timepoint > 1 else current_timepoint,
        'timepoint_2': current_timepoint
    }

    # Add position fields based on event type
    pos_fields = EVENT_TYPES[event_type_key]['position_fields']

    if event_type_key in ['tip_edge_fusion', 'junction_breakage']:
        event_data['position_t1'] = pos_storage
        event_data['position_t2'] = pos_storage
        event_data['degree_t1'] = 1 if event_type_key == 'tip_edge_fusion' else 3
        event_data['degree_t2'] = 3 if event_type_key == 'tip_edge_fusion' else 1

    elif event_type_key in ['tip_tip_fusion', 'tip_tip_fission']:
        # For tip-tip events, use same position for both tips (user should adjust manually)
        event_data['tip1_position'] = pos_storage
        event_data['tip2_position'] = pos_storage
        event_data['distance'] = 0.0

    elif event_type_key in ['extrusion', 'retraction']:
        # For extrusion/retraction, use same position for tip and junction (user should adjust)
        event_data['tip_position'] = pos_storage
        event_data['junction_position'] = pos_storage
        event_data['distance'] = 0.0

    return event_data



def show_event_info(viewer, widget, current_timepoint: int):
    """
    Display information about the currently selected event.

    Args:
        viewer: Napari viewer instance
        widget: Widget for logging status
        current_timepoint: Current timepoint being viewed
    """
    selection = find_selected_event(viewer, current_timepoint)

    if selection is None:
        widget.log_status("No event selected.")
        return

    event_type_key, csv_row_idx, position, csv_file = selection

    # Load event data
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
        else:
            widget.log_status(f"Selected: {EVENT_TYPES[event_type_key]['name']} at {position}")
    else:
        widget.log_status(f"Selected: {EVENT_TYPES[event_type_key]['name']} at {position}")


def get_event_type_menu() -> str:
    """
    Get formatted menu of event types for display.

    Returns:
        Formatted string with event types and numbers
    """
    menu = "Event Types:\n"
    for i, (key, config) in enumerate(EVENT_TYPES.items(), 1):
        menu += f"  {i}. {config['name']}\n"
    return menu
