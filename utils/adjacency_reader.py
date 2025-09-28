#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 17:24:00 2025

@author: amansharma
"""
import os
import pandas as pd
from .parsing import get_float_pos_comma

def adjacency_to_extracted(extracted_csv_path,adjacency_path):
    
    adj_df = pd.read_csv(adjacency_path)
    if os.path.exists(extracted_csv_path):
        ext_df = pd.read_csv(extracted_csv_path)
    else:
        ext_df={}
        
    # Parse adjacency strings and positions
    adjs_list = adj_df['adjacencies'].tolist()
    pos_x = adj_df['pos_x'].tolist()
    pos_y = adj_df['pos_y'].tolist()
    pos_z = adj_df['pos_z'].tolist()

    # Build lists for extracted rows only for nodes that have at least one adjacency
    degrees = []
    positions = []
    neighbours = []

    for i_n, adj_str in enumerate(adjs_list):
        neighs = get_float_pos_comma(adj_str)
        if len(neighs) > 0:
            degrees.append(len(neighs))
            positions.append([pos_z[i_n], pos_y[i_n], pos_x[i_n]])
            neighbours.append(neighs)

    ext_df['Degree of Node'] = degrees
    ext_df['Position(ZXY)'] = positions
    ext_df['Neighbour ID'] = neighbours

    ext_df = pd.DataFrame.from_dict(ext_df)

    # ensure a 'node' column exists (1-based node ids)
    if 'node' not in ext_df.columns:
        ext_df = ext_df.reset_index(drop=True)
        ext_df['node'] = ext_df.index + 1

    ext_df.to_csv(extracted_csv_path,index=False)