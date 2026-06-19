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
    NELLIE_AVAILABLE = True
except ImportError:
    NELLIE_AVAILABLE = False

# Default to CPU. On Apple Silicon, MPS is currently slower than CPU for the
# volumes typical of this pipeline because eigvalsh isn't implemented on MPS
# (CPU fallback) and most scipy.ndimage calls have no GPU equivalent — the
# MPS<->CPU round-trips outweigh the wins on small volumes.
DEFAULT_DEVICE = "cpu"


def process_single_file(im_path, z_res, y_res, x_res,
                        remove_edges=False, ch=0, num_t=None,
                        device=DEFAULT_DEVICE):
    """Run Filter -> Label -> Network on a single OME-TIFF.

    Pure function: no GUI globals, no napari calls. Safe under
    multiprocessing 'spawn'. Returns (im_path, success, error_msg).
    """
    if not NELLIE_AVAILABLE:
        return im_path, False, "Nellie library not installed"

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

        return im_path, True, None
    except Exception as exc:
        logging.exception("Pipeline failed for %s", im_path)
        return im_path, False, repr(exc)


def process_4d_file(im_path, z_res, y_res, x_res,
                    remove_edges=False, ch=0, t_res=1.0,
                    device=DEFAULT_DEVICE):
    """Run Filter -> Label -> Network once on a single 4D OME-TIFF (T, Z, Y, X).

    Unlike ``process_single_file`` (which collapses to a single timepoint), this
    keeps the full temporal range so Nellie produces 4D outputs in one pass.
    Pure function: no GUI globals, no napari calls. Returns
    (im_path, success, num_t, error_msg).
    """
    if not NELLIE_AVAILABLE:
        return im_path, False, 0, "Nellie library not installed"

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

        return im_path, True, num_t, None
    except Exception as exc:
        logging.exception("4D pipeline failed for %s", im_path)
        return im_path, False, 0, repr(exc)


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

    path, ok, err = process_single_file(
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
