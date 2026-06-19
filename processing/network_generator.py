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
from utils.adjacency_reader import adjacency_to_extracted
import networkx as nx
import csv


def _build_network_for_volume(skeleton_zyx, base_name, out_dir):
    """Build the adjacency/edge/extracted CSVs for a single 3D skeleton volume.

    Args:
        skeleton_zyx (np.ndarray): 3D pixel-class skeleton in (Z, Y, X) order,
            exactly as read from a single timepoint of the Nellie output.
        base_name (str): output base name (no extension). Files written are
            ``{base_name}_adjacency_list.csv``, ``{base_name}_edge_list.txt``
            and ``{base_name}_extracted.csv`` in ``out_dir``.
        out_dir (str): directory to write the outputs into.

    Returns:
        tuple: (adjc_path, edge_path) or (None, None) on failure.
    """
    adjc_path = os.path.join(out_dir, f"{base_name}_adjacency_list.csv")
    edge_path = os.path.join(out_dir, f"{base_name}_edge_list.txt")

    # Transpose (Z, Y, X) -> (X, Y, Z) so node positions come out as (x, y, z).
    skeleton = np.transpose(skeleton_zyx)
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
    with open(adjc_path, "w", newline="") as f:
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

    extr_path = os.path.join(out_dir, f"{base_name}_extracted.csv")
    adjacency_to_extracted(extr_path, adjc_path)

    show_info(f"Network analysis complete. Files saved to:\n- {adjc_path}\n- {edge_path}\n- {extr_path}")
    return adjc_path, edge_path


def get_network(pixel_class_path):
    """Generate network representation from a skeleton image.

    Supports both 3D (Z, Y, X) pixel-class images (Single TIFF / per-timepoint
    Time Series) and 4D (T, Z, Y, X) stacks (4D Stack mode). For a 4D stack one
    network is built per timepoint and written to per-frame CSVs named
    ``{base}_t{idx:04d}_adjacency_list.csv`` etc. in the single output folder.

    Args:
        pixel_class_path (str): Path to pixel classification image

    Returns:
        tuple: (adjc_path, edge_path) for the last volume processed, or
            (None, None) on failure.
    """
    try:
        base_name = os.path.basename(pixel_class_path).split(".")[0]
        out_dir = os.path.dirname(pixel_class_path)

        skeleton = imread(pixel_class_path)

        if skeleton.ndim == 4:
            # (T, Z, Y, X): one network per timepoint with per-frame CSV names.
            num_t = skeleton.shape[0]
            show_info(
                f"4D pixel-class {np.shape(skeleton)}: generating networks for "
                f"{num_t} timepoints"
            )
            result = (None, None)
            for t in range(num_t):
                show_info(f"Generating network for timepoint {t + 1}/{num_t}...")
                result = _build_network_for_volume(
                    skeleton[t], f"{base_name}_t{t:04d}", out_dir
                )
            return result

        # 3D volume (Single TIFF or one Time Series frame)
        return _build_network_for_volume(skeleton, base_name, out_dir)

    except Exception as e:
        show_error(f"Error generating network: {str(e)}")
        return None, None
