#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 17:39:25 2025

@author: amansharma
"""
# Check if Nellie is available
try:
    from nellie.im_info.im_info import ImInfo
    from nellie.segmentation.filtering import Filter
    from nellie.segmentation.labelling import Label
    from nellie.segmentation.networking import Network
    NELLIE_AVAILABLE = True
except ImportError:
    NELLIE_AVAILABLE = False
from napari.utils.notifications import show_info, show_warning, show_error

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
        
        # Initialize ImInfo with the image
        im_info = ImInfo(im_path, ch=ch)
        
        # Set dimension sizes (adjust these values based on your imaging parameters)
        im_info.dim_sizes = {'Z': 0.30, 'Y': 0.17, 'X': 0.17, 'T': 0}
        #show_info(f"Dimension sizes set: {im_info.dim_sizes}")
        
        # Filtering step
        preprocessing = Filter(im_info, num_t, remove_edges=remove_edges)
        preprocessing.run()
        #show_info("Filtering complete")
        
        # Segmentation step
        segmenting = Label(im_info, num_t)
        segmenting.run()
        #show_info("Segmentation complete")
        
        # Network analysis
        networking = Network(im_info, num_t)
        networking.run()
        show_info("Networking complete")
        
        return im_info
    
    except Exception as e:
        show_error(f"Error in Nellie processing: {str(e)}")
        return None