import pandas as pd
import numpy as np
from app_state import app_state


# Preview state tracking
preview_state = {
    'enabled': False,
    'layer': None,
    'last_position': None,
    'mouse_callback': None
}

# Z-plane lock state tracking
z_lock_state = {
    'locked': False,
    'z_value': None
}


def find_nearest_skeleton_point(cursor_pos, skeleton_layer):
    """Return the cursor position, with optional Z-plane locking.

    Args:
        cursor_pos: Cursor position [z, y, x]
        skeleton_layer: Napari shapes layer containing skeleton (unused)

    Returns:
        numpy.ndarray: Cursor position [z, y, x] with locked Z if enabled
    """
    # Round cursor position to reasonable precision
    position = np.round(cursor_pos, decimals=2).astype(float)

    # If Z is locked, replace Z coordinate with locked value
    if z_lock_state['locked'] and z_lock_state['z_value'] is not None:
        position[0] = z_lock_state['z_value']

    return position


def update_preview_position(viewer, event):
    """Update the preview point position based on cursor location.

    Args:
        viewer: Napari viewer instance
        event: Mouse move event
    """
    if not preview_state['enabled']:
        return

    # Get cursor position
    cursor_pos = viewer.cursor.position

    if cursor_pos is None or len(cursor_pos) < 3:
        return

    # Take only the 3D coordinates (z, y, x)
    cursor_pos = np.array(cursor_pos[-3:])

    # Snap to nearest skeleton point
    snapped_pos = find_nearest_skeleton_point(cursor_pos, None)

    # Update preview layer if it exists
    if preview_state['layer'] is not None and preview_state['layer'] in viewer.layers:
        preview_state['layer'].data = np.array([snapped_pos])
        preview_state['last_position'] = snapped_pos


def toggle_preview_mode(viewer, widget):
    """Toggle preview mode on/off.

    Args:
        viewer: Napari viewer instance
        widget: Widget for logging status
    """
    if not preview_state['enabled']:
        # Enable preview mode
        preview_state['enabled'] = True

        # Create preview layer if it doesn't exist
        if 'Insert Preview' not in viewer.layers:
            # Start with cursor position or center
            cursor_pos = viewer.cursor.position
            if cursor_pos is not None and len(cursor_pos) >= 3:
                initial_pos = np.array(cursor_pos[-3:])
                snapped_pos = find_nearest_skeleton_point(initial_pos, None)
            else:
                # Use a dummy position if no cursor position
                snapped_pos = np.array([0, 0, 0])

            preview_state['layer'] = viewer.add_points(
                [snapped_pos],
                size=10,
                face_color='yellow',
                scale=[1.765, 1, 1],
                name='Insert Preview'
            )
            # Set edge properties after layer creation
            preview_state['layer'].edge_color = 'orange'
            preview_state['layer'].edge_width = 0.5
            preview_state['last_position'] = snapped_pos
        else:
            preview_state['layer'] = viewer.layers['Insert Preview']
            preview_state['layer'].visible = True

        # Add mouse move callback
        preview_state['mouse_callback'] = viewer.mouse_move_callbacks.append(
            lambda viewer, event: update_preview_position(viewer, event)
        )

        widget.log_status("Preview mode ON - Move cursor to see insertion point (press 'v' to toggle off)")
    else:
        # Disable preview mode
        preview_state['enabled'] = False

        # Hide preview layer
        if preview_state['layer'] is not None and preview_state['layer'] in viewer.layers:
            preview_state['layer'].visible = False

        # Remove mouse move callback
        if preview_state['mouse_callback'] is not None:
            try:
                viewer.mouse_move_callbacks.remove(preview_state['mouse_callback'])
            except (ValueError, AttributeError):
                pass
            preview_state['mouse_callback'] = None

        widget.log_status("Preview mode OFF")


