#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 17:14:32 2025

@author: amansharma
"""
from tifffile import imread
import os
from napari.utils.notifications import show_info, show_warning, show_error
from .adjacency_reader import adjacency_to_extracted
import pandas as pd
from app_state import app_state
import numpy as np
from .parsing import get_float_pos_comma
import glob
import ast
from collections import deque


def trace_skeleton_path(start_pos, end_pos, skeleton_coords):
    """Trace the path along skeleton voxels from start to end position using BFS.

    Args:
        start_pos: Starting position [z, y, x] - already on skeleton (integer coordinates)
        end_pos: Ending position [z, y, x] - already on skeleton (integer coordinates)
        skeleton_coords: All skeleton voxel coordinates as numpy array

    Returns:
        List of positions forming the path, or straight line if no path found
    """
    try:
        # Convert positions to tuples (they're already exact skeleton coordinates)
        start_voxel = tuple(np.round(start_pos).astype(int))
        end_voxel = tuple(np.round(end_pos).astype(int))

        # If start and end are the same or very close, return simple path
        if start_voxel == end_voxel or np.linalg.norm(np.array(start_pos) - np.array(end_pos)) < 2:
            return [list(start_pos), list(end_pos)]

        # Create set of skeleton voxels for fast lookup
        skeleton_set = set(map(tuple, skeleton_coords.tolist()))

        # BFS to find path
        queue = deque([(start_voxel, [start_voxel])])
        visited = {start_voxel}

        # 26-connectivity offsets for 3D
        neighbors_26 = [
            (dz, dy, dx)
            for dz in [-1, 0, 1]
            for dy in [-1, 0, 1]
            for dx in [-1, 0, 1]
            if not (dz == 0 and dy == 0 and dx == 0)
        ]

        max_iterations = min(10000, len(skeleton_coords))  # Prevent infinite loops
        iterations = 0

        while queue and iterations < max_iterations:
            iterations += 1
            current, path = queue.popleft()

            # Check if we reached the end
            if current == end_voxel:
                # Convert path to list of lists for Napari
                return [list(pos) for pos in path]

            # Explore neighbors
            for offset in neighbors_26:
                neighbor = (
                    current[0] + offset[0],
                    current[1] + offset[1],
                    current[2] + offset[2]
                )

                if neighbor in skeleton_set and neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [neighbor]

                    # Heuristic: prioritize paths going toward the end
                    queue.append((neighbor, new_path))

        # If no path found, return straight line
        return [list(start_pos), list(end_pos)]

    except Exception as e:
        # Fallback to straight line on any error
        return [list(start_pos), list(end_pos)]


def generate_edge_lines(node_df, skeleton_coords=None):
    """Generate line segments for edges between connected nodes.

    Args:
        node_df (DataFrame): DataFrame with columns 'Position(ZXY)' and 'Neighbour ID'
                            Node positions are exact skeleton voxel coordinates (integers)
        skeleton_coords (numpy.ndarray): All skeleton voxel coordinates for path tracing

    Returns:
        list: List of line segments, each as a path of coordinates following skeleton curvature
    """
    edge_lines = []
    processed_edges = set()

    if node_df.empty:
        return edge_lines

    # Create a mapping from node ID to position
    node_id_to_pos = {}
    for idx, row in node_df.iterrows():
        node_id = row['Node ID']
        pos_str = row['Position(ZXY)']
        pos = get_float_pos_comma(pos_str)
        node_id_to_pos[node_id] = pos

    # Determine if we should trace paths or use straight lines
    use_path_tracing = skeleton_coords is not None and len(skeleton_coords) > 0

    # Generate edges
    for idx, row in node_df.iterrows():
        node_id = row['Node ID']
        pos = node_id_to_pos[node_id]

        # Parse neighbor IDs
        neighbor_str = str(row['Neighbour ID'])
        if neighbor_str == 'nan' or neighbor_str == '[]':
            continue

        try:
            neighbor_ids = ast.literal_eval(neighbor_str)
            if not isinstance(neighbor_ids, list):
                neighbor_ids = [neighbor_ids]
        except:
            continue

        # Create edges to neighbors
        for neighbor_id in neighbor_ids:
            # Create unique edge identifier (sorted to avoid duplicates)
            edge_id = tuple(sorted([node_id, neighbor_id]))

            # Skip if edge already processed
            if edge_id in processed_edges:
                continue

            # Get neighbor position
            if neighbor_id in node_id_to_pos:
                neighbor_pos = node_id_to_pos[neighbor_id]

                # Trace path along skeleton if available
                if use_path_tracing:
                    path = trace_skeleton_path(pos, neighbor_pos, skeleton_coords)
                    edge_lines.append(path)
                else:
                    # Fallback to straight line
                    edge_lines.append([pos, neighbor_pos])

                processed_edges.add(edge_id)

    return edge_lines


def load_image_and_skeleton(nellie_output_path):
    """Load raw image and skeleton from Nellie output directory.

    Args:
        nellie_output_path (str): Path to Nellie output directory

    Returns:
        tuple: (raw_image, skeleton_image, face_colors, positions, colors, edge_lines)
    """
    try:
        # Find relevant files in the output directory
        tif_files = os.listdir(nellie_output_path)
        
        # Find raw image file (channel 0)
        raw_files = [f for f in tif_files if f.endswith('-ch0.ome.tif')]
        if not raw_files:
            show_error("No raw image file found in the output directory: " + nellie_output_path)
            return None, None, [], [], [], []
            
        raw_file = raw_files[0]
        basename = raw_file.split(".")[0]
        
        # Find skeleton image file
        skel_files = [f for f in tif_files if f.endswith('-ch0-im_pixel_class.ome.tif')]
        if not skel_files:
            show_error("No skeleton file found in the output directory")
            return None, None, [], [], [], []
        else:
            app_state.nellie_output_path = nellie_output_path
            
        skel_file = skel_files[0]
        
        # Get full paths
        raw_im_path = os.path.join(nellie_output_path, raw_file)
        skel_im_path = os.path.join(nellie_output_path, skel_file)
        
        # Check for node data file
        node_path_extracted = os.path.join(nellie_output_path, f"{basename}_extracted.csv")
        adjacency_path = os.path.join(nellie_output_path, f"{basename}_adjacency_list.csv")
        if os.path.exists(node_path_extracted):
            app_state.node_path = node_path_extracted
            app_state.node_dataframe = pd.read_csv(node_path_extracted) 

        # Load images
        raw_im = imread(raw_im_path)
        skel_im = imread(skel_im_path)
        skel_im = np.transpose(np.nonzero(skel_im))

        # Store skeleton coordinates in app_state for point insertion
        app_state.skeleton_coords = skel_im

        # Default all points to red
        face_color_arr = ['red' for _ in range(len(skel_im))]
        
        #Check if an adjaceny list exists and convert to extracted csv if so
        if os.path.exists(adjacency_path) and not os.path.exists(node_path_extracted):
            adjacency_to_extracted(node_path_extracted,adjacency_path)
        
        if os.path.exists(adjacency_path) and os.path.exists(node_path_extracted):
            node_df = pd.read_csv(node_path_extracted)
            # ensure 'Node ID' column exists (create from index if missing)
            if 'Node ID' not in node_df.columns:
                if 'node' in node_df.columns:
                    node_df.rename(columns={'node': 'Node ID'}, inplace=True)
                else:
                    node_df = node_df.reset_index(drop=True)
                    node_df['Node ID'] = node_df.index + 1
            # coerce to int for consistency
            try:
                node_df['Node ID'] = node_df['Node ID'].astype(int)
            except Exception:
                pass
            app_state.node_dataframe = node_df            
            if node_df.empty or pd.isna(node_df.index.max()):
                adjacency_to_extracted(node_path_extracted,adjacency_path)
        
        # Process extracted nodes if available
        if os.path.exists(node_path_extracted):
            node_df = pd.read_csv(node_path_extracted)
            # ensure 'Node ID' column exists
            if 'Node ID' not in node_df.columns:
                if 'node' in node_df.columns:
                    node_df.rename(columns={'node': 'Node ID'}, inplace=True)
                else:
                    node_df = node_df.reset_index(drop=True)
                    node_df['Node ID'] = node_df.index + 1
            try:
                node_df['Node ID'] = node_df['Node ID'].astype(int)
            except Exception:
                pass
            app_state.node_dataframe = node_df
            
            if not node_df.empty and not pd.isna(node_df.index.max()):
                # Extract node positions and degrees
                pos_extracted = node_df['Position(ZXY)'].values
                show_info(f"Extracted positions: {pos_extracted}")
                
                deg_extracted = node_df['Degree of Node'].values.astype(int)
                positions = [get_float_pos_comma(el) for el in pos_extracted]
                # Generate colors based on node degree
                colors = []
                for i, degree in enumerate(deg_extracted):
                    if degree == 1:
                        colors.append('blue')  # Endpoint nodes
                    elif degree == 0:
                        colors.append('white')  # Isolated nodes
                    elif degree == 2:
                        colors.append('magenta')  
                    else:
                        colors.append('green')  # Junction nodes
                #Map skeleton points to node colors if they match positions
                position_color_map = {}
                for i,pos in enumerate(positions):
                    position_color_map[tuple(pos)] = colors[i]
                #update face colors for skeleton points that match node positions
                for i, point in enumerate(skel_im):
                    point_tuple = tuple(point)
                    if point_tuple in position_color_map:
                        face_color_arr[i] = position_color_map[point_tuple]

                # Generate edge lines from node connectivity with path tracing
                # Pass skeleton coordinates for curved path tracing
                edge_lines = generate_edge_lines(node_df, skeleton_coords=skel_im)

                return raw_im, skel_im, face_color_arr, positions, colors, edge_lines
                
            else:
                # Create empty dataframe if no data
                app_state.node_dataframe = pd.DataFrame(columns=['Node ID','Degree of Node', 'Position(ZXY)'])
                app_state.node_dataframe.to_csv(node_path_extracted, index=False)
                return raw_im, skel_im, face_color_arr, [], [], []
        else:
            # Create new node file if none exists
            app_state.node_dataframe = pd.DataFrame(columns=['Node ID','Degree of Node', 'Position(ZXY)'])
            app_state.node_dataframe.to_csv(node_path_extracted, index=False)
            return raw_im, skel_im, face_color_arr, [], [], []

    except Exception as e:
        show_error(f"Error loading image and skeleton: {str(e)}")
        return None, None, [], [], [], []


def _load_frame_data(nellie_output_path):
    """Load raw, skeleton-voxel coords, face colors, node positions/colors, and
    edge lines for a single timepoint's nellie output folder.

    Returns
    -------
    dict or None
        Keys: raw, skel_coords (N,3 int), face_colors (list), positions (list of [z,y,x]),
        colors (list), edge_lines (list of paths in [z,y,x]), node_df (DataFrame),
        nellie_output_path. None if anything required is missing.
    """
    try:
        tif_files = os.listdir(nellie_output_path)
        raw_files = [f for f in tif_files if f.endswith('-ch0.ome.tif')]
        skel_files = [f for f in tif_files if f.endswith('-ch0-im_pixel_class.ome.tif')]
        if not raw_files or not skel_files:
            return None
        raw_file = raw_files[0]
        skel_file = skel_files[0]
        basename = raw_file.split('.')[0]

        raw_im_path = os.path.join(nellie_output_path, raw_file)
        skel_im_path = os.path.join(nellie_output_path, skel_file)

        raw_im = imread(raw_im_path)
        skel_im_raw = imread(skel_im_path)
        skel_coords = np.transpose(np.nonzero(skel_im_raw))  # (N, 3) ints

        # Make/ensure extracted CSV exists
        node_path_extracted = os.path.join(nellie_output_path, f"{basename}_extracted.csv")
        adjacency_path = os.path.join(nellie_output_path, f"{basename}_adjacency_list.csv")

        if os.path.exists(adjacency_path) and not os.path.exists(node_path_extracted):
            adjacency_to_extracted(node_path_extracted, adjacency_path)

        face_colors = ['red' for _ in range(len(skel_coords))]
        positions = []
        colors = []
        edge_lines = []
        node_df = None

        if os.path.exists(node_path_extracted):
            node_df = pd.read_csv(node_path_extracted)
            # ensure 'Node ID' column exists
            if 'Node ID' not in node_df.columns:
                if 'node' in node_df.columns:
                    node_df.rename(columns={'node': 'Node ID'}, inplace=True)
                else:
                    node_df = node_df.reset_index(drop=True)
                    node_df['Node ID'] = node_df.index + 1
            try:
                node_df['Node ID'] = node_df['Node ID'].astype(int)
            except Exception:
                pass

            if not node_df.empty and not pd.isna(node_df.index.max()):
                pos_extracted = node_df['Position(ZXY)'].values
                deg_extracted = node_df['Degree of Node'].values.astype(int)
                positions = [get_float_pos_comma(el) for el in pos_extracted]
                for degree in deg_extracted:
                    if degree == 1:
                        colors.append('blue')
                    elif degree == 0:
                        colors.append('white')
                    elif degree == 2:
                        colors.append('magenta')
                    else:
                        colors.append('green')

                # Color skeleton voxels where they coincide with nodes
                position_color_map = {tuple(p): c for p, c in zip(positions, colors)}
                for i, point in enumerate(skel_coords):
                    pt = tuple(point.tolist())
                    if pt in position_color_map:
                        face_colors[i] = position_color_map[pt]

                edge_lines = generate_edge_lines(node_df, skeleton_coords=skel_coords)
        else:
            # Create empty extracted CSV so downstream code finds it
            pd.DataFrame(columns=['Node ID', 'Degree of Node', 'Position(ZXY)']).to_csv(
                node_path_extracted, index=False
            )

        return {
            'raw': raw_im,
            'skel_coords': skel_coords,
            'face_colors': face_colors,
            'positions': positions,
            'colors': colors,
            'edge_lines': edge_lines,
            'node_df': node_df,
            'nellie_output_path': nellie_output_path,
            'basename': basename,
            'extracted_csv': node_path_extracted,
        }
    except Exception as e:
        show_error(f"Error loading frame at {nellie_output_path}: {e}")
        return None


def _build_frame_dict(skel_coords, extracted_csv, adjacency_csv, out_dir, basename):
    """Build a per-frame data dict from skeleton voxels + a per-frame CSV.

    Shared by the 4D-Stack loader (`_load_frame_from_3d`) and the post-edit
    refresh (`reload_frame_csv_4dstack`). The ``raw`` key is left as None for
    the caller to fill in (the refresh path doesn't re-read pixels).

    Returns a dict with the same keys as `_load_frame_data`.
    """
    face_colors = ['red' for _ in range(len(skel_coords))]
    positions = []
    colors = []
    edge_lines = []
    node_df = None

    if os.path.exists(adjacency_csv) and not os.path.exists(extracted_csv):
        adjacency_to_extracted(extracted_csv, adjacency_csv)

    if os.path.exists(extracted_csv):
        node_df = pd.read_csv(extracted_csv)
        if 'Node ID' not in node_df.columns:
            if 'node' in node_df.columns:
                node_df.rename(columns={'node': 'Node ID'}, inplace=True)
            else:
                node_df = node_df.reset_index(drop=True)
                node_df['Node ID'] = node_df.index + 1
        try:
            node_df['Node ID'] = node_df['Node ID'].astype(int)
        except Exception:
            pass

        if not node_df.empty and not pd.isna(node_df.index.max()):
            pos_extracted = node_df['Position(ZXY)'].values
            deg_extracted = node_df['Degree of Node'].values.astype(int)
            positions = [get_float_pos_comma(el) for el in pos_extracted]
            for degree in deg_extracted:
                if degree == 1:
                    colors.append('blue')
                elif degree == 0:
                    colors.append('white')
                elif degree == 2:
                    colors.append('magenta')
                else:
                    colors.append('green')

            position_color_map = {tuple(p): c for p, c in zip(positions, colors)}
            for i, point in enumerate(skel_coords):
                pt = tuple(point.tolist())
                if pt in position_color_map:
                    face_colors[i] = position_color_map[pt]

            edge_lines = generate_edge_lines(node_df, skeleton_coords=skel_coords)
    else:
        # Create an empty extracted CSV so editing tools have a target.
        pd.DataFrame(columns=['Node ID', 'Degree of Node', 'Position(ZXY)']).to_csv(
            extracted_csv, index=False
        )

    return {
        'raw': None,
        'skel_coords': skel_coords,
        'face_colors': face_colors,
        'positions': positions,
        'colors': colors,
        'edge_lines': edge_lines,
        'node_df': node_df,
        'nellie_output_path': out_dir,
        'basename': basename,
        'extracted_csv': extracted_csv,
    }


def _frame_csv_names(out_dir, pixel_class_basename, t_idx):
    """Return (extracted_csv, adjacency_csv) paths for a 4D-stack frame."""
    stem = f"{pixel_class_basename}_t{t_idx:04d}"
    return (
        os.path.join(out_dir, f"{stem}_extracted.csv"),
        os.path.join(out_dir, f"{stem}_adjacency_list.csv"),
    )


def _load_frame_from_3d(raw3d, skel3d, out_dir, pixel_class_basename, t_idx):
    """Build one 4D-stack frame's data dict from sliced 3D raw/skeleton arrays."""
    skel_coords = np.transpose(np.nonzero(skel3d))  # (N, 3) ints, (Z, Y, X)
    extracted_csv, adjacency_csv = _frame_csv_names(out_dir, pixel_class_basename, t_idx)
    d = _build_frame_dict(
        skel_coords, extracted_csv, adjacency_csv, out_dir,
        f"{pixel_class_basename}_t{t_idx:04d}",
    )
    d['raw'] = raw3d
    return d


def reload_frame_csv_4dstack(t_idx):
    """Re-read one 4D-stack frame's extracted CSV using cached skeleton voxels.

    Used after a manual edit to refresh just that frame without re-reading the
    (unchanged) raw/skeleton pixels. Returns a per-frame data dict, or None.
    """
    if t_idx is None or t_idx < 0 or t_idx >= len(app_state.skeleton_coords_per_frame):
        return None
    skel_coords = app_state.skeleton_coords_per_frame[t_idx]
    extracted_csv, adjacency_csv = _frame_csv_names(
        app_state.single_output_path, app_state.pixel_class_basename, t_idx
    )
    return _build_frame_dict(
        skel_coords, extracted_csv, adjacency_csv,
        app_state.single_output_path, f"{app_state.pixel_class_basename}_t{t_idx:04d}",
    )


def load_4d_stack(nellie_output_path):
    """Load a single 4D Nellie output folder as 4D-stacked arrays for napari.

    Expects the folder to contain a 4D raw ``-ch0.ome.tif`` and a 4D
    ``-ch0-im_pixel_class.ome.tif`` (both shaped (T, Z, Y, X)). Per-frame node
    data is read from ``{pixel_class_basename}_t{idx:04d}_extracted.csv`` files
    in the same folder (written by `processing.network_generator.get_network`).

    Returns a dict mirroring `load_timeseries_4d`, plus:
        single_output_path      : the one nellie folder
        frame_csv_paths         : list[str] per-frame extracted CSV path
        pixel_class_basename    : str basename driving per-frame CSV names
    Or None on failure.
    """
    if not nellie_output_path or not os.path.exists(nellie_output_path):
        show_error(f"4D output folder not found: {nellie_output_path}")
        return None

    files = os.listdir(nellie_output_path)
    raw_files = [f for f in files if f.endswith('-ch0.ome.tif')]
    skel_files = [f for f in files if f.endswith('-ch0-im_pixel_class.ome.tif')]
    if not raw_files or not skel_files:
        show_error("4D stack: raw or pixel-class file missing in output folder.")
        return None

    raw_path = os.path.join(nellie_output_path, raw_files[0])
    skel_path = os.path.join(nellie_output_path, skel_files[0])
    pixel_class_basename = skel_files[0].split('.')[0]

    raw_4d = imread(raw_path)
    skel_4d = imread(skel_path)

    if raw_4d.ndim != 4:
        show_error(
            f"Expected a 4D raw image (T, Z, Y, X) but got shape {raw_4d.shape}. "
            f"Is this actually a 4D stack?"
        )
        return None
    if skel_4d.ndim != 4 or skel_4d.shape[0] != raw_4d.shape[0]:
        show_error(
            f"Pixel-class shape {skel_4d.shape} does not match raw {raw_4d.shape}."
        )
        return None

    num_t = raw_4d.shape[0]
    per_frame = []
    frame_csv_paths = []
    skel_per_frame = []
    for t in range(num_t):
        d = _load_frame_from_3d(raw_4d[t], skel_4d[t], nellie_output_path,
                                pixel_class_basename, t)
        per_frame.append(d)
        frame_csv_paths.append(d['extracted_csv'])
        skel_per_frame.append(d['skel_coords'])

    # 4D skeleton points: prefix each frame's skel_coords with its t index
    skel_pts_parts = []
    face_colors_all = []
    for t, d in enumerate(per_frame):
        sc = d['skel_coords']
        if len(sc) == 0:
            continue
        t_col = np.full((sc.shape[0], 1), t, dtype=sc.dtype)
        skel_pts_parts.append(np.hstack([t_col, sc]))
        face_colors_all.extend(d['face_colors'])
    skel_points = (
        np.concatenate(skel_pts_parts, axis=0)
        if skel_pts_parts else np.zeros((0, 4), dtype=int)
    )

    # 4D node points
    node_pts_parts = []
    node_colors_all = []
    for t, d in enumerate(per_frame):
        for pos, col in zip(d['positions'], d['colors']):
            node_pts_parts.append([t, pos[0], pos[1], pos[2]])
            node_colors_all.append(col)
    node_points = (
        np.array(node_pts_parts, dtype=float)
        if node_pts_parts else np.zeros((0, 4), dtype=float)
    )

    # 4D edge lines (computed for parity; not currently displayed)
    edge_lines_4d = []
    for t, d in enumerate(per_frame):
        for path in d['edge_lines']:
            edge_lines_4d.append([[t, p[0], p[1], p[2]] for p in path])

    return {
        'raw_4d': raw_4d,
        'skel_points': skel_points,
        'face_colors': face_colors_all,
        'node_points': node_points,
        'node_colors': node_colors_all,
        'edge_lines_4d': edge_lines_4d,
        'per_frame': per_frame,
        'skel_per_frame': skel_per_frame,
        'frame_csv_paths': frame_csv_paths,
        'single_output_path': nellie_output_path,
        'pixel_class_basename': pixel_class_basename,
        'num_t': num_t,
    }


def load_timeseries_4d(loaded_folder):
    """Load an entire time series as 4D-stacked arrays for napari.

    Walks numeric subdirectories (1, 2, 3, ...) of `loaded_folder`, expecting
    each to contain a `nellie_output/nellie_necessities/` folder. Refuses to
    load if frames have mismatched (Z, Y, X) shapes.

    Returns
    -------
    dict with keys:
        raw_4d           : np.ndarray, shape (T, Z, Y, X)
        skel_points      : np.ndarray, shape (N, 4), columns [t, z, y, x]
        face_colors      : list, length N
        node_points      : np.ndarray, shape (M, 4)
        node_colors      : list, length M
        edge_lines_4d    : list of 4D paths, each shape (K, 4)
        timepoint_paths  : list[str], one nellie_output_path per frame
        skel_per_frame   : list[np.ndarray (N_t, 3)]   skeleton coords per frame
        per_frame        : list[dict]                  raw _load_frame_data outputs
    Or None on failure.
    """
    if not os.path.exists(loaded_folder):
        show_error(f"Folder not found: {loaded_folder}")
        return None

    subdirs = [d for d in os.listdir(loaded_folder)
               if os.path.isdir(os.path.join(loaded_folder, d)) and d.isdigit()]
    if not subdirs:
        show_error("No numeric timepoint subfolders found.")
        return None

    from natsort import natsorted
    subdirs = natsorted(subdirs)

    per_frame = []
    timepoint_paths = []
    for sub in subdirs:
        nop = os.path.join(loaded_folder, sub, 'nellie_output', 'nellie_necessities')
        if not os.path.exists(nop):
            show_warning(f"Skipping timepoint {sub}: no nellie_necessities folder.")
            continue
        data = _load_frame_data(nop)
        if data is None:
            show_warning(f"Skipping timepoint {sub}: required files missing.")
            continue
        per_frame.append(data)
        timepoint_paths.append(nop)

    if not per_frame:
        show_error("No loadable timepoints found.")
        return None

    # Refuse on shape mismatch
    shape0 = per_frame[0]['raw'].shape
    for i, d in enumerate(per_frame[1:], start=1):
        if d['raw'].shape != shape0:
            show_error(
                f"Shape mismatch: timepoint 1 is {shape0}, timepoint {i+1} is "
                f"{d['raw'].shape}. Refusing to load."
            )
            return None

    raw_4d = np.stack([d['raw'] for d in per_frame], axis=0)  # (T, Z, Y, X)

    # 4D skeleton points: prefix each frame's skel_coords with its t index
    skel_pts_parts = []
    face_colors_all = []
    skel_per_frame = []
    for t, d in enumerate(per_frame):
        sc = d['skel_coords']
        skel_per_frame.append(sc)
        if len(sc) == 0:
            continue
        t_col = np.full((sc.shape[0], 1), t, dtype=sc.dtype)
        skel_pts_parts.append(np.hstack([t_col, sc]))
        face_colors_all.extend(d['face_colors'])
    if skel_pts_parts:
        skel_points = np.concatenate(skel_pts_parts, axis=0)
    else:
        skel_points = np.zeros((0, 4), dtype=int)

    # 4D node points
    node_pts_parts = []
    node_colors_all = []
    for t, d in enumerate(per_frame):
        for pos, col in zip(d['positions'], d['colors']):
            node_pts_parts.append([t, pos[0], pos[1], pos[2]])
            node_colors_all.append(col)
    if node_pts_parts:
        node_points = np.array(node_pts_parts, dtype=float)
    else:
        node_points = np.zeros((0, 4), dtype=float)

    # 4D edge lines
    edge_lines_4d = []
    for t, d in enumerate(per_frame):
        for path in d['edge_lines']:
            path_4d = [[t, p[0], p[1], p[2]] for p in path]
            edge_lines_4d.append(path_4d)

    return {
        'raw_4d': raw_4d,
        'skel_points': skel_points,
        'face_colors': face_colors_all,
        'node_points': node_points,
        'node_colors': node_colors_all,
        'edge_lines_4d': edge_lines_4d,
        'timepoint_paths': timepoint_paths,
        'skel_per_frame': skel_per_frame,
        'per_frame': per_frame,
    }


def refresh_frame_in_4d(frame_index, layer_skel=None, layer_nodes=None,
                       skel_data_state=None, node_data_state=None,
                       face_colors_state=None, node_colors_state=None,
                       edge_lines_state=None):
    """Re-read one frame's CSV and update the in-memory 4D arrays / lists.

    Returns updated (skel_data, node_data, face_colors, node_colors, edge_lines).
    Pure helper — call sites set the napari layers from the returned arrays.
    """
    # Implemented in the caller for simplicity; this is a stub for symmetry.
    raise NotImplementedError(
        "refresh_frame_in_4d is implemented inline in the caller "
        "(update_display_mod.refresh_4d_frame)."
    )


def load_dynamics_events_layer(viewer, current_timepoint=None):
    """
    Load dynamic events as color-coded points layer in the Napari viewer.

    Args:
        viewer: Napari viewer instance
        current_timepoint: Current timepoint to filter events (optional)

    Returns:
        bool: True if events were loaded successfully, False otherwise
    """
    if not app_state.loaded_folder:
        return False

    # Look for dynamics analysis results CSV files directly in loaded folder
    dynamics_folder = app_state.loaded_folder

    # Define event types and their colors (avoiding network node colors: blue, white, magenta, green, red)
    event_types = {
        'tip_edge_fusion_events.csv': {'color': 'gold', 'name': 'Tip-Edge Fusion'},
        'junction_breakage_events.csv': {'color': 'darkorange', 'name': 'Junction Breakage'},
        'tip_tip_fusion_events.csv': {'color': 'purple', 'name': 'Tip-Tip Fusion'},
        'tip_tip_fission_events.csv': {'color': 'turquoise', 'name': 'Tip-Tip Fission'},
        'extrusion_events.csv': {'color': 'lime', 'name': 'Extrusion'},
        'retraction_events.csv': {'color': 'olive', 'name': 'Retraction'}
    }

    all_points = []
    all_colors = []
    all_properties = []

    try:
        for csv_file, config in event_types.items():
            csv_path = os.path.join(dynamics_folder, csv_file)

            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)

                if df.empty:
                    continue

                # Extract points and filter by timepoint if specified
                points, colors, properties = extract_event_points(df, config, current_timepoint, csv_file)

                all_points.extend(points)
                all_colors.extend(colors)
                all_properties.extend(properties)

        if all_points:
            # Remove existing dynamics events layer if it exists
            layer_names = [layer.name for layer in viewer.layers]
            if "Dynamic Events" in layer_names:
                viewer.layers.remove("Dynamic Events")

            # Add new points layer
            points_array = np.array(all_points)
            properties_dict = {
                'event_type': [prop['event_type'] for prop in all_properties],
                'timepoint': [prop['timepoint'] for prop in all_properties],
                'csv_row_index': [prop['csv_row_index'] for prop in all_properties],
                'csv_file': [prop['csv_file'] for prop in all_properties]
            }

            viewer.add_points(
                points_array,
                properties=properties_dict,
                face_color=all_colors,
                size=8,
                opacity=0.5,
                scale=app_state.visualization_scale,
                name="Dynamic Events"
            )

            show_info(f"Loaded {len(all_points)} dynamic events for timepoint {current_timepoint if current_timepoint else 'all'}")
            return True

    except Exception as e:
        show_error(f"Error loading dynamics events: {str(e)}")
        return False

    return False


