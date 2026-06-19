# Nellie Manual Pipeline App

A graphical user interface application for manual network analysis and topology modification using Napari and the Nellie library. 

## Features

### Core Functionality
- **Network Analysis**: Process mitochondrial 3D images using the Nellie pipeline for skeleton extraction and network generation
- **Interactive Visualization**: Built on Napari for intuitive image viewing and manipulation. Time series datasets — whether from numbered timepoint folders or a single 4D OME-TIFF (**4D Stack** mode) — are loaded as a single 4D (T, Z, Y, X) stack so the native napari time slider, arrow keys, and animation controls all work out of the box.
- **Manual Network Editing**: Tools to manually modify network topology including:
  - Add/remove nodes and edges
  - Add junction points and tips
  - Edit existing network structures

### Analysis Modules
- **Dynamics Analysis**: Study temporal changes in network structures
  - Event detection and analysis
  - Time-series data reading and processing
- **Network Processing**: Generate and analyze network structures from image data
- **Topology Modification**: Interactive tools for network editing

## Project Structure

```
├── main.py                     # Application entry point
├── app_state.py               # Global application state management
├── gui/                       # User interface components
│   ├── viewer.py             # Main viewer setup
│   ├── browse.py             # File browser functionality
│   └── ...
├── processing/               # Image and network processing
│   ├── run_nellie_skeleton.py  # Nellie pipeline integration
│   ├── network_generator.py    # Network generation tools
│   └── colouring_network.py   # Network visualization
├── modifying_topology/       # Network editing tools
│   ├── add_tip.py           # Add network tips
│   ├── add_junction.py      # Add junction points
│   ├── add_edge.py          # Add edges
│   └── remove_edge.py       # Remove edges
├── dynamics/                # Time-series and event analysis
│   ├── event_detector.py    # Detect network events
│   ├── analyze_events.py    # Event analysis tools
│   └── timeseries_reader.py # Time-series data handling
└── utils/                   # Utility functions
    ├── layer_loader.py      # Napari layer management
    ├── parsing.py           # Data parsing utilities
    └── adjacency_reader.py  # Network adjacency handling
```

## Installation

### Prerequisites
- Python 3.7+
- Napari
- Nellie library (optional but recommended for full functionality)

### Setup
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Nellie_manual_pipeline_app
   ```

2. Install required dependencies:
   ```bash
   pip install napari nellie
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Data Structure Requirements

### Single Frame Z-stack TIFF (Single TIFF)
For single image analysis, your folder should contain:
```
your_data_folder/
├── image_name.ome.tif    # Required: OME-TIFF format image file
└── [other files...]      # Optional: any other files
```

**Requirements:**
- Must contain at least one `.ome.tif` file
- The `.ome.tif` file is required to run Nellie processing
- Folder can contain additional files, but the OME-TIFF is essential

### Time Series
For time-series analysis, organize your data as follows:
```
your_timeseries_folder/
├── 1/
│   └── timepoint_1.ome.tif    # Required: OME-TIFF for timepoint 1
├── 2/
│   └── timepoint_2.ome.tif    # Required: OME-TIFF for timepoint 2
├── 3/
│   └── timepoint_3.ome.tif    # Required: OME-TIFF for timepoint 3
└── [additional numbered folders...]
```

**Requirements:**
- Each timepoint must be in its own numbered folder (1, 2, 3, etc.)
- Each folder must contain exactly one `.ome.tif` file
- Folder numbers should be sequential starting from 1
- All `.ome.tif` files are required for Nellie processing and dynamics analysis

### 4D Stack (Single 4D OME-TIFF)
For 4D analysis, point the app at a **single** OME-TIFF that contains a time
(`T`) axis — no numbered subfolders needed:
```
your_data_folder/
└── movie.ome.tif        # Required: one (T, Z, Y, X) OME-TIFF with a T dimension
```

**Requirements:**
- Set the **File Type** dropdown to **`4D Stack`**, then **Browse** to the `.ome.tif` *file* (a file picker opens instead of a folder picker).
- The file must have a `T` axis in its OME metadata (shape `(T, Z, Y, X)`).
- Nellie runs **once** over the whole stack (native 4D), writing 4D outputs to `movie/`'s sibling `nellie_output/nellie_necessities/` folder.
- All timepoints must share the same `(Z, Y, X)` shape (guaranteed for a single stack).

## Usage

1. **Launch the Application**: Run `python main.py` to start the Napari viewer with Nellie controls
2. **Load Data**: Use the file browser to load your image data (following the structure above)
3. **Process Networks**: Run Nellie processing pipeline to extract network skeletons
4. **Manual Editing**: Use the topology modification tools to refine networks
5. **Analyze Dynamics**: Study temporal changes using the dynamics analysis tools (Time Series only)

## Time Series Processing (Parallel)