def toggle_z_lock(viewer, widget):
    """Toggle Z-plane locking on/off.

    Args:
        viewer: Napari viewer instance
        widget: Widget for logging status
    """
    if not z_lock_state['locked']:
        # Enable Z-lock
        z_lock_state['locked'] = True

        # Capture current Z position
        cursor_pos = viewer.cursor.position
        if cursor_pos is not None and len(cursor_pos) >= 3:
            z_value = np.round(cursor_pos[-3], decimals=2)
            z_lock_state['z_value'] = z_value
            widget.log_status(f"Z-plane LOCKED at Z={z_value:.2f}")
        else:
            # Fallback if no cursor position
            z_lock_state['z_value'] = 0.0
            widget.log_status("Z-plane LOCKED at Z=0.00")
    else:
        # Disable Z-lock
        z_lock_state['locked'] = False
        z_lock_state['z_value'] = None
        widget.log_status("Z-plane UNLOCKED")


def insert_node_at_cursor(viewer, widget):
    """Insert a new isolated node at the cursor position.

    Args:
        viewer: Napari viewer instance
        widget: Widget for logging status
    """
    # Get node dataframe and path
    nd_pdf = app_state.node_dataframe
    node_path = app_state.node_path

    if nd_pdf is None or node_path is None:
        widget.log_status("No node data loaded. Please view results first.")
        return

    # Get Extracted Nodes layer
    if 'Extracted Nodes' not in viewer.layers:
        widget.log_status("Extracted Nodes layer not found.")
        return
    extracted_layer = viewer.layers['Extracted Nodes']

    # Get skeleton layer for snapping
    skeleton_layer = None
    if 'Skeleton' in viewer.layers:
        skeleton_layer = viewer.layers['Skeleton']

    # Use preview position if available, otherwise use cursor position
    if preview_state['enabled'] and preview_state['last_position'] is not None:
        snapped_pos = preview_state['last_position']
    else:
        # Get cursor position
        cursor_pos = viewer.cursor.position

        if cursor_pos is None or len(cursor_pos) < 3:
            widget.log_status("Could not get cursor position. Please move cursor over the image.")
            return

        # Take only the 3D coordinates (z, y, x)
        cursor_pos = np.array(cursor_pos[-3:])

        # Snap to nearest skeleton point
        snapped_pos = find_nearest_skeleton_point(cursor_pos, skeleton_layer)

    # Get next node ID
    if nd_pdf.empty or 'Node ID' not in nd_pdf.columns:
        max_node_id = 0
    else:
        node_ids = nd_pdf['Node ID'].dropna().astype(int)
        max_node_id = node_ids.max() if len(node_ids) > 0 else 0

    # Get next index location
    insert_loc = nd_pdf.index.max()
    if pd.isna(insert_loc):
        insert_loc = 0
    else:
        insert_loc = insert_loc + 1

    # Create new node entry
    new_node_id = max_node_id + 1
    nd_pdf.loc[insert_loc, 'Node ID'] = new_node_id
    nd_pdf.loc[insert_loc, 'Degree of Node'] = 0  # Isolated node
    nd_pdf.loc[insert_loc, 'Position(ZXY)'] = str(list(snapped_pos))
    nd_pdf.loc[insert_loc, 'Neighbour ID'] = '[]'  # No neighbors initially

    # Update app state
    app_state.node_dataframe = nd_pdf

    # Save to CSV
    nd_pdf.to_csv(node_path, index=False)

    # Update Extracted Nodes layer
    current_data = extracted_layer.data
    if len(current_data) > 0:
        new_data = np.vstack([current_data, snapped_pos])
    else:
        new_data = np.array([snapped_pos])

    extracted_layer.data = new_data

    # Update colors (degree 0 = white)
    current_colors = list(extracted_layer.face_color)
    current_colors.append('white')
    extracted_layer.face_color = current_colors

    widget.log_status(f"Inserted new node (ID: {new_node_id}) at position {snapped_pos}")
