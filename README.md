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

## Usage

1. **Launch the Application**: Run `python main.py` to start the Napari viewer with Nellie controls
2. **Load Data**: Use the file browser to load your image data
3. **Process Networks**: Run Nellie processing pipeline to extract network skeletons
4. **Manual Editing**: Use the topology modification tools to refine networks
5. **Analyze Dynamics**: Study temporal changes using the dynamics analysis tools

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
