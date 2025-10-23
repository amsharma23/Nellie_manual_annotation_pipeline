from app_state import app_state
from utils.layer_loader import load_image_and_skeleton
import os
from natsort import natsorted
from modifying_topology.edit_node import highlight  
from modifying_topology.add_edge import join
from modifying_topology.remove_edge import remove
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
                raw_im, skel_im, face_colors, positions, colors = load_image_and_skeleton(app_state.nellie_output_path)
                
                if raw_im is not None and skel_im is not None:
                    network_btn.setEnabled(True)
                    # Add layers to viewer
                    app_state.raw_layer = widget.viewer.add_image(
                        raw_im, 
                        scale=[1.765, 1, 1],  # Z, Y, X scaling
                        name='Raw Image'
                    )
                    
                    app_state.skeleton_layer = widget.viewer.add_points(
                        skel_im,
                        size=3,
                        face_color=face_colors,
                        scale=[1.765, 1, 1],
                        name='Skeleton'
                    )
                    
                    # Add extracted points if available
                    if positions and colors:

                        widget.graph_btn.setEnabled(True)

                        app_state.points_layer = widget.viewer.add_points(
                            positions,
                            size=5,
                            face_color=colors,
                            scale=[1.765, 1, 1],
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
                
                        raw_im, skel_im, face_colors, positions, colors = load_image_and_skeleton(app_state.nellie_output_path)
                
                        if raw_im is not None and skel_im is not None:
                            
                            # Add layers to viewer
                            app_state.raw_layer = widget.viewer.add_image(
                                raw_im, 
                                scale=[1.765, 1, 1],  # Z, Y, X scaling
                                name='Raw Image'
                            )
                            
                            app_state.skeleton_layer = widget.viewer.add_points(
                                skel_im,
                                size=3,
                                face_color=face_colors,
                                scale=[1.765, 1, 1],
                                name='Skeleton'
                            )
                            
                            # Add extracted points if available
                            if positions and colors:
                                app_state.points_layer = widget.viewer.add_points(
                                    positions,
                                    size=5,
                                    face_color=colors,
                                    scale=[1.765, 1, 1],
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
                
                        raw_im, skel_im, face_colors, positions, colors = load_image_and_skeleton(app_state.nellie_output_path)
                
                        if raw_im is not None and skel_im is not None:
                            network_btn.setEnabled(True)
                            # Add layers to viewer
                            app_state.raw_layer = widget.viewer.add_image(
                                raw_im, 
                                scale=[1.765, 1, 1],  # Z, Y, X scaling
                                name='Raw Image'
                            )
                            
                            app_state.skeleton_layer = widget.viewer.add_points(
                                skel_im,
                                size=3,
                                face_color=face_colors,
                                scale=[1.765, 1, 1],
                                name='Skeleton'
                            )
                            
                            # Add extracted points if available
                            if positions and colors:
                                app_state.points_layer = widget.viewer.add_points(
                                    positions,
                                    size=5,
                                    face_color=colors,
                                    scale=[1.765, 1, 1],
                                    name='Extracted Nodes'
                                )
                            widget.log_status("Broke Nodes sucessfully")
                            return

                    widget.log_status("Visualization loaded successfully")
                    
                
            elif app_state.folder_type == 'Time Series':
                
                # Look for time series subfolders or files
                image_sets = {}
                
                # Check if we have subfolders for each time point
                subdirs = [d for d in os.listdir(app_state.loaded_folder) 
                          if os.path.isdir(os.path.join(app_state.loaded_folder, d)) and d.isdigit()]
                
                if subdirs:
                    
                    # Process each subfolder as a time point
                    widget.log_status(f"Found {len(subdirs)} time point folders in {app_state.loaded_folder} to view.")
                    subdirs = natsorted(subdirs)
                    for subdir in subdirs:
                        
                        subdir_path = os.path.join(app_state.loaded_folder, subdir)
                        check_nellie_path = os.path.exists(os.path.join(subdir_path , 'nellie_output/nellie_necessities'))
                        tif_files = [f for f in os.listdir(os.path.join(subdir_path,'nellie_output/nellie_necessities')) if (f.endswith('-ch0.ome.tif') or f.endswith('raw.ome.tiff'))]
                        
                        if not check_nellie_path :
                            widget.log_status(f"No results to view for {subdir_path} Please run processing first.")
                            continue
                        for file in tif_files:

                            if file.endswith('.ome.tif') or file.endswith('.ome.tiff'):
                            
                                # Extract base name (usually contains time point info)
                                base_parts = file.split('.')
                                if len(base_parts) > 1:
                                    base_name = base_parts[0]  # Remove the last part (ch0, etc.)
                                    if base_name not in image_sets:
                                        image_sets[base_name] = os.path.join(subdir_path,file)
                                    
                                
                    # Store image sets in app state
                    app_state.image_sets_keys = natsorted(image_sets.keys())
                    
                    for k in app_state.image_sets_keys:
                        app_state.image_sets[k] = image_sets[k]
                    
                    # Update slider settings
                    num_images = len(app_state.image_sets)
                    image_slider.setMaximum(max(1, num_images))
                    image_slider.setValue(1)
                    image_label.setText(f"Current Image: 1/{max(1, num_images)}")
                    print(f"Number of images: {num_images}")
                    
                    # Enable/disable navigation buttons
                    prev_btn.setEnabled(num_images > 1)
                    next_btn.setEnabled(num_images > 1)
                    
                    # Clear existing layers
                    viewer.layers.clear()
                    
                    # Initialize with first image
                    if num_images > 0:
                        network_btn.setEnabled(True)
                        widget.update_displayed_image(0)                        
                    
                    else:

                        # Fallback to original method if no image sets were found
                        raw_im, skel_im, face_colors, positions, colors = load_image_and_skeleton(app_state.nellie_output_path)
                        
                        if raw_im is not None and skel_im is not None:
                            
                            # Add layers to viewer
                            app_state.raw_layer = widget.viewer.add_image(
                                raw_im, 
                                scale=[1.765, 1, 1],  # Z, Y, X scaling
                                name='Raw Image'
                            )
                            
                            app_state.skeleton_layer = widget.viewer.add_points(
                                skel_im,
                                size=3,
                                face_color=face_colors,
                                scale=[1.765, 1, 1],
                                name='Skeleton'
                            )
                            
                            # Add extracted points if available
                            if positions and colors:
                                app_state.points_layer = widget.viewer.add_points(
                                    positions,
                                    size=5,
                                    face_color=colors,
                                    scale=[1.765, 1, 1],
                                    name='Extracted Nodes'
                                )
                            
                            @viewer.bind_key('e')
                            def edit(viewer):
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
                                    widget.log_status("Need to select exactly 2 nodes to join.")
                                    join(viewer)
                                    # Clear existing layers
                                    viewer.layers.clear()
                
                                    raw_im, skel_im, face_colors, positions, colors = load_image_and_skeleton(app_state.nellie_output_path)
                
                                    if raw_im is not None and skel_im is not None:
                            
                                     # Add layers to viewer
                                        app_state.raw_layer = widget.viewer.add_image(
                                                            raw_im, 
                                                            scale=[1.765, 1, 1],  # Z, Y, X scaling
                                                            name='Raw Image'
                                                            )
                                    
                                    app_state.skeleton_layer = widget.viewer.add_points(
                                        skel_im,
                                        size=3,
                                        face_color=face_colors,
                                        scale=[1.765, 1, 1],
                                        name='Skeleton'
                                    )
                                    
                                    # Add extracted points if available
                                    if positions and colors:
                                        app_state.points_layer = widget.viewer.add_points(
                                            positions,
                                            size=5,
                                            face_color=colors,
                                            scale=[1.765, 1, 1],
                                            name='Extracted Nodes'
                                        )
                                    widget.log_status("Joined Nodes sucessfully")
                                    return

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
                                viewer.layers.clear()
                
                                raw_im, skel_im, face_colors, positions, colors = load_image_and_skeleton(app_state.nellie_output_path)
            
                                if raw_im is not None and skel_im is not None:
                        
                                    # Add layers to viewer
                                    app_state.raw_layer = widget.viewer.add_image(
                                                        raw_im, 
                                                        scale=[1.765, 1, 1],  # Z, Y, X scaling
                                                        name='Raw Image'
                                                        )
                                
                                app_state.skeleton_layer = widget.viewer.add_points(
                                    skel_im,
                                    size=3,
                                    face_color=face_colors,
                                    scale=[1.765, 1, 1],
                                    name='Skeleton'
                                )
                                
                                # Add extracted points if available
                                if positions and colors:
                                    app_state.points_layer = widget.viewer.add_points(
                                        positions,
                                        size=5,
                                        face_color=colors,
                                        scale=[1.765, 1, 1],
                                        name='Extracted Nodes'
                                    )
                                widget.log_status("Broke Nodes sucessfully")                                
                                return
                            widget.log_status(f"Visualization loaded successfully. Found {num_images} image sets.")
                            network_btn.setEnabled(True)
                    
        except Exception as e:
            widget.log_status(f"Error viewing results: {str(e)}")