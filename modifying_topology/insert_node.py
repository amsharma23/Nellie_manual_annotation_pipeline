import pandas as pd
import numpy as np
from app_state import app_state
from scipy.spatial.distance import cdist


def find_nearest_skeleton_point(cursor_pos, skeleton_layer):
    """Find the nearest skeleton point to the cursor position.

    Args:
        cursor_pos: Cursor position [z, y, x]
        skeleton_layer: Napari shapes layer containing skeleton

    Returns:
        numpy.ndarray: Nearest skeleton point [z, y, x]
    """
    # Get skeleton points from the skeleton layer if it exists
    # The skeleton layer is a shapes layer, so we need to get points from elsewhere
    # We'll look for skeleton coordinates in the raw skeleton image

    # For now, we'll look for a points layer that contains skeleton coordinates
    # or we can store skeleton coordinates in app_state

    # If we have skeleton coordinates available, use them
    # Otherwise, just use the cursor position

    # Try to get skeleton data from stored skeleton coordinates
    # This would need to be set when the skeleton is loaded
    if hasattr(app_state, 'skeleton_coords') and app_state.skeleton_coords is not None:
        skeleton_coords = app_state.skeleton_coords
        # Calculate distances to all skeleton points
        distances = cdist([cursor_pos], skeleton_coords, metric='euclidean')
        nearest_idx = np.argmin(distances)
        return skeleton_coords[nearest_idx]
    else:
        # Fallback: just use cursor position rounded to integers
        return np.round(cursor_pos).astype(float)


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
