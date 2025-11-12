import os
import gc
from natsort import natsorted
from app_state import app_state
import pandas as pd
from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox,
QLabel, QPushButton, QSpinBox, QTextEdit,
QVBoxLayout, QHBoxLayout, QWidget, QFileDialog)



def browse_folder(widget, path_label, process_btn, view_btn, network_btn, graph_btn, type_combo, analyze_dynamics_btn, file_path):
    """Handle browse button click to select input file or folder.

    Args:
        widget: The parent widget for QFileDialog
        path_label: The QLabel to update with folder name
        process_btn: The process button to enable
        view_btn: The view button to potentially enable
        type_combo: ComboBox with folder type selection
    """

    # Clear viewer layers and memory before resetting state
    if hasattr(widget, 'viewer') and widget.viewer is not None:
        try:
            widget.viewer.layers.clear()
            widget.log_status("Cleared previous visualization from viewer.")
        except Exception as e:
            widget.log_status(f"Note: Could not clear viewer layers: {str(e)}")

    # Reset UI elements to initial state
    view_btn.setEnabled(False)
    network_btn.setEnabled(False)
    graph_btn.setEnabled(False)
    analyze_dynamics_btn.setEnabled(False)

    # Reset image slider and navigation if they exist
    if hasattr(widget, 'image_slider'):
        widget.image_slider.setValue(1)
        widget.image_slider.setMaximum(1)
    if hasattr(widget, 'image_label'):
        widget.image_label.setText("Current Image: 1/1")
    if hasattr(widget, 'prev_btn'):
        widget.prev_btn.setEnabled(False)
    if hasattr(widget, 'next_btn'):
        widget.next_btn.setEnabled(False)

    # Reset state when selecting a new file/folder
    app_state.reset()
    app_state.folder_type = type_combo.currentText()

    # Force garbage collection to free memory
    gc.collect()

    if file_path:

        app_state.loaded_folder = file_path
        path_label.setText(os.path.basename(file_path))
        process_btn.setEnabled(True)
        widget.log_status(f"Selected folder: {file_path}")
        
        #check if there's an output folder already
        if app_state.folder_type == 'Single TIFF':
            # Disable dynamics analysis for single TIFF
            analyze_dynamics_btn.setEnabled(False)

            directory_list = [item for item in os.listdir(file_path) if (os.path.isdir(os.path.join(file_path,item)))]

            if 'nellie_output' in directory_list:
                app_state.nellie_output_path = os.path.join(file_path, 'nellie_output/nellie_necessities')
                view_btn.setEnabled(True)
                widget.log_status( f'{file_path} has a processed output already!')
                app_state.node_dataframe = os.path.join(app_state.nellie_output_path, file.endswith('extracted.csv'))
        
        elif app_state.folder_type == 'Time Series':

            subdirs = [d for d in os.listdir(app_state.loaded_folder)
                      if os.path.isdir(os.path.join(app_state.loaded_folder, d)) and d.isdigit()]

            if subdirs:

                # Process each subfolder as a time point
                widget.log_status(f"Found {len(subdirs)} time point folders in {app_state.loaded_folder} to view/process.")
                subdirs = natsorted(subdirs)

                # Check if all subfolders have adjacency list CSV files for dynamics analysis
                all_have_adjacency = True
                missing_adjacency_folders = []

                for subdir in subdirs:
                    subdir_path = os.path.join(app_state.loaded_folder, subdir)
                    check_nellie_path = os.path.exists(os.path.join(subdir_path,'nellie_output/nellie_necessities'))
                
                    if check_nellie_path:
                        
                        view_btn.setEnabled(True)
                        widget.log_status(f"Results to view for {subdir_path} are already available!")
                        nellie_path = os.path.join(subdir_path,'nellie_output/nellie_necessities')
                        nellie_op_files = os.listdir(nellie_path)
                        check_skel = False
                        check_extracted = False
                        check_multigraph_im = False
                        check_adjacency = False

                        for file in nellie_op_files:
                            if file.endswith('im_pixel_class.ome.tif') or file.endswith('im_pixel_class.ome.tiff'):
                                check_skel = True
                            if file.endswith('extracted.csv'):
                                check_extracted = True
                                app_state.node_dataframe = pd.read_csv(
                                    os.path.join(nellie_path, file)
                                )
                            if file.endswith('multigraph.png') or file.endswith('multigraph.pdf'):
                                check_multigraph_im = True
                            if file.endswith('adjacency_list.csv'):
                                check_adjacency = True

                        # Check for adjacency file for dynamics analysis
                        if not check_adjacency:
                            all_have_adjacency = False
                            missing_adjacency_folders.append(subdir)

                        if check_skel and check_extracted and check_multigraph_im:
                            network_btn.setEnabled(True)
                            graph_btn.setEnabled(True)
                            widget.log_status(f"Raw Image is already processed and has a graph image for {subdir}!")
                        
                        elif check_skel and check_extracted:
                            network_btn.setEnabled(True)
                            graph_btn.setEnabled(True)    
                            widget.log_status(f"Raw Image is already processed and has a graph generated that can be visualized for {subdir}!")
                        
                        elif check_skel:
                            network_btn.setEnabled(True)
                            graph_btn.setEnabled(False)
                            widget.log_status(f"Raw Image is already processed and has a skeleton for {subdir}!")
                    else:
                        # No nellie output folder means no adjacency file
                        all_have_adjacency = False
                        missing_adjacency_folders.append(subdir)

                # Enable/disable dynamics analysis button based on adjacency file availability
                if all_have_adjacency:
                    analyze_dynamics_btn.setEnabled(True)
                    widget.log_status("All time points have adjacency files. Dynamics analysis available!")
                else:
                    analyze_dynamics_btn.setEnabled(False)
                    widget.log_status(f"Dynamics analysis disabled. Missing adjacency files in folders: {missing_adjacency_folders}")
