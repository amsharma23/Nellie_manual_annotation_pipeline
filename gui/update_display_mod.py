from app_state import app_state
from utils.layer_loader import load_image_and_skeleton, load_dynamics_events_layer
from natsort import natsorted
import os
from modifying_topology.edit_node import highlight
from modifying_topology.add_edge import join
from tifffile import imread
from modifying_topology.remove_edge import remove
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
        scale=[1.765, 1, 1],
        name='Raw Image'
    )

    # Add skeleton edges as Shapes layer (lines between connected nodes)
    if edge_lines:
        app_state.skeleton_layer = widget.viewer.add_shapes(
            edge_lines,
            shape_type='path',
            edge_width=0.2,
            edge_color='red',
            face_color='transparent',
            scale=[1.765, 1, 1],
            name='Skeleton Edges'
        )
    else:
        # Fallback to point-based skeleton if no edges available
        app_state.skeleton_layer = widget.viewer.add_points(
            skel_im,
            size=3,
            face_color=face_colors,
            scale=[1.765, 1, 1],
            name='Skeleton'
        )

    # Add extracted nodes if available
    if positions and colors:
        app_state.points_layer = widget.viewer.add_points(
            positions,
            size=3,
            face_color=colors,
            scale=[1.765, 1, 1],
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
        if len(list(viewer.layers[1].selected_data)) == 0:
            widget.log_status("No node selected to edit.")
            return
        highlight(viewer, widget)
        
    @viewer.bind_key('u')
    def unseen(viewer):
        if len(list(viewer.layers[1].selected_data)) == 0:
            widget.log_status("No node selected to edit.")
            return
        if 'Connected Nodes' in [layer.name for layer in viewer.layers]:
            viewer.layers.remove('Connected Nodes')
        app_state.editable_node_positions = []
        app_state.selected_node_position = []
        
    @viewer.bind_key('j')
    def join_points(viewer):
        if len(list(viewer.layers[1].selected_data)) != 2:
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
        if len(list(viewer.layers[1].selected_data)) != 2:
            widget.log_status("Need to select exactly 2 nodes to remove on the skeleton layer.")
            return
            
        try:
            flag = remove(viewer)
            if flag:
                widget.log_status("Need to select exactly 2 nodes that are BOTH NOT RED to remove on the skeleton layer.")
                return
            
            reload_visualization_with_state_preservation(widget)
            widget.log_status("Broke Nodes successfully")
        except Exception as e:
            widget.log_status(f"Error removing edge: {str(e)}")


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
                        scale=[1.765, 1, 1],  # Z, Y, X scaling
                        name=f'Raw Image {index+1}'
                    )
                    
                    # Restore viewer state after loading new image
                    viewer_state.restore_state(widget.viewer)
                
    except FileNotFoundError as e:
        widget.log_status(f"Required files not found: {e}")
    except Exception as e:
        widget.log_status(f"Error updating image: {str(e)}")