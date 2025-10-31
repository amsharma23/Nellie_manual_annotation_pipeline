from app_state import app_state
from utils.layer_loader import load_image_and_skeleton
from natsort import natsorted
import os
from modifying_topology.edit_node import highlight
from modifying_topology.add_edge import join
from tifffile import imread
from modifying_topology.remove_edge import remove

from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, 
QLabel, QPushButton, QSpinBox, QTextEdit, 
QVBoxLayout, QHBoxLayout, QWidget, QFileDialog)



def update_image(widget,viewer,current,index):

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
            
            if int(subdir)>0:
                
                subdir_path = os.path.join(app_state.loaded_folder, subdir)
                check_nellie_path = os.path.exists(os.path.join(subdir_path, 'nellie_output'))
                nellie_op_path = os.path.join(subdir_path , 'nellie_output')
                app_state.nellie_output_path = nellie_op_path
            
                if(check_nellie_path):

                    # Load images
                    raw_im, skel_im, face_colors, positions, colors, edge_lines = load_image_and_skeleton(app_state.nellie_output_path)
                    
                    # Clear existing layers
                    widget.viewer.layers.clear()
                    
                    if raw_im is not None and skel_im is not None:
                        # Add layers to viewer
                        app_state.raw_layer = widget.viewer.add_image(
                            raw_im, 
                            scale=[1.765, 1, 1],  # Z, Y, X scaling
                            name='Raw Image'
                        )
                        
                        # Add skeleton edges as Shapes layer
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
                            # Add skeleton edges as Shapes layer
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
                                return
                            join(viewer)
                            # Clear existing layers
                            widget.viewer.layers.clear()
            
                            raw_im, skel_im, face_colors, positions, colors, edge_lines = load_image_and_skeleton(app_state.nellie_output_path)
        
                            if raw_im is not None and skel_im is not None:
                    
                                # Add layers to viewer
                                app_state.raw_layer = widget.viewer.add_image(
                                                    raw_im, 
                                                    scale=[1.765, 1, 1],  # Z, Y, X scaling
                                                    name='Raw Image'
                                                    )
                            
                            # Add skeleton edges as Shapes layer
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
                            widget.viewer.layers.clear()
            
                            raw_im, skel_im, face_colors, positions, colors, edge_lines = load_image_and_skeleton(app_state.nellie_output_path)
        
                            if raw_im is not None and skel_im is not None:
                    
                                # Add layers to viewer
                                app_state.raw_layer = widget.viewer.add_image(
                                                    raw_im, 
                                                    scale=[1.765, 1, 1],  # Z, Y, X scaling
                                                    name='Raw Image'
                                                    )
                            
                            # Add skeleton edges as Shapes layer
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
                        
                        widget.log_status(f"Visualization for {nellie_op_path} loaded successfully")
                        widget.network_btn.setEnabled(True)
                        
                
                else:
                   
                   tif_files = [f for f in os.listdir(subdir_path) if (f.endswith('.ome.tif') or f.endswith('.ome.tiff'))]
                   for file in tif_files:                            
                       raw_im_path = (os.path.join(subdir_path, file))
                       widget.log_status(f"Only Raw Image file found {file}.")
                       
                       raw_im = imread(raw_im_path)
                          
                       # Clear existing layers
                       widget.viewer.layers.clear()
                       
                       # Add new layers
                       app_state.raw_layer = widget.viewer.add_image(
                           raw_im, 
                           scale=[1.765, 1, 1],  # Z, Y, X scaling
                           name=f'Raw Image {index+1}'
                       )
                
                    
        except Exception as e:
            widget.log_status(f"Error updating image: {str(e)}")