#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 17:39:25 2025

@author: amansharma
"""
# Check if Nellie is available
try:
    from nellie.im_info.verifier import ImInfo
    from nellie.im_info.verifier import FileInfo
    from nellie.segmentation.filtering import Filter
    from nellie.segmentation.labelling import Label
    from nellie.segmentation.networking import Network
    NELLIE_AVAILABLE = True
except ImportError:
    NELLIE_AVAILABLE = False
from napari.utils.notifications import show_info, show_warning, show_error
import os
import logging
from app_state import app_state

def run_nellie_processing(im_path, num_t=None, remove_edges=False, ch=0):
    
    """Run the complete Nellie processing pipeline on an image.
    
    Args:
        im_path (str): Path to input image file
        num_t (int, optional): Number of time points
        remove_edges (bool): Whether to remove edge artifacts
        ch (int): Channel number to process
        
    Returns:
        ImInfo: Object containing processed data
    """
    if not NELLIE_AVAILABLE:
        show_error("Nellie library is required for processing. Please install it first.")
        return None
    
    try:
        # Initialize FileInfo, load metadata and set dimension resolutions
        file_info = FileInfo(im_path)
        # read file metadata and populate axes/shape/dim_res
        file_info.find_metadata()
        file_info.load_metadata()

        # Set dimension sizes from GUI resolution settings
        # use change_dim_res to ensure FileInfo internal validation runs
        file_info.change_dim_res('Z', app_state.z_resolution)
        file_info.change_dim_res('Y', app_state.y_resolution)
        file_info.change_dim_res('X', app_state.x_resolution)
        file_info.change_dim_res('T', 0)

        # Ensure selected temporal range does not exceed actual frames
        try:
            if file_info.axes and 'T' in file_info.axes:
                t_len = file_info.shape[file_info.axes.index('T')]
                # set temporal range to available frames
                file_info.select_temporal_range(0, max(0, t_len - 1))
            else:
                # no T axis in original file -> single frame; set temporal range to (0,0)
                file_info.select_temporal_range(0, 0)
        except Exception:
            # if anything goes wrong here, just continue and let Nellie handle
            pass

        # Now create ImInfo from the populated FileInfo
        im_info = ImInfo(file_info)
        show_info("Output directory is "+str(file_info.output_dir))
        # Filtering step
        try:
            preprocessing = Filter(im_info, num_t, remove_edges=remove_edges)
            preprocessing.run()
            #show_info("Filtering complete")
            logging.info('Filtering complete')
        except Exception as e:
            logging.exception('Filtering step failed')
            raise
        
        # Segmentation step
        try:
            segmenting = Label(im_info, num_t)
            segmenting.run()
            #show_info("Segmentation complete")
            logging.info('Segmentation complete')
        except Exception as e:
            logging.exception('Segmentation step failed')
            raise
        
        # Network analysis
        try:
            networking = Network(im_info, num_t)
            networking.run()
            logging.info('Networking complete')
        except Exception as e:
            logging.exception('Networking step failed')
            raise
        
        # Collect which pipeline outputs were created
        created = []
        for k, path in im_info.pipeline_paths.items():
            if os.path.exists(path):
                created.append(path)

        # also include the main ome path
        if os.path.exists(im_info.im_path):
            created.append(im_info.im_path)

        show_info("Networking complete")
        return im_info, created
    
    except Exception as e:
        show_error(f"Error in Nellie processing: {str(e)}")
        return None