When you click **Run Nellie Processing** on a **Time Series** folder, each timepoint is processed in a separate worker process via a `concurrent.futures.ProcessPoolExecutor` (with macOS's `spawn` start method). By default the pool uses `os.cpu_count() - 1` workers, so on an 8-core machine 7 frames run concurrently. Each frame's outputs land in its own `<N>/nellie_output/nellie_necessities/` folder exactly as in serial mode.

Progress is reported per-frame in the status log (`[k/N] Done: time point M` or `FAILED ...`). The Qt event loop is pumped between completions so log lines appear as the workers finish, though the rest of the GUI may be unresponsive while the pool is running.

**When does parallel help?** It depends on per-frame work vs. worker spin-up. Spawning a fresh Python process and importing Nellie + scipy + skimage + torch costs ~1–1.5 s per worker. So:

- For tiny single-cell crops (~1 MB / frame, ~0.2 s of pipeline work) parallel may be a small loss — spin-up dominates.
- For typical mito 3D stacks (~5–10 MB / frame) parallel is a clear win — expect roughly 5–8× faster on an 8-core Mac.
- For large deskewed volumes (≥50 MB / frame), parallel is essentially `serial / num_workers`.

**Single TIFF** mode is unchanged — it runs serially in the GUI process.

To change the worker count, edit `_choose_worker_count()` in `gui/process_image.py`.

## 4D Stack Processing (Native)

**4D Stack** mode is the recommended way to analyze a movie. Instead of pre-splitting
your data into numbered timepoint folders, you select a single `(T, Z, Y, X)`
OME-TIFF and Nellie processes the entire stack in **one native run**
(`process_4d_file()` keeps the full temporal range rather than collapsing to a
single frame). All outputs land in one `nellie_output/nellie_necessities/`
folder beside the file:

- The raw and skeleton (`im_pixel_class`) TIFFs are 4D `(T, Z, Y, X)`.
- **Generate Network** slices the 4D skeleton per timepoint and writes per-frame
  CSVs named `…_im_pixel_class_t{idx:04d}_adjacency_list.csv` /
  `…_extracted.csv` into that same folder.
- **View Results** loads the single 4D folder as one napari stack — identical
  navigation/editing to numbered-folder Time Series (T-slider, arrow keys,
  Prev/Next, and all editing/event keybindings operate on the current frame).
- **Analyze Dynamics** reads the per-frame CSVs (`read_4d_stack_csvs()`),
  tagging each with `time_point = idx + 1`, then runs the unchanged event
  analysis. The combined CSV and event CSVs are written next to the input file.

The numbered-folder **Time Series** mode is still fully supported.

## Time Series Navigation

When a **Time Series** folder is loaded, all timepoints are stacked into a single 4D (T, Z, Y, X) napari layer rather than being loaded one frame at a time. This means you can navigate frames using any of:

- **Napari's native T-slider** at the bottom of the viewer (drag, animate, scrub)
- **Left / Right arrow keys** (napari's default for stepping the active axis)
- **Prev / Next buttons** in the side panel
- **The image_slider spinbox** in the side panel

All four controls are kept in sync — moving any one updates the others. The `Skeleton`, `Extracted Nodes`, and `Dynamic Events` overlay layers are also 4D, so they automatically show only the points belonging to the current timepoint. All editing keybindings (below) and the dynamics event keys (`1`–`6`, `d`, `Ctrl+i`) operate on whichever frame is currently displayed.

**Requirements:** every frame must have the same `(Z, Y, X)` shape. If shapes differ, the time series will refuse to load and an error is shown.

## Keybindings

### Network Topology Editing

The following keyboard shortcuts are available for network editing after visualization:

| Key | Function | Requirements |
|-----|----------|--------------|
| **e** | Edit/Highlight connections | Select 1 node on skeleton layer |
| **u** | Unsee/Clear highlighted connections | Previously highlighted node selected |
| **j** | Join two nodes (add edge) | Select exactly 2 nodes on skeleton layer |
| **r** | Remove edge between nodes | Select exactly 2 nodes on skeleton layer |
| **i** | Insert new node at cursor | Cursor over image |
| **v** | Toggle insertion preview mode | - |
| **l** | Lock/unlock Z-plane | - |
| **x** | Delete selected node | Select 1 node on Extracted Nodes layer |

### Dynamic Event Correction (Time Series Only)

Manual correction of automatically detected dynamic events:

| Key | Function | Requirements |
|-----|----------|--------------|
| **Ctrl+i** | Show event information | Select 1 event point on Dynamic Events layer |
| **d** | Delete selected event | Select 1 event point on Dynamic Events layer |
| **1** | Add Tip-Edge Fusion at cursor | Cursor over image |
| **2** | Add Junction Breakage at cursor | Cursor over image |
| **3** | Add Tip-Tip Fusion at cursor | Cursor over image |
| **4** | Add Tip-Tip Fission at cursor | Cursor over image |
| **5** | Add Extrusion at cursor | Cursor over image |
| **6** | Add Retraction at cursor | Cursor over image |

For detailed event correction workflow, see [EVENT_CORRECTION_GUIDE.md](dynamics/EVENT_CORRECTION_GUIDE.md)

## Node Color Coding

- **<span style="color:red">Red</span>**: Regular skeleton points
- **<span style="color:blue">Blue</span>**: Tips (degree 1)
- **<span style="color:green">Green</span>**: Junctions (degree 3+)
- **<span style="color:magenta">Magenta</span>**: Degree 2 nodes

### Dynamic Analysis Events
- **<span style="color:gold">Gold</span>**: Tip-Edge fusion
- **<span style="color:darkorange">Dark Orange</span>**: Junction-Breakage
- **<span style="color:purple">Purple</span>**: Tip-Tip fusion
- **<span style="color:turquoise">Turquoise</span>**: Tip-Tip fission
- **<span style="color:lime">Lime</span>**: Extrusion
- **<span style="color:olive">Olive</span>**: Retraction

## Key Components

### Main Application (`main.py`)
- Initializes the Napari viewer
- Loads the main GUI components
- Checks for Nellie library availability

### GUI Components
- **Viewer**: Main Napari interface with custom widgets
- **File Browser**: Navigate and select input files
- **Control Panel**: Processing parameters and options

### Processing Pipeline
- **Nellie Integration**: Automated skeleton extraction and network generation
- **Manual Tools**: Interactive editing of network structures
- **Export Options**: Save processed networks and analysis results

## Dependencies

- **Napari**: Interactive image viewer and GUI framework
- **Nellie**: Biological network analysis library
- **NumPy/Pandas**: Data processing and analysis
- **Various image processing libraries**: For handling different image formats
