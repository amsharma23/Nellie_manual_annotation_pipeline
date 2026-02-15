# Manual Event Correction Guide

## Overview

The manual event correction system allows you to interactively refine dynamic event detection results by adding, deleting, and reclassifying events directly in the Napari viewer.

---

## Workflow

1. **Run dynamics analysis** to detect events
2. **View results** with the time series slider
3. **Select Dynamic Events layer** in Napari
4. **Use keybindings** to correct events
5. **Changes are saved automatically** to event CSV files

---

## Keybindings Reference

### Event Inspection

| Key | Function | Description |
|-----|----------|-------------|
| **Ctrl+i** | Event Info | Display information about the selected event |

### Event Deletion

| Key | Function | Description |
|-----|----------|-------------|
| **d** | Delete | Remove the selected event (false positive) |

### Adding Events (at cursor position)

| Key | Event Type | Color |
|-----|-----------|-------|
| **1** | Tip-Edge Fusion | Gold |
| **2** | Junction Breakage | Dark Orange |
| **3** | Tip-Tip Fusion | Purple |
| **4** | Tip-Tip Fission | Turquoise |
| **5** | Extrusion | Lime |
| **6** | Retraction | Olive |

---

## Detailed Usage

### Deleting False Positive Events

1. Navigate to the timepoint where the false positive appears
2. Select the **Dynamic Events** layer
3. Click on the event point you want to delete
4. Press **`d`** to delete
5. Event is removed from the CSV file and visualization updates

**Example:**
```
You detect a spurious fusion event at timepoint 5
→ Navigate to frame 5 with slider
→ Select the gold-colored event point
→ Press 'd'
→ Event deleted!
```

### Adding Missing Events

Use this when the automatic detection missed an event.

1. Navigate to the timepoint where the event occurred
2. Move cursor to the event location
3. Press the number key for the event type (**1-6**)
4. Event is added at cursor position with default parameters

**Example:**
```
You see a tip-tip fusion that wasn't detected at timepoint 8
→ Navigate to frame 8
→ Position cursor between the two tips
→ Press '3' (tip-tip fusion)
→ Purple event point appears!
```

**Important Notes:**
- For **single-position events** (fusion, breakage): position is set to cursor location
- For **two-position events** (tip-tip, extrusion, retraction): both positions initially set to same location
  - You may need to manually edit the CSV to adjust the second position
- Timepoint is automatically set to current slider value
- Degree and dynamics values use defaults (may need manual CSV editing for accuracy)

### Viewing Event Information

1. Select an event point
2. Press **`Ctrl+i`**
3. Status log shows: Event type, Timepoint, Position

**Example Output:**
```
Selected: Tip-Edge Fusion | Timepoint: 12 | Position: [15.2, 203.4, 187.9]
```

---

## Event Types & Biological Meaning

### 1. Tip-Edge Fusion (Gold)
- **Biology**: Mitochondrial tip contacts an edge and merges
- **Topology**: Degree 1 node → Degree 3 node
- **Signature**: Positive convergence

### 2. Junction Breakage (Dark Orange)
- **Biology**: Junction splits, creating a new tip
- **Topology**: Degree 3 node → Degree 1 node
- **Signature**: Positive divergence

### 3. Tip-Tip Fusion (Purple)
- **Biology**: Two mitochondrial tips fuse together
- **Topology**: 2 degree-1 nodes disappear
- **Signature**: Divergence in both tips

### 4. Tip-Tip Fission (Turquoise)
- **Biology**: An edge splits to create two new tips
- **Topology**: 2 degree-1 nodes appear
- **Signature**: Convergence in at least one tip

### 5. Extrusion (Lime)
- **Biology**: New branch extends from edge
- **Topology**: Tip + junction appear together
- **Signature**: Negative convergence (material extending)

### 6. Retraction (Olive)
- **Biology**: Branch retracts back into network
- **Topology**: Tip + junction disappear together
- **Signature**: Positive divergence (material pulling back)

---

## Data Storage

All corrections are saved to CSV files in your loaded folder:

