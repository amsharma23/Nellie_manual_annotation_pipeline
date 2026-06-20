#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nellie pipeline (Filter -> Label -> Network) wrapper.

Exposes two entry points:

- ``process_single_file(...)``: a picklable, module-level worker that takes
  every input as an explicit argument and does NOT touch GUI globals
  (``app_state`` / napari notifications). Safe for use under
  ``concurrent.futures.ProcessPoolExecutor`` with the ``spawn`` start method
  (the macOS default), where each subprocess re-imports modules fresh.

- ``run_nellie_processing(...)``: the original GUI-facing entry point used
  by Single TIFF mode. Reads resolutions from ``app_state`` and delegates
  to ``process_single_file``, then layers in napari notifications.
"""
import os
import logging

try:
    from nellie.im_info.verifier import ImInfo, FileInfo
    from nellie.segmentation.filtering import Filter
    from nellie.segmentation.labelling import Label
    from nellie.segmentation.networking import Network
    from nellie.segmentation.mocap_marking import Markers
    from nellie.tracking.hu_tracking import HuMomentTracking
    from nellie.tracking.voxel_reassignment import VoxelReassigner
    from nellie.feature_extraction.hierarchical import Hierarchy
    NELLIE_AVAILABLE = True
except ImportError:
    NELLIE_AVAILABLE = False


# Files retained in nellie_necessities/ after a successful run. Everything else
# in that folder is pruned to reclaim disk space. NOTE: the raw '-ch0' channel
# passthrough MUST be kept — the viewer loads it as the "Raw Image" layer
# (see utils/layer_loader.py). The reference batch script drops it because it
# never views results; this GUI does, so it stays. Nellie's feature CSVs live
# one level up in nellie_output/ and are left untouched.
_KEEP_TIF_SUFFIXES = (
    '-im_pixel_class.ome.tif', '-im_pixel_class.ome.tiff',
    '-im_instance_label.ome.tif', '-im_instance_label.ome.tiff',
)
# App-generated network CSVs/edge-lists (written later by Generate Network).
_KEEP_CSV_SUFFIXES = (
    '_adjacency_list.csv', '_extracted.csv', '_edge_list.txt',
)


def _keep_necessity(fname):
    """True if a nellie_necessities/ file should survive cleanup."""
    if fname.endswith(_KEEP_TIF_SUFFIXES):
        return True
    if fname.endswith(_KEEP_CSV_SUFFIXES):
        return True
    # Nellie's Hierarchy feature CSVs (features_branches/nodes/voxels/
    # organelles/image) — these land in nellie_necessities/, not one level up.
    if '-features_' in fname and fname.endswith('.csv'):
        return True
    # Raw channel passthrough: has '-ch0' but no derived '-im_' token. Required
    # by the viewer as the "Raw Image".
    if '-ch0' in fname and '-im_' not in fname and (
        fname.endswith('.ome.tif') or fname.endswith('.ome.tiff')
    ):
        return True
    return False


def cleanup_nellie_necessities(im_path):
    """Prune nellie_necessities/ down to the files this app actually needs.

    Retains the raw '-ch0' passthrough, the pixel-class skeleton, the instance
    label, and any app-generated network CSVs/edge-lists; deletes the rest
    (intermediate filtered/preprocessed/marker/skeleton volumes). Leaves
    nellie_output/ (Nellie feature CSVs) and any subfolders untouched.

    Returns the number of files removed.
    """
    nec_dir = os.path.join(os.path.dirname(im_path), 'nellie_output', 'nellie_necessities')
    if not os.path.isdir(nec_dir):
        return 0
    removed = 0
    for fname in os.listdir(nec_dir):
        fpath = os.path.join(nec_dir, fname)
        if not os.path.isfile(fpath):
            continue  # skip subfolders (e.g. network_csvs/)
        if _keep_necessity(fname):
            continue
        try:
            os.remove(fpath)
            removed += 1
        except OSError:
            pass
    return removed

# Default to CPU. On Apple Silicon, MPS is currently slower than CPU for the
# volumes typical of this pipeline because eigvalsh isn't implemented on MPS
# (CPU fallback) and most scipy.ndimage calls have no GPU equivalent — the
# MPS<->CPU round-trips outweigh the wins on small volumes.
DEFAULT_DEVICE = "cpu"


def process_single_file(im_path, z_res, y_res, x_res,
                        remove_edges=False, ch=0, num_t=None,
                        device=DEFAULT_DEVICE):
    """Run the full Nellie pipeline on a single OME-TIFF.

    Filter -> Label -> Network -> Markers -> Hierarchy, then prune the
    nellie_necessities/ folder (see ``cleanup_nellie_necessities``). Markers +
    Hierarchy are what produce Nellie's feature CSVs in nellie_output/.

    Pure function: no GUI globals, no napari calls. Safe under multiprocessing
    'spawn'. Returns (im_path, success, error_msg, num_removed).
    """
    if not NELLIE_AVAILABLE:
        return im_path, False, "Nellie library not installed", 0

    try:
        file_info = FileInfo(im_path)
        file_info.find_metadata()
        file_info.load_metadata()

        file_info.change_dim_res('Z', z_res)
        file_info.change_dim_res('Y', y_res)
        file_info.change_dim_res('X', x_res)
        file_info.change_dim_res('T', 0)

        try:
            if file_info.axes and 'T' in file_info.axes:
                t_len = file_info.shape[file_info.axes.index('T')]
                file_info.select_temporal_range(0, max(0, t_len - 1))
            else:
                file_info.select_temporal_range(0, 0)
        except Exception:
            pass

        im_info = ImInfo(file_info)

        Filter(im_info, num_t, remove_edges=remove_edges, device=device).run()
        logging.info("Filter complete: %s", im_path)
        Label(im_info, num_t, device=device).run()
        logging.info("Label complete: %s", im_path)
        Network(im_info, num_t, device=device).run()
        logging.info("Network complete: %s", im_path)
        Markers(im_info, num_t, device=device).run()
        logging.info("Markers (MOCAP) complete: %s", im_path)
        # HuMomentTracking writes flow_vector_array.npy; VoxelReassigner writes
        # the reassigned label volumes. Both are prerequisites for Hierarchy's
        # motility/node features — without them Hierarchy raises FileNotFoundError.
        HuMomentTracking(im_info, num_t, device=device).run()
        logging.info("HuMomentTracking complete: %s", im_path)
        VoxelReassigner(im_info, num_t, device=device).run()
        logging.info("VoxelReassigner complete: %s", im_path)
        # Hierarchy produces the feature CSVs (features_branches/nodes/voxels/
        # organelles/image). It can still fail on some volumes, so treat a
        # failure as non-fatal — the skeleton/pixel-class outputs remain usable.
        try:
            Hierarchy(im_info, skip_nodes=False, device=device).run()
            logging.info("Hierarchy (feature extraction) complete: %s", im_path)
        except Exception as h_exc:
            logging.warning("Hierarchy feature extraction failed for %s: %r",
                            im_path, h_exc)

        removed = cleanup_nellie_necessities(im_path)
        logging.info("Cleanup removed %d file(s) for %s", removed, im_path)

        return im_path, True, None, removed
    except Exception as exc:
        logging.exception("Pipeline failed for %s", im_path)
        return im_path, False, repr(exc), 0


def process_4d_file(im_path, z_res, y_res, x_res,
                    remove_edges=False, ch=0, t_res=1.0,
                    device=DEFAULT_DEVICE):
    """Run Filter -> Label -> Network once on a single 4D OME-TIFF (T, Z, Y, X).

    Unlike ``process_single_file`` (which collapses to a single timepoint), this
    keeps the full temporal range so Nellie produces 4D outputs in one pass.
    Runs Filter -> Label -> Network -> Markers -> Hierarchy, then prunes
    nellie_necessities/. Pure function: no GUI globals, no napari calls.
    Returns (im_path, success, num_t, error_msg, num_removed).
    """
    if not NELLIE_AVAILABLE:
        return im_path, False, 0, "Nellie library not installed", 0

    try:
        file_info = FileInfo(im_path)
        file_info.find_metadata()
        file_info.load_metadata()

        file_info.change_dim_res('Z', z_res)
        file_info.change_dim_res('Y', y_res)
        file_info.change_dim_res('X', x_res)
        file_info.change_dim_res('T', t_res)

        # Keep every timepoint. If the file has no T axis, fall back to a
        # single timepoint so we degrade gracefully.
        num_t = 1
        try:
            if file_info.axes and 'T' in file_info.axes:
                t_len = file_info.shape[file_info.axes.index('T')]
                num_t = max(1, int(t_len))
                file_info.select_temporal_range(0, num_t - 1)
            else:
                file_info.select_temporal_range(0, 0)
        except Exception:
            pass

        im_info = ImInfo(file_info)

        # num_t=None lets Nellie process the full selected temporal range.
        Filter(im_info, None, remove_edges=remove_edges, device=device).run()
        logging.info("Filter complete (4D): %s", im_path)
        Label(im_info, None, device=device).run()
        logging.info("Label complete (4D): %s", im_path)
        Network(im_info, None, device=device).run()
        logging.info("Network complete (4D): %s", im_path)
        Markers(im_info, None, device=device).run()
        logging.info("Markers (MOCAP) complete (4D): %s", im_path)
        HuMomentTracking(im_info, None, device=device).run()
        logging.info("HuMomentTracking complete (4D): %s", im_path)
        VoxelReassigner(im_info, None, device=device).run()
        logging.info("VoxelReassigner complete (4D): %s", im_path)
        try:
            Hierarchy(im_info, skip_nodes=False, device=device).run()
            logging.info("Hierarchy (feature extraction) complete (4D): %s", im_path)
        except Exception as h_exc:
            logging.warning("Hierarchy feature extraction failed (4D) for %s: %r",
                            im_path, h_exc)

        removed = cleanup_nellie_necessities(im_path)
        logging.info("Cleanup removed %d file(s) for %s", removed, im_path)

        return im_path, True, num_t, None, removed
    except Exception as exc:
        logging.exception("4D pipeline failed for %s", im_path)
        return im_path, False, 0, repr(exc), 0


def run_nellie_processing(im_path, num_t=None, remove_edges=False, ch=0):
    """GUI-facing wrapper for Single TIFF mode.

    Reads resolutions from ``app_state`` and emits napari notifications.
    Time Series mode does not use this — it calls ``process_single_file``
    directly via a ProcessPoolExecutor.
    """
    from app_state import app_state
    from napari.utils.notifications import show_info, show_error

    if not NELLIE_AVAILABLE:
        show_error("Nellie library is required for processing. Please install it first.")
        return None

    path, ok, err, removed = process_single_file(
        im_path,
        z_res=app_state.z_resolution,
        y_res=app_state.y_resolution,
        x_res=app_state.x_resolution,
        remove_edges=remove_edges,
        ch=ch,
        num_t=num_t,
        device=DEFAULT_DEVICE,
    )

    if not ok:
        show_error(f"Error in Nellie processing: {err}")
        return None

    if removed:
        show_info(f"Cleanup: removed {removed} intermediate file(s) from nellie_necessities/")

    # Rebuild ImInfo briefly to collect output paths for the caller
    file_info = FileInfo(im_path)
    file_info.find_metadata()
    file_info.load_metadata()
    file_info.change_dim_res('Z', app_state.z_resolution)
    file_info.change_dim_res('Y', app_state.y_resolution)
    file_info.change_dim_res('X', app_state.x_resolution)
    file_info.change_dim_res('T', 0)
    im_info = ImInfo(file_info)
    show_info("Output directory is " + str(file_info.output_dir))

    created = [p for p in im_info.pipeline_paths.values() if os.path.exists(p)]
    if os.path.exists(im_info.im_path):
        created.append(im_info.im_path)

    show_info("Networking complete")
    return im_info, created
