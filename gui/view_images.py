from app_state import app_state
from utils.layer_loader import (
    load_image_and_skeleton,
    load_timeseries_4d,
    load_4d_stack,
    load_dynamics_events_layer,
    load_dynamics_events_layer_4d,
)
import os
import numpy as np
from natsort import natsorted
from modifying_topology.edit_node import highlight
from modifying_topology.add_edge import join
from modifying_topology.remove_edge import remove
from modifying_topology.insert_node import insert_node_at_cursor, toggle_preview_mode, toggle_z_lock
from modifying_topology.remove_node import remove_node
from gui.update_display_mod import setup_key_bindings
from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox,
QLabel, QPushButton, QSpinBox, QTextEdit,
QVBoxLayout, QHBoxLayout, QWidget, QFileDialog)



def view_clicked(widget,viewer,next_btn,prev_btn,image_slider,image_label,network_btn):        
        current = image_slider.value()
        
        if current == widget.image_slider.maximum():
            widget.next_btn.setEnabled(False)
        elif current == 0:
            widget.prev_btn.setEnabled(False)
            
        
       
        try:
            if app_state.folder_type == 'Single TIFF':
                if not app_state.nellie_output_path or not os.path.exists(app_state.nellie_output_path):
                    widget.log_status("No results to view. Please run processing first.")
                    return
                # Clear existing layers
                viewer.layers.clear()
                
                # Load images
                raw_im, skel_im, face_colors, positions, colors, edge_lines = load_image_and_skeleton(app_state.nellie_output_path)

                if raw_im is not None and skel_im is not None:
                    network_btn.setEnabled(True)
                    # Add layers to viewer
                    app_state.raw_layer = widget.viewer.add_image(
                        raw_im,
                        scale=app_state.visualization_scale,  # Z, Y, X scaling
                        name='Raw Image'
                    )

                    # Add skeleton as points layer
                    app_state.skeleton_layer = widget.viewer.add_points(
                        skel_im,
                        size=3,
                        face_color=face_colors,
                        scale=app_state.visualization_scale,
                        name='Skeleton'
                    )
                    
                    # Add extracted points if available
                    if positions and colors:

                        app_state.points_layer = widget.viewer.add_points(
                            positions,
                            size=5,
                            face_color=colors,
                            scale=app_state.visualization_scale,
                            name='Extracted Nodes'
                        )
                    
                    @viewer.bind_key('e')
                    def see_connections(viewer):
                        if (len(list(viewer.layers[1].selected_data))==0):
                            widget.log_status("No node selected to edit.")
                            return
                        highlight(viewer)
                    @viewer.bind_key('u')
                    def unseen(viewer):
                        if (len(list(viewer.layers[1].selected_data))==0):
                            widget.log_status("No node selected to edit.")
                            return
                        viewer.layers.remove('Connected Nodes')
                        app_state.editable_node_positions = []
                        app_state.selected_node_position = []

                    @viewer.bind_key('j')
                    def join_points(viewer):
                        if (len(list(viewer.layers[1].selected_data))!=2):
                            widget.log_status("Need to select exactly 2 nodes to join on the skeleton layer.")
                            return
                        join(viewer)

                        # Clear existing layers
                        widget.viewer.layers.clear()
                
                        raw_im, skel_im, face_colors, positions, colors, edge_lines = load_image_and_skeleton(app_state.nellie_output_path)

                        if raw_im is not None and skel_im is not None:

                            # Add layers to viewer
                            app_state.raw_layer = widget.viewer.add_image(
                                raw_im,
                                scale=app_state.visualization_scale,  # Z, Y, X scaling
                                name='Raw Image'
                            )

                            # Add skeleton as points layer
                            app_state.skeleton_layer = widget.viewer.add_points(
                                skel_im,
                                size=3,
                                face_color=face_colors,
                                scale=app_state.visualization_scale,
                                name='Skeleton'
                            )
                            
                            # Add extracted points if available
                            if positions and colors:
                                app_state.points_layer = widget.viewer.add_points(
                                    positions,
                                    size=5,
                                    face_color=colors,
                                    scale=app_state.visualization_scale,
                                    name='Extracted Nodes'
                                )
                            widget.log_status("Joined Nodes sucessfully")

                    @viewer.bind_key('r')
                    def remove_edge(viewer):
                        flag = remove(viewer)
                        if (len(list(viewer.layers[1].selected_data))!=2):
                            widget.log_status("Need to select exactly 2 nodes to remove on the skeleton layer.")
                            return
                        elif flag:
                            widget.log_status("Need to select exactly 2 nodes that are BOTH NOT RED to remove on the skeleton layer.")
                            return

                        # Clear existing layers
                        widget.viewer.layers.clear()
                
                        raw_im, skel_im, face_colors, positions, colors, edge_lines = load_image_and_skeleton(app_state.nellie_output_path)
                
                        if raw_im is not None and skel_im is not None:
                            network_btn.setEnabled(True)
                            # Add layers to viewer
                            app_state.raw_layer = widget.viewer.add_image(
                                raw_im, 
                                scale=app_state.visualization_scale,  # Z, Y, X scaling
                                name='Raw Image'
                            )
                            
                            # Add skeleton as points layer
                            app_state.skeleton_layer = widget.viewer.add_points(
                                skel_im,
                                size=3,
                                face_color=face_colors,
                                scale=app_state.visualization_scale,
                                name='Skeleton'
                            )
                            
                            # Add extracted points if available
                            if positions and colors:
                                app_state.points_layer = widget.viewer.add_points(
                                    positions,
                                    size=5,
                                    face_color=colors,
                                    scale=app_state.visualization_scale,
                                    name='Extracted Nodes'
                                )
                            widget.log_status("Broke Nodes sucessfully")
                            return

                    @viewer.bind_key('i')
                    def insert_node(viewer):
                        insert_node_at_cursor(viewer, widget)

                    @viewer.bind_key('v')
                    def toggle_preview(viewer):
                        toggle_preview_mode(viewer, widget)

                    @viewer.bind_key('l')
                    def toggle_z_plane_lock(viewer):
                        toggle_z_lock(viewer, widget)

                    @viewer.bind_key('x')
                    def remove_node_key(viewer):
                        remove_node(viewer, widget)

                    widget.log_status("Visualization loaded successfully")
                    
                
            elif app_state.folder_type == 'Time Series':
                _view_timeseries_4d(widget, viewer, next_btn, prev_btn,
                                    image_slider, image_label, network_btn)

            elif app_state.folder_type == '4D Stack':
                _view_4d_stack(widget, viewer, next_btn, prev_btn,
                               image_slider, image_label, network_btn)

        except Exception as e:
            widget.log_status(f"Error viewing results: {str(e)}")