```
your_timeseries_folder/
├── tip_edge_fusion_events.csv
├── junction_breakage_events.csv
├── tip_tip_fusion_events.csv
├── tip_tip_fission_events.csv
├── extrusion_events.csv
└── retraction_events.csv
```

**CSV Columns:**

**Single-position events** (fusion, breakage):
```csv
position_t1, position_t2, degree_t1, degree_t2, timepoint_1, timepoint_2, convergence/divergence
```

**Two-position events** (tip-tip):
```csv
tip1_position, tip2_position, distance, timepoint_1, timepoint_2, convergence_tip1, convergence_tip2
```

**Extrusion/Retraction**:
```csv
tip_position, junction_position, distance, timepoint_1, timepoint_2, convergence_tip, convergence_junction
```

---

## Tips & Best Practices

### Quality Control Workflow

1. **First pass**: Review automated detection results frame-by-frame
2. **Mark false positives**: Delete spurious events with `d`
3. **Add missing events**: Use number keys (1-6) for overlooked events
4. **Fix misclassifications**: Delete the wrong event with `d`, then add the correct type with number keys (1-6)
5. **Verify corrections**: Re-run analysis to check topology reconciliation

### Common Correction Scenarios

**Segmentation artifacts**:
- Problem: False junctions from imaging noise
- Solution: Delete associated fusion/breakage events

**Tracking errors**:
- Problem: Same tip tracked as different nodes
- Solution: Delete false fission/fusion, add retraction/extrusion

**Event ambiguity**:
- Problem: Could be fusion OR extrusion
- Solution: Press `c` to toggle between types, choose best fit

### Keyboard Shortcuts Summary

```
Network Editing:
  e   - Highlight connections
  u   - Unhighlight connections
  j   - Join nodes
  r   - Remove edge
  i   - Insert node
  v   - Toggle preview
  l   - Lock Z-plane
  x   - Delete node

Event Correction:
  Ctrl+i - Event info
  d      - Delete event
  1-6    - Add event type 1-6
```

---

## Limitations & Caveats

1. **CSV row tracking**: If you manually edit CSVs outside the tool, re-run dynamics analysis to rebuild indices

2. **Two-position events**: Adding tip-tip or extrusion/retraction events creates both positions at cursor
   - Edit CSV manually to separate positions if needed

3. **Persistence validation**: Added events bypass persistence window checks
   - May need manual verification

4. **Dynamics values**: Added events use placeholder values for convergence/divergence
   - Check against actual Nellie dynamics data if critical

5. **Undo functionality**: Currently no built-in undo
   - Consider backing up CSV files before major corrections

---

## Advanced: Manual CSV Editing

For precise control, you can directly edit the event CSV files:

### Editing Event Positions

```python
import pandas as pd

# Load event file
df = pd.read_csv('tip_edge_fusion_events.csv')

# Update position for row 5 (Python 0-indexed, so CSV row 6)
df.at[5, 'position_t2'] = [15.0, 200.0, 180.0]

# Save
df.to_csv('tip_edge_fusion_events.csv', index=False)
```

### Adjusting Event Metadata

```python
# Adjust dynamics values
df.at[5, 'convergence'] = 0.85

# Change timepoints
df.at[5, 'timepoint_1'] = 10
df.at[5, 'timepoint_2'] = 11
```

**After manual CSV edits**: Reload the visualization or navigate to a different frame and back to see changes.

---

## Troubleshooting

**"No event selected" error**
- Ensure Dynamic Events layer is selected
- Click directly on an event point (not empty space)

**Event not deleting**
- Check that CSV file exists in loaded folder
- Verify file permissions (need write access)

**Added event doesn't appear**
- Check you're on correct timepoint
- Ensure cursor is over the image volume
- Check status log for errors

**Colors don't match**
- Reload events layer: Navigate to different frame and back
- Check CSV files weren't modified externally

**Modifications not persisting**
- Events are saved immediately to CSV
- If changes lost, check file system issues
- Don't run dynamics analysis again (overwrites corrections)

---

## Contact & Support

For questions about manual event correction:
1. Check this guide
2. Review event_detector.py documentation
3. Contact development team

---

**Last Updated**: 2026-02-14
