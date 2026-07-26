# Dynamic Event Annotation (standalone)

A minimal napari tool for manually annotating dynamic events on a 4D skeleton.
Stripped from the full Nellie pipeline — **no** network analysis, **no** automated
dynamics detection, **no** Nellie processing. Just: load a 4D stack + skeleton,
annotate events with key bindings, save to CSV.

## Install

With conda (recommended — matches the tested versions):

```bash
cd /Users/amansharma/Documents/Dynamic_annotation_only
conda env create -f environment.yml
conda activate dynamic-annotation
```

Or with pip:

```bash
pip install "napari[all]" tifffile numpy pandas
```

## Run

```bash
cd /Users/amansharma/Documents/Dynamic_annotation_only
python main.py
```

## Workflow

1. **Browse Raw 4D...** — pick the raw 4D OME-TIFF stack `(T, Z, Y, X)`.
2. **Browse Skeleton 4D...** — pick the skeleton / pixel-class 4D OME-TIFF
   (same `T, Z, Y, X` shape). Its non-zero voxels become the `Skeleton` layer.
3. Set the **Z/Y/X resolution** (µm) if needed — this only affects display scaling.
4. **Load / View** — both stacks load into napari. Navigate timepoints with the
   T-slider at the bottom of the viewer.

## Annotation key bindings

Select **one point on the `Skeleton` layer**, then press a key to add an event at
that voxel on the current timepoint:

| Key      | Event              |
|----------|--------------------|
| `Ctrl+1` | Tip-Edge Fusion    |
| `Ctrl+2` | Junction Breakage  |
| `Ctrl+3` | Tip-Tip Fusion     |
| `Ctrl+4` | Tip-Tip Fission    |
| `Ctrl+5` | Extrusion          |
| `Ctrl+6` | Retraction         |

Select **one point on the `Dynamic Events` layer**, then:

| Key      | Action            |
|----------|-------------------|
| `d`      | Delete the event  |
| `Ctrl+i` | Show event info   |

See `Dynamic_Event_Keybindings_Cheatsheet.pdf` for the printable reference.

## Output

Events are written to a per-dataset subfolder next to the raw stack:
`<raw_dir>/<raw_stem>_annotations/`, one CSV per event type
(`tip_edge_fusion_events.csv`, `junction_breakage_events.csv`, …). Each row stores
the event `position` (`[x, y, z]`), `timepoint_1`, `timepoint_2`, and either degree
or distance metadata. Re-loading the same data re-renders the saved events.