def extract_event_points(df, config, current_timepoint=None, csv_file=None):
    """
    Extract points from event DataFrame based on event type structure.

    Args:
        df: Event DataFrame
        config: Event configuration (color, name)
        current_timepoint: Current timepoint to filter by
        csv_file: Name of the CSV file this event came from

    Returns:
        tuple: (points, colors, properties)
    """
    points = []
    colors = []
    properties = []

    for row_idx, row in df.iterrows():
        event_points = []
        event_timepoint = None

        # Handle different event structures - always use timepoint_2
        if 'position_t1' in row and 'position_t2' in row:
            # Events with two timepoints (tip-edge fusion, junction breakage)
            if 'timepoint_2' in row:
                timepoint_2 = row['timepoint_2']
                if current_timepoint is None or current_timepoint == timepoint_2:
                    pos_2 = parse_position(row['position_t2'])
                    if pos_2:
                        event_points.append(pos_2)
                        event_timepoint = timepoint_2

        elif 'tip1_position' in row and 'tip2_position' in row:
            # Tip-tip events
            if 'timepoint_2' in row:
                timepoint_2 = row['timepoint_2']
                if current_timepoint is None or current_timepoint == timepoint_2:
                    pos_1 = parse_position(row['tip1_position'])
                    pos_2 = parse_position(row['tip2_position'])
                    if pos_1 and pos_2:
                        event_points.extend([pos_1, pos_2])
                        event_timepoint = timepoint_2

        elif 'tip_position' in row and 'junction_position' in row:
            # Extrusion/retraction events
            if 'timepoint_2' in row:
                timepoint_2 = row['timepoint_2']
                if current_timepoint is None or current_timepoint == timepoint_2:
                    tip_pos = parse_position(row['tip_position'])
                    junction_pos = parse_position(row['junction_position'])
                    if tip_pos and junction_pos:
                        event_points.extend([tip_pos, junction_pos])
                        event_timepoint = timepoint_2

        # Add points to lists
        for point in event_points:
            points.append(point)
            colors.append(config['color'])
            properties.append({
                'event_type': config['name'],
                'timepoint': event_timepoint,
                'csv_row_index': row_idx,
                'csv_file': csv_file
            })

    return points, colors, properties


