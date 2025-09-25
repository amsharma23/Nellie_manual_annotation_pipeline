#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 17:47:10 2025

@author: amansharma
"""
from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, 
QLabel, QPushButton, QSpinBox, QTextEdit, 
QVBoxLayout, QHBoxLayout, QWidget, QFileDialog)
from app_state import app_state
import os
from tifffile import imread
from natsort import natsorted
from processing.run_nellie_skeleton import run_nellie_processing
from utils.layer_loader import load_image_and_skeleton
from processing.network_generator import get_network

class FileLoaderWidget(QWidget):
    """Widget for loading image files and setting processing options."""
    
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.setup_ui()
        
    def setup_ui(self):
        """Create the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title
        title = QLabel("Nellie Network Analysis")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # File selection section
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        file_group.setLayout(file_layout)
        
        # File type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("File Type:")
        type_layout.addWidget(type_label)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Single TIFF", "Time Series"])
        type_layout.addWidget(self.type_combo)
        file_layout.addLayout(type_layout)
        
        # File path display and browse button
        path_layout = QHBoxLayout()
        self.path_label = QLabel("No file selected")
        path_layout.addWidget(self.path_label)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.on_browse_clicked)
        path_layout.addWidget(self.browse_btn)
        file_layout.addLayout(path_layout)
        
        
        
        layout.addWidget(file_group)
        
        # Processing options section
        proc_group = QGroupBox("Processing Options")
        proc_layout = QFormLayout()
        proc_group.setLayout(proc_layout)
        
        # Channel selection
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(0, 10)
        self.channel_spin.setValue(0)
        proc_layout.addRow("Channel Number:", self.channel_spin)
        
        # Remove edges option
        self.remove_edges_check = QCheckBox()
        self.remove_edges_check.setChecked(False)
        proc_layout.addRow("Remove Edge Artifacts:", self.remove_edges_check)
        
        layout.addWidget(proc_group)
        
        # Buttons section
        button_layout = QHBoxLayout()
        
        self.process_btn = QPushButton("Run Nellie Processing")
        self.process_btn.clicked.connect(self.on_process_clicked)
        self.process_btn.setEnabled(False)
        button_layout.addWidget(self.process_btn)
        
        self.view_btn = QPushButton("View Results")
        self.view_btn.clicked.connect(self.on_view_clicked)
        self.view_btn.setEnabled(False)
        button_layout.addWidget(self.view_btn)
        
        layout.addLayout(button_layout)
        
        
        # Image slider section
        slider_group = QGroupBox("Image Navigation")
        slider_layout = QVBoxLayout()
        slider_group.setLayout(slider_layout)
        
        # Slider control
        slider_control_layout = QHBoxLayout()
        self.image_label = QLabel("Current Image: 1/1")
        slider_control_layout.addWidget(self.image_label)
        
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.on_prev_clicked)
        self.prev_btn.setEnabled(False)
        slider_control_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.on_next_clicked)
        self.next_btn.setEnabled(False)
        slider_control_layout.addWidget(self.next_btn)
        
        slider_layout.addLayout(slider_control_layout)
        
        # Slider widget
        slider_widget_layout = QHBoxLayout()
        slider_widget_layout.addWidget(QLabel("Image:"))
        self.image_slider = QSpinBox()
        self.image_slider.setMinimum(1)
        self.image_slider.setMaximum(1)
        self.image_slider.setValue(1)
        self.image_slider.valueChanged.connect(self.on_slider_changed)
        slider_widget_layout.addWidget(self.image_slider)
        
        slider_layout.addLayout(slider_widget_layout)
        layout.addWidget(slider_group)
        
        
        # Status section
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(300)
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status_text)
        
        # Network analysis button
        self.network_btn = QPushButton("Generate Network")
        self.network_btn.clicked.connect(self.on_network_clicked)
        self.network_btn.setEnabled(False)
        layout.addWidget(self.network_btn)
        
    def log_status(self, message):
        """Add a message to the status log."""
        current_text = self.status_text.toPlainText()
        self.status_text.setPlainText(f"{current_text}\n{message}" if current_text else message)
        self.status_text.verticalScrollBar().setValue(self.status_text.verticalScrollBar().maximum())
        
    def on_browse_clicked(self):
        """Handle browse button click to select input file or folder."""
        file_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        app_state.folder_type = self.type_combo.currentText()
        if file_path:
            app_state.loaded_folder = file_path
            self.path_label.setText(os.path.basename(file_path))
            self.process_btn.setEnabled(True)
            self.log_status(f"Selected folder: {file_path}")
            
            #check if there's an output folder already
            if app_state.folder_type == 'Single TIFF':
                directory_list = [item for item in os.listdir(file_path) if (os.path.isdir(os.path.join(file_path,item)))]
                if 'nellie_output' in directory_list:
                    app_state.nellie_output_path = os.path.join(file_path, 'nellie_output')
                    app_state.nellie_output_path = os.path.join(app_state.nellie_output_path, 'nellie_necessities')
                    self.view_btn.setEnabled(True)
                    self.log_status(f'{file_path} has a processed output already!')
            
            elif app_state.folder_type == 'Time Series':
                subdirs = [d for d in os.listdir(app_state.loaded_folder) 
                          if os.path.isdir(os.path.join(app_state.loaded_folder, d))]
                if subdirs:
                    # Process each subfolder as a time point
                    self.log_status(f"Found {len(subdirs)} time point folders")
                    subdirs = natsorted(subdirs)
                    for subdir in subdirs:
                        subdir_path = os.path.join(app_state.loaded_folder, subdir)
                        check_nellie_path = os.path.exists(os.path.join(subdir_path,'nellie_output/nellie_necessities'))
                        
                        if check_nellie_path :
                            self.view_btn.setEnabled(True)
                            self.log_status(f"Results to view for {subdir_path} are already available!")
            
            
    def on_process_clicked(self):
        """Handle process button click to run Nellie processing."""
        if not app_state.loaded_folder:
            self.log_status("No folder selected. Please select a folder first.")
            return
            
        app_state.folder_type = self.type_combo.currentText()
        
        try:
        
            
            if app_state.folder_type == 'Single TIFF':
                
                # Find TIFF files in the directory
                app_state.nellie_output_path = os.path.join(app_state.loaded_folder, 'nellie_output')
                app_state.nellie_output_path = os.path.join(app_state.nellie_output_path, 'nellie_necessities')
                tif_files = [f for f in os.listdir(app_state.loaded_folder) if (f.endswith('.ome.tif') or f.endswith('.ome.tiff'))]
                
                if not tif_files:
                    self.log_status("No .ome.tif files found in the selected folder.")
                    return
                    
                # Use the first TIFF file found
                input_file = tif_files[0]
                im_path = os.path.join(app_state.loaded_folder, input_file)
                
                self.log_status(f"Processing {im_path}...")
                
                # Run Nellie processing
                im_info = run_nellie_processing(
                    im_path, 
                    remove_edges=self.remove_edges_check.isChecked(),
                    ch=self.channel_spin.value()
                )
                
                if im_info:
                    self.log_status("Processing complete!")
                    self.view_btn.setEnabled(True)
                    
            elif app_state.folder_type == 'Time Series':
                
                # Look for time series subfolders or files
                time_points = []
                
                # Check if we have subfolders for each time point
                subdirs = [d for d in os.listdir(app_state.loaded_folder) 
                          if os.path.isdir(os.path.join(app_state.loaded_folder, d))]
                
                if subdirs:
                    # Process each subfolder as a time point
                    self.log_status(f"Found {len(subdirs)} time point folders")
                    
                    for subdir in subdirs:
                        subdir_path = os.path.join(app_state.loaded_folder, subdir)
                        tif_files = [f for f in os.listdir(subdir_path) if (f.endswith('.ome.tif') or f.endswith('.ome.tiff'))]
                        
                        if tif_files:
                            # Use the first TIFF file in this subfolder
                            input_file = tif_files[0]
                            im_path = os.path.join(subdir_path, input_file)
                            time_points.append((subdir, im_path))
                            self.log_status(f"Added time point from {subdir}: {input_file}")
                
                time_points = natsorted(time_points)
                # Process each time point
                if not time_points:
                    self.log_status("No time points found to process.")
                    return
                    
                self.log_status(f"Processing {len(time_points)} time points...")
                
                for i, (time_point, im_path) in enumerate(time_points):
                    self.log_status(f"Processing time point {time_point} ({i+1}/{len(time_points)})")
                    
                    # Run Nellie processing with time point in the output name
                    im_info = run_nellie_processing(
                        im_path, 
                        num_t=1,  # Pass time point index
                        remove_edges=self.remove_edges_check.isChecked(),
                        ch=self.channel_spin.value()
                    )
                    
                    if im_info:
                        self.log_status(f"Processing complete for time point {time_point}")
                
                self.log_status("All time points processed successfully!")
                self.view_btn.setEnabled(True)
                
        except Exception as e:
            self.log_status(f"Error during processing: {str(e)}")
            
    def on_view_clicked(self):
        """Handle view button click to display processing results."""
        current = self.image_slider.value()
        if current == self.image_slider.maximum():
            self.next_btn.setEnabled(False)
        elif current == 0:
            self.prev_btn.setEnabled(False)
            
        app_state.folder_type = self.type_combo.currentText()
       
        try:
            if app_state.folder_type == 'Single TIFF':
                if not app_state.nellie_output_path or not os.path.exists(app_state.nellie_output_path):
                    self.log_status("No results to view. Please run processing first.")
                    return
                # Clear existing layers
                self.viewer.layers.clear()
                
                # Load images
                raw_im, skel_im, face_colors, positions, colors = load_image_and_skeleton(app_state.nellie_output_path)
                
                if raw_im is not None and skel_im is not None:
                    # Add layers to viewer
                    app_state.raw_layer = self.viewer.add_image(
                        raw_im, 
                        scale=[1.765, 1, 1],  # Z, Y, X scaling
                        name='Raw Image'
                    )
                    
                    app_state.skeleton_layer = self.viewer.add_points(
                        skel_im,
                        size=3,
                        face_color=face_colors,
                        scale=[1.765, 1, 1],
                        name='Skeleton'
                    )
                    
                    # Add extracted points if available
                    if positions and colors:
                        app_state.points_layer = self.viewer.add_points(
                            positions,
                            size=5,
                            face_color=colors,
                            scale=[1.765, 1, 1],
                            name='Extracted Nodes'
                        )
                        
                    self.log_status("Visualization loaded successfully")
                    self.network_btn.setEnabled(True)
                
            elif app_state.folder_type == 'Time Series':
                # Look for time series subfolders or files
                image_sets = {}
                # Check if we have subfolders for each time point
                subdirs = [d for d in os.listdir(app_state.loaded_folder) 
                          if os.path.isdir(os.path.join(app_state.loaded_folder, d))]
                if subdirs:
                    # Process each subfolder as a time point
                    self.log_status(f"Found {len(subdirs)} time point folders")
                    subdirs = natsorted(subdirs)
                    for subdir in subdirs:
                        subdir_path = os.path.join(app_state.loaded_folder, subdir)
                        check_nellie_path = os.path.exists(os.path.join(subdir_path , 'nellie_output'))
                        tif_files = [f for f in os.listdir(subdir_path) if (f.endswith('.ome.tif') or f.endswith('.ome.tiff'))]
                        
                        if not check_nellie_path :
                            self.log_status(f"No results to view for {subdir_path} Please run processing first.")
                            continue
                        
                        for file in tif_files:
                            if file.endswith('.ome.tif'):
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
                    self.image_slider.setMaximum(max(1, num_images))
                    self.image_slider.setValue(1)
                    self.image_label.setText(f"Current Image: 1/{max(1, num_images)}")
                    
                    # Enable/disable navigation buttons
                    self.prev_btn.setEnabled(num_images > 1)
                    self.next_btn.setEnabled(num_images > 1)
                    
                    # Clear existing layers
                    self.viewer.layers.clear()
                    
                    # Initialize with first image
                    if num_images > 0:
                        self.update_displayed_image(0)
                    
                    else:
                        # Fallback to original method if no image sets were found
                        raw_im, skel_im, face_colors, positions, colors = load_image_and_skeleton(app_state.nellie_output_path)
                        
                        if raw_im is not None and skel_im is not None:
                            # Add layers to viewer
                            app_state.raw_layer = self.viewer.add_image(
                                raw_im, 
                                scale=[1.765, 1, 1],  # Z, Y, X scaling
                                name='Raw Image'
                            )
                            
                            app_state.skeleton_layer = self.viewer.add_points(
                                skel_im,
                                size=3,
                                face_color=face_colors,
                                scale=[1.765, 1, 1],
                                name='Skeleton'
                            )
                            
                            # Add extracted points if available
                            if positions and colors:
                                app_state.points_layer = self.viewer.add_points(
                                    positions,
                                    size=5,
                                    face_color=colors,
                                    scale=[1.765, 1, 1],
                                    name='Extracted Nodes'
                                )
                    
                        self.log_status(f"Visualization loaded successfully. Found {num_images} image sets.")
                        self.network_btn.setEnabled(True)
                    
        except Exception as e:
            self.log_status(f"Error viewing results: {str(e)}")
            
    def on_network_clicked(self):
        """Handle network button click to generate network representation."""
        if not app_state.nellie_output_path:
            self.log_status("No data to analyze. Please run processing and view results first.")
            return
            
        try:
            # Find pixel classification file
            tif_files = os.listdir(app_state.nellie_output_path)
            pixel_class_files = [f for f in tif_files if f.endswith('-ch0-im_pixel_class.ome.tif')]
            
            if not pixel_class_files:
                self.log_status("No pixel classification file found.")
                return
                
            pixel_class_path = os.path.join(app_state.nellie_output_path, pixel_class_files[0])
            
            # Generate network
            self.log_status("Generating network representation...")
            adjacency_path, edge_path = get_network(pixel_class_path)
            
            if adjacency_path and edge_path:
                self.log_status(f"Network analysis complete. Files saved to:\n- {adjacency_path}\n- {edge_path}")
                
        except Exception as e:
            self.log_status(f"Error generating network: {str(e)}")
            
    def on_prev_clicked(self):
        """Handle previous button click to show previous image."""
        current = self.image_slider.value()
        if current > 1:
            self.next_btn.setEnabled(True)
            self.image_slider.setValue(current - 1)
        elif (current) == 0:
            self.prev_btn.setEnabled(False)            
            self.log_status('Reached End of Time Series')

    def on_next_clicked(self):
        """Handle next button click to show next image."""
        current = self.image_slider.value()
        if current < self.image_slider.maximum():
            self.prev_btn.setEnabled(True)
            self.image_slider.setValue(current + 1)
        elif (current) == self.image_slider.maximum():
            self.next_btn.setEnabled(False)            
            self.log_status('Reached End of Time Series')
            
    def on_slider_changed(self, value):
        """Handle slider value change to update displayed image."""
        self.image_label.setText(f"Current Image: {value}/{self.image_slider.maximum()}")
        self.update_displayed_image(value - 1)  # Convert to 0-based index
        

    def update_displayed_image(self, index):
        """Update the displayed image based on slider index."""
        current = self.image_slider.value()
        if current < self.image_slider.maximum():
            self.prev_btn.setEnabled(True)

            
        try:
            
            if index < 0 or index >= len(app_state.image_sets_keys):
                self.log_status(f"Invalid image index: {index+1}")
                return
                
            # Get the image set for the selected index
            current_im_in = app_state.image_sets_keys[index]
            self.log_status(f"Loading image: {current_im_in}")
            
            
                        
            subdirs = [d for d in os.listdir(app_state.loaded_folder) 
                      if os.path.isdir(os.path.join(app_state.loaded_folder, d))]
            subdirs = natsorted(subdirs)
            subdir = subdirs[index]
            
            if int(subdir)>0:
                
                subdir_path = os.path.join(app_state.loaded_folder, subdir)
                check_nellie_path = os.path.exists(os.path.join(subdir_path, 'nellie_output'))
                nellie_op_path = os.path.join(subdir_path , 'nellie_output')
                
            
                        
                if(check_nellie_path):
                    # Load images
                    raw_im, skel_im, face_colors, positions, colors = load_image_and_skeleton(nellie_op_path)
                    
                    # Clear existing layers
                    self.viewer.layers.clear()
                    
                    if raw_im is not None and skel_im is not None:
                        # Add layers to viewer
                        app_state.raw_layer = self.viewer.add_image(
                            raw_im, 
                            scale=[1.765, 1, 1],  # Z, Y, X scaling
                            name='Raw Image'
                        )
                        
                        app_state.skeleton_layer = self.viewer.add_points(
                            skel_im,
                            size=3,
                            face_color=face_colors,
                            scale=[1.765, 1, 1],
                            name='Skeleton'
                        )
                        
                        # Add extracted points if available
                        if positions and colors:
                            app_state.points_layer = self.viewer.add_points(
                                positions,
                                size=5,
                                face_color=colors,
                                scale=[1.765, 1, 1],
                                name='Extracted Nodes'
                            )
                            
                        self.log_status(f"Visualization for {nellie_op_path} loaded successfully")
                        self.network_btn.setEnabled(True)
                    
                
                else:
                   tif_files = [f for f in os.listdir(subdir_path) if (f.endswith('.ome.tif') or f.endswith('.ome.tiff'))]
                   for file in tif_files:                            
                       raw_im_path = (os.path.join(subdir_path, file))
                       self.log_status(f"Raw Image file found {file}.")
                       
                       raw_im = imread(raw_im_path)
                       
                       
                       # Clear existing layers
                       self.viewer.layers.clear()
                       
                       # Add new layers
                       app_state.raw_layer = self.viewer.add_image(
                           raw_im, 
                           scale=[1.765, 1, 1],  # Z, Y, X scaling
                           name=f'Raw Image {index+1}'
                       )
                
                    
        except Exception as e:
            self.log_status(f"Error updating image: {str(e)}")