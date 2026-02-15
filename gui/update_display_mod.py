from app_state import app_state
from utils.layer_loader import load_image_and_skeleton, load_dynamics_events_layer
from natsort import natsorted
import os
from modifying_topology.edit_node import highlight
from modifying_topology.add_edge import join
from tifffile import imread
from modifying_topology.remove_edge import remove
from modifying_topology.insert_node import insert_node_at_cursor, toggle_preview_mode, toggle_z_lock
from modifying_topology.remove_node import remove_node
import numpy as np

from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, 
QLabel, QPushButton, QSpinBox, QTextEdit, 
QVBoxLayout, QHBoxLayout, QWidget, QFileDialog)


class ViewerState:
    """Class to store and restore viewer state"""
    def __init__(self):
        self.camera_center = None
        self.camera_zoom = None
        self.camera_angles = None
        self.contrast_limits = {}
        self.layer_visibility = {}
        
    def capture_state(self, viewer):
        """Capture current viewer state"""
        self.camera_center = viewer.camera.center
        self.camera_zoom = viewer.camera.zoom
        self.camera_angles = viewer.camera.angles
        
        # Capture contrast limits and visibility for each layer
        for layer in viewer.layers:
            if hasattr(layer, 'contrast_limits'):
                self.contrast_limits[layer.name] = layer.contrast_limits
            self.layer_visibility[layer.name] = layer.visible
            
    def restore_state(self, viewer):
        """Restore viewer state"""
        if self.camera_center is not None:
            viewer.camera.center = self.camera_center
        if self.camera_zoom is not None:
            viewer.camera.zoom = self.camera_zoom
        if self.camera_angles is not None:
            viewer.camera.angles = self.camera_angles
            
        # Restore contrast limits and visibility
        for layer in viewer.layers:
            if layer.name in self.contrast_limits and hasattr(layer, 'contrast_limits'):
                layer.contrast_limits = self.contrast_limits[layer.name]
            if layer.name in self.layer_visibility:
                layer.visible = self.layer_visibility[layer.name]


# Global viewer state instance
viewer_state = ViewerState()


def reload_visualization_with_state_preservation(widget):
    """Reload the visualization after modifications while preserving viewer state"""
    # Capture current state before clearing
    viewer_state.capture_state(widget.viewer)
    
    # Reload the visualization
    reload_visualization(widget)
    
    # Restore the captured state
    viewer_state.restore_state(widget.viewer)


def reload_visualization(widget):
    """Reload the visualization after modifications"""
    widget.viewer.layers.clear()
    raw_im, skel_im, face_colors, positions, colors, edge_lines = load_image_and_skeleton(
        app_state.nellie_output_path
    )

    if raw_im is not None and skel_im is not None:
        add_image_layers(widget, raw_im, skel_im, face_colors, positions, colors, edge_lines)


