# Nellie Manual Pipeline App

A graphical user interface application for manual network analysis and topology modification using Napari and the Nellie library. 

## Features

### Core Functionality
- **Network Analysis**: Process mitochondrial 3D images using the Nellie pipeline for skeleton extraction and network generation
- **Interactive Visualization**: Built on Napari for intuitive image viewing and manipulation
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

## Usage

1. **Launch the Application**: Run `python main.py` to start the Napari viewer with Nellie controls
2. **Load Data**: Use the file browser to load your image data (following the structure above)
3. **Process Networks**: Run Nellie processing pipeline to extract network skeletons
4. **Manual Editing**: Use the topology modification tools to refine networks
5. **Analyze Dynamics**: Study temporal changes using the dynamics analysis tools (Time Series only)

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