def _view_timeseries_4d(widget, viewer, next_btn, prev_btn,
                        image_slider, image_label, network_btn):
    """Load a Time Series folder as a single 4D napari stack and wire navigation."""
    ts = load_timeseries_4d(app_state.loaded_folder)
    if ts is None:
        widget.log_status("Failed to load time series as 4D stack.")
        return

    num_t = ts['raw_4d'].shape[0]
    widget.log_status(
        f"Loaded {num_t} timepoints as 4D stack {ts['raw_4d'].shape}."
    )

    # Persist 4D state
    app_state.is_timeseries_4d = True
    app_state.timepoint_paths = ts['timepoint_paths']
    app_state.ts_per_frame = ts['per_frame']
    app_state.skeleton_coords_per_frame = ts['skel_per_frame']
    app_state.image_sets_keys = [d['basename'] for d in ts['per_frame']]
    app_state.image_sets = {
        d['basename']: d['nellie_output_path'] for d in ts['per_frame']
    }
    # Track the first frame as "current"
    app_state.current_image_index = 0
    app_state.nellie_output_path = ts['timepoint_paths'][0]
    app_state.skeleton_coords = ts['skel_per_frame'][0]
    app_state.node_dataframe = ts['per_frame'][0].get('node_df')

    # Clear and rebuild layers
    viewer.layers.clear()

    scale_4d = [1] + list(app_state.visualization_scale)

    # 1) Raw 4D image
    app_state.raw_layer = viewer.add_image(
        ts['raw_4d'],
        scale=scale_4d,
        name='Raw Image',
    )

    # 2) Skeleton voxels (T, Z, Y, X)
    if len(ts['skel_points']) > 0:
        app_state.skeleton_layer = viewer.add_points(
            ts['skel_points'],
            size=3,
            face_color=ts['face_colors'],
            scale=scale_4d,
            name='Skeleton',
        )

    # 3) Extracted nodes (T, Z, Y, X)
    if len(ts['node_points']) > 0:
        app_state.points_layer = viewer.add_points(
            ts['node_points'],
            size=5,
            face_color=ts['node_colors'],
            scale=scale_4d,
            name='Extracted Nodes',
        )

    # Dynamic events as a single 4D layer (no-op if no events present)
    load_dynamics_events_layer_4d(viewer)

    # Configure the side-panel slider to mirror napari's T axis
    image_slider.blockSignals(True)
    image_slider.setMinimum(1)
    image_slider.setMaximum(max(1, num_t))
    image_slider.setValue(1)
    image_slider.blockSignals(False)
    image_label.setText(f"Current Image: 1/{max(1, num_t)}")
    prev_btn.setEnabled(num_t > 1)
    next_btn.setEnabled(num_t > 1)

    # Set napari's T axis to 0
    try:
        viewer.dims.set_current_step(0, 0)
    except Exception:
        pass

    # Wire the napari T-axis listener to keep widget.image_slider + app_state in sync.
    # The listener is idempotent on repeated viewings because we always disconnect first.
    if hasattr(widget, '_ts_dims_listener'):
        try:
            viewer.dims.events.current_step.disconnect(widget._ts_dims_listener)
        except Exception:
            pass

    def _on_dims_changed(event):
        if not app_state.is_timeseries_4d:
            return
        try:
            t_idx = int(viewer.dims.current_step[0])
        except Exception:
            return
        if t_idx == app_state.current_image_index:
            return
        widget.set_current_timepoint(t_idx, source='napari')

    widget._ts_dims_listener = _on_dims_changed
    viewer.dims.events.current_step.connect(_on_dims_changed)

    # Bind the manual-annotation keys once (same set used by single-TIFF refresh path)
    if not getattr(widget, '_key_bindings_setup', False):
        setup_key_bindings(widget, viewer)
        widget._key_bindings_setup = True

    network_btn.setEnabled(True)
    widget.log_status(
        "Visualization loaded. Use the bottom T-slider, arrow keys, or the "
        "Prev/Next buttons to navigate frames."
    )


