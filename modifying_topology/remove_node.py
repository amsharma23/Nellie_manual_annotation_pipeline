import pandas as pd
import numpy as np
from app_state import app_state
from utils.layer_loader import load_image_and_skeleton
from utils.parsing import get_float_pos_comma


def remove_node(viewer, widget):
    """Remove a selected node and update all related CSVs.

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

    # Get selected node
    selected_indices = list(extracted_layer.selected_data)
    if len(selected_indices) == 0:
        widget.log_status("No node selected. Please select a node to remove.")
        return
    elif len(selected_indices) > 1:
        widget.log_status("Multiple nodes selected. Please select only one node to remove.")
        return

    # Get position of selected node
    selected_index = selected_indices[0]
    selected_pos = extracted_layer.data[selected_index]

    # Find node in dataframe by matching position
    node_positions = nd_pdf['Position(ZXY)'].tolist()
    node_positions_parsed = [get_float_pos_comma(str(pos)) for pos in node_positions]

    node_df_index = None
    node_id = None
    for idx, pos in enumerate(node_positions_parsed):
        if np.array_equal(pos, selected_pos):
            node_df_index = nd_pdf.index[idx]
            node_id = nd_pdf.loc[node_df_index, 'Node ID']
            break

    if node_df_index is None or node_id is None:
        widget.log_status("Could not find selected node in dataframe.")
        return

    # Get neighbors of the node to be removed
    neighbor_ids_str = nd_pdf.loc[node_df_index, 'Neighbour ID']
    if pd.isna(neighbor_ids_str) or neighbor_ids_str == '[]':
        neighbor_ids = []
    else:
        neighbor_ids = get_float_pos_comma(str(neighbor_ids_str))

    # Update all neighbors to remove this node from their adjacency lists
    for neighbor_id in neighbor_ids:
        # Find the neighbor in the dataframe
        neighbor_rows = nd_pdf[nd_pdf['Node ID'] == neighbor_id]
        if len(neighbor_rows) == 0:
            continue

        neighbor_df_index = neighbor_rows.index[0]

        # Get neighbor's adjacency list
        neighbor_adj_str = nd_pdf.loc[neighbor_df_index, 'Neighbour ID']
        if pd.isna(neighbor_adj_str) or neighbor_adj_str == '[]':
            neighbor_adj_list = []
        else:
            neighbor_adj_list = get_float_pos_comma(str(neighbor_adj_str))

        # Remove the deleted node from neighbor's list
        if node_id in neighbor_adj_list:
            neighbor_adj_list.remove(node_id)

        # Update neighbor's adjacency list and degree
        nd_pdf.loc[neighbor_df_index, 'Neighbour ID'] = str(neighbor_adj_list)
        nd_pdf.loc[neighbor_df_index, 'Degree of Node'] = len(neighbor_adj_list)

    # Remove the node from dataframe
    nd_pdf.drop(node_df_index, inplace=True)

    # Update app state
    app_state.node_dataframe = nd_pdf

    # Save to CSV
    nd_pdf.to_csv(node_path, index=False)

    # Reload visualization to show updated network properly
    viewer.layers.clear()

    raw_im, skel_im, face_colors, positions, colors, edge_lines = load_image_and_skeleton(
        app_state.nellie_output_path
    )

    if raw_im is not None and skel_im is not None:
        # Add raw image layer
        app_state.raw_layer = viewer.add_image(
            raw_im,
            scale=app_state.visualization_scale,
            name='Raw Image'
        )

        # Add skeleton as points layer
        app_state.skeleton_layer = viewer.add_points(
            skel_im,
            size=3,
            face_color=face_colors,
            scale=app_state.visualization_scale,
            name='Skeleton'
        )

        # Add extracted nodes if available
        if positions and colors:
            app_state.points_layer = viewer.add_points(
                positions,
                size=5,
                face_color=colors,
                scale=app_state.visualization_scale,
                name='Extracted Nodes'
            )

    widget.log_status(f"Removed node (ID: {node_id}) at position {selected_pos}")