def add_image_layers(widget, raw_im, skel_im, face_colors, positions, colors, edge_lines):
    """Helper method to add layers to viewer"""
    # Add raw image layer
    app_state.raw_layer = widget.viewer.add_image(
        raw_im,
        scale=app_state.visualization_scale,
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

    # Add extracted nodes if available
    if positions and colors:
        app_state.points_layer = widget.viewer.add_points(
            positions,
            size=5,
            face_color=colors,
            scale=app_state.visualization_scale,
            name='Extracted Nodes'
        )

    # Add dynamics events layer if available
    if hasattr(widget, 'image_slider'):
        current_timepoint = widget.image_slider.value()
        load_dynamics_events_layer(widget.viewer, current_timepoint)


def setup_key_bindings(widget, viewer):
    """Setup key bindings for the viewer"""

    @viewer.bind_key('e')
    def edit(viewer):
        # Get Extracted Nodes layer by name
        if 'Extracted Nodes' not in viewer.layers:
            widget.log_status("Extracted Nodes layer not found.")
            return
        extracted_layer = viewer.layers['Extracted Nodes']

        if len(list(extracted_layer.selected_data)) == 0:
            widget.log_status("No node selected to edit.")
            return
        highlight(viewer, widget)

    @viewer.bind_key('u')
    def unseen(viewer):
        # Get Extracted Nodes layer by name
        if 'Extracted Nodes' not in viewer.layers:
            widget.log_status("Extracted Nodes layer not found.")
            return
        extracted_layer = viewer.layers['Extracted Nodes']

        if len(list(extracted_layer.selected_data)) == 0:
            widget.log_status("No node selected to edit.")
            return
        if 'Connected Nodes' in [layer.name for layer in viewer.layers]:
            viewer.layers.remove('Connected Nodes')
        app_state.editable_node_positions = []
        app_state.selected_node_position = []

    @viewer.bind_key('j')
    def join_points(viewer):
        # Get Extracted Nodes layer by name
        if 'Extracted Nodes' not in viewer.layers:
            widget.log_status("Extracted Nodes layer not found.")
            return
        extracted_layer = viewer.layers['Extracted Nodes']

        if len(list(extracted_layer.selected_data)) != 2:
            widget.log_status("Need to select exactly 2 nodes to join.")
            return

        try:
            join(viewer)
            reload_visualization_with_state_preservation(widget)
            widget.log_status("Joined Nodes successfully")
        except Exception as e:
            widget.log_status(f"Error joining nodes: {str(e)}")

    @viewer.bind_key('r')
    def remove_edge(viewer):
        # Get Extracted Nodes layer by name
        if 'Extracted Nodes' not in viewer.layers:
            widget.log_status("Extracted Nodes layer not found.")
            return
        extracted_layer = viewer.layers['Extracted Nodes']

        if len(list(extracted_layer.selected_data)) != 2:
            widget.log_status("Need to select exactly 2 nodes to remove.")
            return

        try:
            flag = remove(viewer)
            if flag:
                widget.log_status("Need to select exactly 2 connected extracted nodes to remove.")
                return

            reload_visualization_with_state_preservation(widget)
            widget.log_status("Broke Nodes successfully")
        except Exception as e:
            widget.log_status(f"Error removing edge: {str(e)}")

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

    # ========== Dynamic Event Correction Keybindings ==========
    from dynamics.manual_event_correction import (
        delete_selected_event, show_event_info,
        add_event_at_cursor, EVENT_TYPES
    )

    @viewer.bind_key('d')
    def delete_event(viewer):
        """Delete selected dynamic event (key: 'd')"""
        if hasattr(widget, 'image_slider'):
            current_tp = widget.image_slider.value()
            delete_selected_event(viewer, widget, current_tp)

    @viewer.bind_key('Control-i')
    def event_info(viewer):
        """Show info about selected event (key: 'Ctrl+i')"""
        if hasattr(widget, 'image_slider'):
            current_tp = widget.image_slider.value()
            show_event_info(viewer, widget, current_tp)

    # Keybindings for adding specific event types (1-6)
    @viewer.bind_key('1')
    def add_tip_edge_fusion(viewer):
        """Add tip-edge fusion event at cursor (key: '1')"""
        if hasattr(widget, 'image_slider'):
            current_tp = widget.image_slider.value()
            add_event_at_cursor(viewer, widget, 'tip_edge_fusion', current_tp)

    @viewer.bind_key('2')
    def add_junction_breakage(viewer):
        """Add junction breakage event at cursor (key: '2')"""
        if hasattr(widget, 'image_slider'):
            current_tp = widget.image_slider.value()
            add_event_at_cursor(viewer, widget, 'junction_breakage', current_tp)

    @viewer.bind_key('3')
    def add_tip_tip_fusion(viewer):
        """Add tip-tip fusion event at cursor (key: '3')"""
        if hasattr(widget, 'image_slider'):
            current_tp = widget.image_slider.value()
            add_event_at_cursor(viewer, widget, 'tip_tip_fusion', current_tp)

    @viewer.bind_key('4')
    def add_tip_tip_fission(viewer):
        """Add tip-tip fission event at cursor (key: '4')"""
        if hasattr(widget, 'image_slider'):
            current_tp = widget.image_slider.value()
            add_event_at_cursor(viewer, widget, 'tip_tip_fission', current_tp)

    @viewer.bind_key('5')
    def add_extrusion(viewer):
        """Add extrusion event at cursor (key: '5')"""
        if hasattr(widget, 'image_slider'):
            current_tp = widget.image_slider.value()
            add_event_at_cursor(viewer, widget, 'extrusion', current_tp)

    @viewer.bind_key('6')
    def add_retraction(viewer):
        """Add retraction event at cursor (key: '6')"""
        if hasattr(widget, 'image_slider'):
            current_tp = widget.image_slider.value()
            add_event_at_cursor(viewer, widget, 'retraction', current_tp)


def update_image(widget, viewer, current, index):
    """Main function to update the displayed image"""
    
    if current < widget.image_slider.maximum():
        widget.prev_btn.setEnabled(True)
        
    try:
        if index < 0 or index >= len(app_state.image_sets_keys):
            widget.log_status(f"Invalid image index: {index+1}")
            return
            
        # Get the image set for the selected index
        current_im_in = app_state.image_sets_keys[index]
        widget.log_status(f"Loading image: {current_im_in}")
                    
        subdirs = [d for d in os.listdir(app_state.loaded_folder) 
                  if os.path.isdir(os.path.join(app_state.loaded_folder, d))]
        subdirs = natsorted(subdirs)
        subdir = subdirs[index]
        
        if int(subdir) > 0:
            subdir_path = os.path.join(app_state.loaded_folder, subdir)
            check_nellie_path = os.path.exists(os.path.join(subdir_path, 'nellie_output/nellie_necessities'))
            nellie_op_path = os.path.join(subdir_path, 'nellie_output/nellie_necessities')
            app_state.nellie_output_path = nellie_op_path
        
            if check_nellie_path:
                # Capture current state before loading new image (if layers exist)
                if len(widget.viewer.layers) > 0:
                    viewer_state.capture_state(widget.viewer)

                # Load images
                raw_im, skel_im, face_colors, positions, colors, edge_lines = load_image_and_skeleton(
                    app_state.nellie_output_path
                )

                # Clear existing layers
                widget.viewer.layers.clear()

                if raw_im is not None and skel_im is not None:
                    # Add layers to viewer
                    add_image_layers(widget, raw_im, skel_im, face_colors, positions, colors, edge_lines)
                    
                    # Restore viewer state after loading new image
                    viewer_state.restore_state(widget.viewer)
                    
                    # Setup key bindings (only once per session to avoid rebinding)
                    if not hasattr(widget, '_key_bindings_setup'):
                        setup_key_bindings(widget, viewer)
                        widget._key_bindings_setup = True
                    
                    widget.log_status(f"Visualization for {nellie_op_path} loaded successfully")
                    widget.network_btn.setEnabled(True)
                
            else:
                # Handle case with only raw TIFF files
                tif_files = [f for f in os.listdir(subdir_path) 
                           if (f.endswith('.ome.tif') or f.endswith('.ome.tiff'))]
                
                for file in tif_files:                            
                    raw_im_path = os.path.join(subdir_path, file)
                    widget.log_status(f"Only Raw Image file found {file}.")
                    
                    # Capture current state before loading new image (if layers exist)
                    if len(widget.viewer.layers) > 0:
                        viewer_state.capture_state(widget.viewer)
                    
                    raw_im = imread(raw_im_path)
                       
                    # Clear existing layers
                    widget.viewer.layers.clear()
                    
                    # Add new layer
                    app_state.raw_layer = widget.viewer.add_image(
                        raw_im, 
                        scale=app_state.visualization_scale,  # Z, Y, X scaling
                        name=f'Raw Image {index+1}'
                    )
                    
                    # Restore viewer state after loading new image
                    viewer_state.restore_state(widget.viewer)
                
    except FileNotFoundError as e:
        widget.log_status(f"Required files not found: {e}")
    except Exception as e:
        widget.log_status(f"Error updating image: {str(e)}")