def _view_4d_stack(widget, viewer, next_btn, prev_btn,
                   image_slider, image_label, network_btn):
    """Load a single 4D Nellie output folder as one napari stack and wire nav."""
    out_path = app_state.single_output_path
    if not out_path:
        # Derive from the selected file if processing set nothing.
        if app_state.loaded_file:
            out_path = os.path.join(
                os.path.dirname(app_state.loaded_file),
                'nellie_output', 'nellie_necessities',
            )
            app_state.single_output_path = out_path

    ts = load_4d_stack(out_path)
    if ts is None:
        widget.log_status("Failed to load 4D stack.")
        return

    num_t = ts['num_t']
    widget.log_status(
        f"Loaded 4D stack {ts['raw_4d'].shape} ({num_t} timepoints) from one output folder."
    )

    # Persist 4D state (both flags so existing 4D code paths engage)
    app_state.is_timeseries_4d = True
    app_state.is_4d_stack = True
    app_state.single_output_path = ts['single_output_path']
    app_state.pixel_class_basename = ts['pixel_class_basename']
    app_state.frame_csv_paths = ts['frame_csv_paths']
    app_state.ts_per_frame = ts['per_frame']
    app_state.skeleton_coords_per_frame = ts['skel_per_frame']
    # timepoint_paths is the same single folder for every frame (kept length-T
    # so any code indexing it by t stays in-bounds).
    app_state.timepoint_paths = [ts['single_output_path']] * num_t
    app_state.image_sets_keys = [f"t{t:04d}" for t in range(num_t)]
    app_state.image_sets = {f"t{t:04d}": ts['single_output_path'] for t in range(num_t)}

    # Track the first frame as "current"
    app_state.current_image_index = 0
    app_state.nellie_output_path = ts['single_output_path']
    app_state.skeleton_coords = ts['skel_per_frame'][0] if ts['skel_per_frame'] else None
    app_state.node_dataframe = ts['per_frame'][0].get('node_df') if ts['per_frame'] else None
    app_state.node_path = ts['frame_csv_paths'][0] if ts['frame_csv_paths'] else None

    # Clear and rebuild layers
    viewer.layers.clear()

    scale_4d = [1] + list(app_state.visualization_scale)

    # 1) Raw 4D image
    app_state.raw_layer = viewer.add_image(
        ts['raw_4d'],
        scale=scale_4d,
        name='Raw Image',
    )

    # 2) Skeleton voxels (T, Z, Y, X)
    if len(ts['skel_points']) > 0:
        app_state.skeleton_layer = viewer.add_points(
            ts['skel_points'],
            size=3,
            face_color=ts['face_colors'],
            scale=scale_4d,
            name='Skeleton',
        )

    # 3) Extracted nodes (T, Z, Y, X)
    if len(ts['node_points']) > 0:
        app_state.points_layer = viewer.add_points(
            ts['node_points'],
            size=5,
            face_color=ts['node_colors'],
            scale=scale_4d,
            name='Extracted Nodes',
        )

    # Dynamic events as a single 4D layer (no-op if no events present)
    load_dynamics_events_layer_4d(viewer)

    # Configure the side-panel slider to mirror napari's T axis
    image_slider.blockSignals(True)
    image_slider.setMinimum(1)
    image_slider.setMaximum(max(1, num_t))
    image_slider.setValue(1)
    image_slider.blockSignals(False)
    image_label.setText(f"Current Image: 1/{max(1, num_t)}")
    prev_btn.setEnabled(num_t > 1)
    next_btn.setEnabled(num_t > 1)

    # Set napari's T axis to 0
    try:
        viewer.dims.set_current_step(0, 0)
    except Exception:
        pass

    # Wire the napari T-axis listener to keep widget.image_slider + app_state in sync.
    if hasattr(widget, '_ts_dims_listener'):
        try:
            viewer.dims.events.current_step.disconnect(widget._ts_dims_listener)
        except Exception:
            pass

    def _on_dims_changed(event):
        if not app_state.is_timeseries_4d:
            return
        try:
            t_idx = int(viewer.dims.current_step[0])
        except Exception:
            return
        if t_idx == app_state.current_image_index:
            return
        widget.set_current_timepoint(t_idx, source='napari')

    widget._ts_dims_listener = _on_dims_changed
    viewer.dims.events.current_step.connect(_on_dims_changed)

    # Bind the manual-annotation keys once
    if not getattr(widget, '_key_bindings_setup', False):
        setup_key_bindings(widget, viewer)
        widget._key_bindings_setup = True

    network_btn.setEnabled(True)
    widget.log_status(
        "4D stack loaded. Use the bottom T-slider, arrow keys, or the "
        "Prev/Next buttons to navigate frames."
    )