def load_dynamics_events_layer_4d(viewer):
    """Load all dynamic events as a single 4D points layer (T, Z, Y, X).

    Reads the same event CSVs as load_dynamics_events_layer but emits one
    combined points layer with a T column so napari's native T-slider
    filters them automatically.
    """
    if not app_state.loaded_folder:
        return False

    dynamics_folder = app_state.loaded_folder
    event_types = {
        'tip_edge_fusion_events.csv': {'color': 'gold', 'name': 'Tip-Edge Fusion'},
        'junction_breakage_events.csv': {'color': 'darkorange', 'name': 'Junction Breakage'},
        'tip_tip_fusion_events.csv': {'color': 'purple', 'name': 'Tip-Tip Fusion'},
        'tip_tip_fission_events.csv': {'color': 'turquoise', 'name': 'Tip-Tip Fission'},
        'extrusion_events.csv': {'color': 'lime', 'name': 'Extrusion'},
        'retraction_events.csv': {'color': 'olive', 'name': 'Retraction'},
    }

    all_points = []
    all_colors = []
    all_properties = []

    try:
        for csv_file, config in event_types.items():
            csv_path = os.path.join(dynamics_folder, csv_file)
            if not os.path.exists(csv_path):
                continue
            df = pd.read_csv(csv_path)
            if df.empty:
                continue

            # Emit one point per event at timepoint_2, with [t, z, y, x] coords
            pts, cols, props = extract_event_points(df, config, None, csv_file)
            # extract_event_points returns 3D [z, y, x] - we need to add the
            # T coordinate from each event's timepoint
            for pt, col, prop in zip(pts, cols, props):
                tp = prop.get('timepoint')
                if tp is None:
                    continue
                # convert 1-indexed timepoint (matches subdir naming) to 0-indexed T axis
                t_idx = int(tp) - 1
                all_points.append([t_idx, pt[0], pt[1], pt[2]])
                all_colors.append(col)
                all_properties.append(prop)

        if not all_points:
            return False

        # Replace any existing Dynamic Events layer
        if "Dynamic Events" in [layer.name for layer in viewer.layers]:
            viewer.layers.remove("Dynamic Events")

        points_array = np.array(all_points)
        properties_dict = {
            'event_type': [p['event_type'] for p in all_properties],
            'timepoint': [p['timepoint'] for p in all_properties],
            'csv_row_index': [p['csv_row_index'] for p in all_properties],
            'csv_file': [p['csv_file'] for p in all_properties],
        }

        # 4D scale: T is unitless, Z/Y/X follow the usual visualization scale
        scale_4d = [1] + list(app_state.visualization_scale)

        viewer.add_points(
            points_array,
            properties=properties_dict,
            face_color=all_colors,
            size=8,
            opacity=0.5,
            scale=scale_4d,
            name="Dynamic Events",
        )

        show_info(f"Loaded {len(all_points)} dynamic events across all timepoints.")
        return True

    except Exception as e:
        show_error(f"Error loading dynamics events (4D): {e}")
        return False


def parse_position(position):
    """
    Parse position from various formats (list, string, etc.)

    Args:
        position: Position data in various formats

    Returns:
        list: [z, y, x] coordinates or None if parsing fails
    """
    try:
        if isinstance(position, str):
            # Handle string representation of list
            import ast
            position = ast.literal_eval(position)

        if isinstance(position, (list, tuple)) and len(position) >= 3:
            # Return as [z, y, x] for Napari
            return [float(position[2]), float(position[1]), float(position[0])]

    except Exception:
        pass

    return None