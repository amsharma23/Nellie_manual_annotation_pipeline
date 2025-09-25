from app_state import app_state
from processing.run_nellie_skeleton import run_nellie_processing
from natsort import natsorted
import os
from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, 
QLabel, QPushButton, QSpinBox, QTextEdit, 
QVBoxLayout, QHBoxLayout, QWidget, QFileDialog)


def process_clicked(widget):

        if not app_state.loaded_folder:
            widget.log_status("No folder selected. Please select a folder first.")
            return    
        app_state.folder_type = widget.type_combo.currentText()
        
        try:        
            if app_state.folder_type == 'Single TIFF':
                # Find TIFF files in the directory
                app_state.nellie_output_path = os.path.join(app_state.loaded_folder, 'nellie_output/nellie_necessities')
                tif_files = [f for f in os.listdir(app_state.loaded_folder) if (f.endswith('.ome.tif') or f.endswith('.ome.tiff'))]
                
                if not tif_files:
                    widget.log_status("No .ome.tif files found in the selected folder.")
                    return
                    
                # Use the first TIFF file found
                input_file = tif_files[0]
                im_path = os.path.join(app_state.loaded_folder, input_file)
                
                widget.log_status(f"Processing {im_path}...")
                
                # Run Nellie processing
                im_info = run_nellie_processing(
                    im_path, 
                    remove_edges=widget.remove_edges_check.isChecked(),
                    ch=widget.channel_spin.value()
                )
                
                if im_info:
                    widget.log_status("Processing complete!")
                    widget.view_btn.setEnabled(True)
                    
            elif app_state.folder_type == 'Time Series':
                
                # Look for time series subfolders or files
                time_points = []
                
                # Check if we have subfolders for each time point
                subdirs = [d for d in os.listdir(app_state.loaded_folder) 
                          if os.path.isdir(os.path.join(app_state.loaded_folder, d))]
                
                if subdirs:
                    # Process each subfolder as a time point
                    widget.log_status(f"Found {len(subdirs)} time point folders")
                    
                    for subdir in subdirs:
                        subdir_path = os.path.join(app_state.loaded_folder, subdir)
                        tif_files = [f for f in os.listdir(subdir_path) if (f.endswith('.ome.tif') or f.endswith('.ome.tiff'))]
                        
                        if tif_files:
                            # Use the first TIFF file in this subfolder
                            input_file = tif_files[0]
                            im_path = os.path.join(subdir_path, input_file)
                            time_points.append((subdir, im_path))
                            widget.log_status(f"Added time point from {subdir}: {input_file}"
                            )
                time_points = natsorted(time_points)
                
                # Process each time point
                if not time_points:
                    widget.log_status("No time points found to process.")
                    return
            
                widget.log_status(f"Processing {len(time_points)} time points...")
                
                for i, (time_point, im_path) in enumerate(time_points):
                    widget.log_status(f"Processing time point {time_point} ({i+1}/{len(time_points)})")
                    
                    # Run Nellie processing with time point in the output name
                    im_info = run_nellie_processing(
                        im_path, 
                        num_t=1,  # Pass time point index
                        remove_edges=widget.remove_edges_check.isChecked(),
                        ch=widget.channel_spin.value()
                    )
                    
                    if im_info:
                        widget.log_status(f"Processing complete for time point {time_point}")
                
                widget.log_status("All time points processed successfully!")
                widget.view_btn.setEnabled(True)
                
        except Exception as e:
            widget.log_status(f"Error during processing: {str(e)}")