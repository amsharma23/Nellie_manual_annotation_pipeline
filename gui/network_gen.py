from app_state import app_state
from processing.network_generator import get_network
import os
from natsort import natsorted
from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, 
QLabel, QPushButton, QSpinBox, QTextEdit, 
QVBoxLayout, QHBoxLayout, QWidget, QFileDialog)


def network_click(widget):

    try:
        if (app_state.folder_type == 'Single TIFF'):    
            widget.log_status(f"Starting network generation for single TIFF {app_state.nellie_output_path}")
            # Find pixel classification file
            tif_files = os.listdir(app_state.nellie_output_path)
            pixel_class_files = [f for f in tif_files if (f.endswith('im_pixel_class.ome.tif') or f.endswith('im_pixel_class.ome.tiff'))]
            
            if not pixel_class_files:
                widget.log_status("No pixel classification file found.")
                return
                
            pixel_class_path = os.path.join(app_state.nellie_output_path, pixel_class_files[0])
            
            # Generate network
            widget.log_status(f"Generating network representation for {pixel_class_path}...")
            adjacency_path, edge_path = get_network(pixel_class_path)
            
            if adjacency_path and edge_path:
                widget.log_status(f"Network analysis complete. Files saved to:\n- {adjacency_path}\n- {edge_path}")
                widget.analyze_dynamics_btn.setEnabled(True)
        elif app_state.folder_type == 'Time Series':
                widget.log_status(f"Starting network generation for time series in folder {app_state.loaded_folder}")
                # Check if we have subfolders for each time point
                subdirs = [d for d in os.listdir(app_state.loaded_folder) 
                          if os.path.isdir(os.path.join(app_state.loaded_folder, d))]
                subdirs = natsorted(subdirs)

                if subdirs:
                    # Process each subfolder as a time point
                    widget.log_status(f"Found {len(subdirs)} time point folders")
                    
                    for subdir in subdirs:

                        subdir_path = os.path.join(app_state.loaded_folder, subdir)
                        tif_files = os.listdir(os.path.join(subdir_path,'nellie_output/nellie_necessities'))
                        pixel_class_files = [f for f in tif_files if (f.endswith('im_pixel_class.ome.tif') or f.endswith('im_pixel_class.ome.tiff'))]       

                        if not pixel_class_files:
                            widget.log_status(f"No pixel classification file found for {subdir}.")
                            return

                        pixel_class_path = os.path.join(os.path.join(subdir_path,'nellie_output/nellie_necessities'), pixel_class_files[0])

                        # Generate network
                        widget.log_status(f"Generating network representation for {pixel_class_path}...")
                        adjacency_path, edge_path = get_network(pixel_class_path)
            
                        if adjacency_path and edge_path:
                            widget.log_status(f"Network analysis complete. Files saved to:\n- {adjacency_path}\n- {edge_path}")
                            widget.analyze_dynamics_btn.setEnabled(True)
    
    
    except Exception as e:
        widget.log_status(f"Error generating network: {str(e)}")