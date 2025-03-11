#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 17:42:38 2025

@author: Austin Lefebvre https://github.com/aelefebv
"""
import os
import numpy as np
from tifffile import imread
from napari.utils.notifications import show_info, show_warning, show_error
from scipy.ndimage import label as labell
import networkx as nx
import csv

def get_network(pixel_class_path):
    
    """Generate network representation from a skeleton image.
    
    Args:
        pixel_class_path (str): Path to pixel classification image
        
    Returns:
        tuple: (save_path, edge_path) - Paths to generated CSV and edge list files
    """
    try:
        # Define output file paths
        base_name = os.path.basename(pixel_class_path).split(".")[0]
        save_name = f"{base_name}_adjacency_list.csv"
        save_path = os.path.join(os.path.dirname(pixel_class_path), save_name)
        
        edge_name = f"{base_name}_edge_list.txt"
        edge_path = os.path.join(os.path.dirname(pixel_class_path), edge_name)
        
        # Load the skeleton image
        skeleton = imread(pixel_class_path)
        skeleton = np.transpose(skeleton)
        show_info(f"Skeleton shape: {np.shape(skeleton)}")
        
        # Define 3D connectivity structure
        struct = np.ones((3, 3, 3))
        
        # Extract tree structures
        trees, num_trees = labell(skeleton > 0, structure=struct)
        show_info(f"Found {num_trees} tree structures")
        
        # Convert tips and lone-tips to nodes (all nodes will have value 4)
        skeleton[skeleton == 2] = 4  # Tips
        skeleton[skeleton == 1] = 4  # Lone-tips
        
        # Extract edges (all voxels except nodes)
        no_nodes = np.where(skeleton == 4, 0, skeleton)
        edges, num_edges = labell(no_nodes > 0, structure=struct)
        show_info(f"Found {num_edges} edges")
        
        # Extract nodes
        nodes = np.where(skeleton == 4, 4, 0)
        node_labels, num_nodes = labell(nodes > 0, structure=struct)
        show_info(f"Found {num_nodes} nodes")
        
        # Map nodes to their connected edges
        node_edges = {}
        node_positions = {}
        
        # For each node, find connected edges
        for j_id in range(1, num_nodes + 1):
            # Get coordinates of all voxels in this node
            j_coords = np.argwhere(node_labels == j_id)
            
            # Track edges connected to this node
            connected_edges = set()
            
            if len(j_coords) > 0:
                # Take the first voxel's coordinates
                x, y, z = j_coords[0]
                node_positions[j_id] = (x, y, z)
            else:
                # Fallback if node has no voxels (shouldn't happen)
                node_positions[j_id] = (0, 0, 0)
            
            
            # Check 3x3x3 neighborhood around each node voxel
            for (x, y, z) in j_coords:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        for dz in [-1, 0, 1]:
                            # Skip the center voxel
                            if dx == 0 and dy == 0 and dz == 0:
                                continue
                                
                            # Neighbor coordinates
                            xx, yy, zz = x + dx, y + dy, z + dz
                            
                            # Check bounds
                            if (0 <= xx < skeleton.shape[0] and
                                0 <= yy < skeleton.shape[1] and
                                0 <= zz < skeleton.shape[2]):
                                
                                # If neighbor is part of an edge, add to connected edges
                                edge_label = edges[xx, yy, zz]
                                if edge_label != 0:
                                    connected_edges.add(edge_label)
            
            # Store edges connected to this node
            node_edges[j_id] = connected_edges
        
        # Map edges to connected nodes
        edge_nodes = {}
        for n_id, e_set in node_edges.items():
            for e_id in e_set:
                if e_id not in edge_nodes:
                    edge_nodes[e_id] = set()
                edge_nodes[e_id].add(n_id)
        
        # Create network graph
        G = nx.MultiGraph()
        
        # Add all nodes to graph
        for j_id in range(1, num_nodes + 1):
            x, y, z = node_positions[j_id]
            G.add_node(j_id, pos_x=x, pos_y=y, pos_z=z)

        
        # Add edges between nodes
        for e_id, connected_nodes in edge_nodes.items():
            cn = list(connected_nodes)
            
            if len(cn) == 2:
                # Standard edge between two nodes
                n1, n2 = cn
                G.add_edge(n1, n2, edge_id=e_id)
            elif len(cn) == 1:
                # Self-loop (edge connects to same node)
                (n1,) = cn
                G.add_edge(n1, n1, edge_id=e_id)
            elif len(cn) > 2:
                # Edge connects multiple nodes - add edges between all pairs
                for i in range(len(cn)):
                    for j in range(i + 1, len(cn)):
                        G.add_edge(cn[i], cn[j], edge_id=e_id)
        
        # Find connected components (separate trees)
        components = list(nx.connected_components(G))
        show_info(f"Found {len(components)} connected components")
        
        # Write adjacency list to CSV
        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            # Header row
            writer.writerow(["component_num", "node", "pos_x", "pos_y", "pos_z", "adjacencies"])
            
            # Write each component
            for comp_num, comp in enumerate(components, start=1):
                # Create subgraph for this component
                subG = G.subgraph(comp).copy()
                
                # For each node, write its adjacencies
                for node in sorted(subG.nodes()):
                    
                    # Get node attributes (positions)
                    pos_x = subG.nodes[node]['pos_x']
                    pos_y = subG.nodes[node]['pos_y']
                    pos_z = subG.nodes[node]['pos_z']
                    
                    adjacencies = sorted(list(subG[node]))
                    writer.writerow([comp_num, node, pos_x, pos_y, pos_z, adjacencies])
            
        
        # Write edge list
        nx.write_edgelist(G, edge_path)
        
        show_info(f"Network analysis complete. Files saved to:\n- {save_path}\n- {edge_path}")
        return save_path, edge_path
        
    except Exception as e:
        show_error(f"Error generating network: {str(e)}")
        return None, None