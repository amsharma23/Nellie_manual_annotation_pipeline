import os
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

from natsort import natsorted

from app_state import app_state
from processing.run_nellie_skeleton import run_nellie_processing, process_single_file

# Try to keep the GUI from being completely frozen during parallel processing
try:
    from qtpy.QtWidgets import QApplication
except Exception:
    QApplication = None


def _flush_gui():
    """Pump pending Qt events so log_status() lines appear during a blocking pool."""
    if QApplication is not None:
        app = QApplication.instance()
        if app is not None:
            app.processEvents()


def _choose_worker_count(num_tasks):
    """Pick a worker count: cpu_count() - 1, capped at num_tasks, min 1."""
    try:
        cores = os.cpu_count() or 1
    except Exception:
        cores = 1
    return max(1, min(num_tasks, cores - 1))


def process_clicked(widget):
    if not app_state.loaded_folder:
        widget.log_status("No folder selected. Please select a folder first.")
        return
    app_state.folder_type = widget.type_combo.currentText()

    try:
        if app_state.folder_type == 'Single TIFF':
            app_state.nellie_output_path = os.path.join(
                app_state.loaded_folder, 'nellie_output/nellie_necessities'
            )
            tif_files = [
                f for f in os.listdir(app_state.loaded_folder)
                if f.endswith('.ome.tif') or f.endswith('.ome.tiff')
            ]
            if not tif_files:
                widget.log_status("No .ome.tif files found in the selected folder.")
                return

            input_file = tif_files[0]
            im_path = os.path.join(app_state.loaded_folder, input_file)
            widget.log_status(f"Processing {im_path}...")

            im_info = run_nellie_processing(
                im_path,
                remove_edges=widget.remove_edges_check.isChecked(),
                ch=widget.channel_spin.value(),
            )
            if im_info:
                widget.log_status("Processing complete!")
                widget.view_btn.setEnabled(True)

        elif app_state.folder_type == 'Time Series':
            # Build the task list (one nellie pipeline per timepoint folder)
            subdirs = [
                d for d in os.listdir(app_state.loaded_folder)
                if os.path.isdir(os.path.join(app_state.loaded_folder, d))
            ]
            time_points = []
            for subdir in subdirs:
                subdir_path = os.path.join(app_state.loaded_folder, subdir)
                tif_files = [
                    f for f in os.listdir(subdir_path)
                    if f.endswith('.ome.tif') or f.endswith('.ome.tiff')
                ]
                if tif_files:
                    im_path = os.path.join(subdir_path, tif_files[0])
                    time_points.append((subdir, im_path))
                    widget.log_status(f"Queued time point {subdir}: {tif_files[0]}")

            time_points = natsorted(time_points)
            if not time_points:
                widget.log_status("No time points found to process.")
                return

            num_workers = _choose_worker_count(len(time_points))
            widget.log_status(
                f"Processing {len(time_points)} time points in parallel "
                f"with {num_workers} worker process{'es' if num_workers != 1 else ''}. "
                f"The GUI may be unresponsive while this runs."
            )
            _flush_gui()

            # Snapshot GUI parameters here — workers don't see app_state.
            z_res = app_state.z_resolution
            y_res = app_state.y_resolution
            x_res = app_state.x_resolution
            remove_edges = widget.remove_edges_check.isChecked()
            ch = widget.channel_spin.value()

            # spawn is the macOS default; force it explicitly so workers
            # don't inherit any GUI/Qt state.
            ctx = mp.get_context('spawn')

            failures = []
            completed = 0
            total = len(time_points)
            with ProcessPoolExecutor(max_workers=num_workers, mp_context=ctx) as pool:
                future_to_tp = {
                    pool.submit(
                        process_single_file,
                        im_path, z_res, y_res, x_res,
                        remove_edges, ch, 1,  # num_t=1 (one timepoint per file)
                    ): tp_label
                    for tp_label, im_path in time_points
                }
                for fut in as_completed(future_to_tp):
                    tp_label = future_to_tp[fut]
                    completed += 1
                    try:
                        path, ok, err = fut.result()
                    except Exception as exc:
                        ok, err, path = False, repr(exc), '?'
                    if ok:
                        widget.log_status(
                            f"[{completed}/{total}] Done: time point {tp_label}"
                        )
                    else:
                        failures.append((tp_label, err))
                        widget.log_status(
                            f"[{completed}/{total}] FAILED time point {tp_label}: {err}"
                        )
                    _flush_gui()

            if failures:
                widget.log_status(
                    f"Finished with {len(failures)} failure(s); "
                    f"{total - len(failures)}/{total} succeeded."
                )
            else:
                widget.log_status(
                    f"All {total} time points processed successfully!"
                )
            widget.view_btn.setEnabled(True)

    except Exception as e:
        widget.log_status(f"Error during processing: {str(e)}")
