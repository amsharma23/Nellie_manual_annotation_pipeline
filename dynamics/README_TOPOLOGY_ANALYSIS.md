# Topology-Driven Event Analysis

## Overview

This system provides a **topology-driven approach** to analyzing mitochondrial network dynamics. Instead of only detecting events through spatial matching and then checking if they explain topology changes, this system **reverses the process**: it starts with observed topology changes and infers what events must have occurred.

## Motivation

Traditional event detection uses spatial matching to identify:
- Tip-edge fusion
- Junction breakage
- Tip-tip fusion/fission
- Extrusion/retraction

However, discrepancies can arise from:
1. **Mis-segmentations** - Image processing errors creating/removing nodes artificially
2. **Missing event types** - Events not covered by current classifications
3. **Detection errors** - False positives/negatives in spatial matching

By reconciling detected events with actual topology changes, we can:
- Validate event detection algorithms
- Identify missing event classifications
- Quantify segmentation quality
- Provide ground truth for algorithm improvement

## Key Concepts

### Event Topology Effects

Each event type has a predictable effect on network topology:

| Event Type | Δ Tips | Δ Junctions |
|------------|--------|-------------|
| Tip-edge fusion | -1 | +1 |
| Junction breakage | +1 | -1 |
| Tip-tip fusion | -2 | 0* |
| Tip-tip fission | +2 | 0* |
| Extrusion | +1 | +1 |
| Retraction | -1 | -1 |

*Note: Tip-tip events may create/destroy junctions depending on local topology

### Mathematical Formulation

Given event counts n₁, n₂, ..., n₆, we can predict topology changes:

```
Δtips = -n₁ + n₂ - 2n₃ + 2n₄ + n₅ - n₆
Δjunctions = n₁ - n₂ + n₅ - n₆
```

**Forward problem** (traditional): Detect events → predict topology changes
**Inverse problem** (new): Observe topology changes → infer events

## Modules

### 1. `topology_reconciliation.py`

**Purpose**: Compare detected events against actual topology changes

**Key Functions**:
- `calculate_topology_metrics(df)` - Count tips, junctions, components
- `calculate_actual_topology_changes(combined_df)` - Compute Δtips, Δjunctions per transition
- `calculate_expected_topology_changes(events_dict)` - Predict changes from detected events
- `reconcile_topology_and_events(combined_df, events_dict)` - Compare actual vs. expected
- `print_reconciliation_report(reconciliation)` - Display results

**Usage**:
```python
from dynamics.timeseries_reader_with_dynamics import read_timeseries_csvs_with_dynamics
from dynamics.event_detector import analyze_timeseries_events
from dynamics.topology_reconciliation import reconcile_topology_and_events, print_reconciliation_report

# Load data
combined_df = read_timeseries_csvs_with_dynamics('/path/to/time_series/')

# Detect events
detected_events = analyze_timeseries_events(combined_df, distance_threshold=5.0)

# Reconcile
reconciliation = reconcile_topology_and_events(combined_df, detected_events)
print_reconciliation_report(reconciliation)
```

**Command Line**:
```bash
python -m dynamics.topology_reconciliation /path/to/time_series/ [distance_threshold]
```

### 2. `topology_driven_inference.py`

**Purpose**: Infer event counts from topology changes using optimization

**Key Functions**:
- `infer_events_from_topology_change(delta_tips, delta_junctions, ...)` - Solve inverse problem
- `infer_events_for_timeseries(combined_df, ...)` - Infer events for all transitions
- `compare_detected_vs_inferred(detected_events, inferred_df)` - Compare approaches

**Optimization Methods**:

1. **minimize_total**: Find minimal set of events explaining topology
   - Uses linear programming
   - Provides sparsest solution
   - Ignores detected events

2. **minimize_discrepancy**: Adjust detected events to match topology
   - Uses constrained optimization
   - Minimizes deviation from detected events
   - Provides "corrected" event counts

**Usage**:
```python
from dynamics.topology_driven_inference import infer_events_for_timeseries, compare_detected_vs_inferred

# Infer events (method 1: minimize discrepancy)
inferred_df = infer_events_for_timeseries(
    combined_df,
    detected_events={'event_counts': detected_events['summary_statistics']},
    method='minimize_discrepancy'
)

# Infer events (method 2: minimize total)
inferred_df_sparse = infer_events_for_timeseries(
    combined_df,
    method='minimize_total'
)

# Compare
comparison = compare_detected_vs_inferred(detected_events, inferred_df)
```

**Command Line**:
```bash
python -m dynamics.topology_driven_inference /path/to/time_series/ [method]
```

### 3. `run_topology_analysis.py`

**Purpose**: Comprehensive analysis combining all approaches

**Performs**:
1. Traditional event detection (spatial matching)
2. Topology reconciliation (validate detected events)
3. Topology-driven inference (infer events from topology)
4. Comparison and diagnostic reporting

**Usage**:
```python
from dynamics.run_topology_analysis import run_comprehensive_analysis

results = run_comprehensive_analysis(
    base_folder='/path/to/time_series/',
    distance_threshold=5.0,
    output_folder='/path/to/output/'
)
```

**Command Line**:
```bash
python -m dynamics.run_topology_analysis /path/to/time_series/ [distance_threshold] [output_folder]
```

**Output Files**:
1. `detected_events_summary.csv` - Traditional event counts
2. `topology_reconciliation_summary.csv` - Reconciliation metrics
3. `topology_changes_by_transition.csv` - Actual Δtips, Δjunctions per transition
4. `topology_inferred_events_minimize_discrepancy.csv` - Inferred events (method 1)
5. `comparison_minimize_discrepancy.csv` - Detected vs. inferred (method 1)
6. `topology_inferred_events_minimize_total.csv` - Inferred events (method 2)
7. `comparison_minimize_total.csv` - Detected vs. inferred (method 2)

## Interpretation Guide

### Reconciliation Report

**Percent Explained**: How well detected events account for topology changes
- **>95%**: Excellent - events fully explain topology
- **80-95%**: Good - minor discrepancies
- **<80%**: Poor - significant missing/spurious events

**Discrepancy Signs**:
- **Positive**: More tips/junctions than events predict → missing events or false negatives
- **Negative**: Fewer tips/junctions than events predict → spurious events or false positives

### Comparison Report

**Event Count Differences**:
- **Large positive difference**: Event type under-detected by spatial matching
- **Large negative difference**: Event type over-detected (false positives)
- **Near zero**: Good agreement between methods

### Diagnostic Workflow

1. **Run comprehensive analysis**:
   ```bash
   python -m dynamics.run_topology_analysis /path/to/data/
   ```

2. **Check reconciliation percent explained**:
   - If <90%: Investigate segmentation quality or add event types
   - If >95%: Events well-calibrated

3. **Compare detected vs. inferred event counts**:
   - Large differences indicate specific event types with detection issues
   - Review those event categories for false positives/negatives

4. **Examine transition-by-transition results**:
   - Identify specific time intervals with problems
   - Correlate with image quality or biological events

## Integration with GUI

To integrate with the Napari GUI:

```python
# In gui/dynamics_analysis.py, add topology analysis option

def run_topology_analysis_gui(base_folder):
    """Run topology analysis and store results in app_state."""
    from dynamics.run_topology_analysis import run_comprehensive_analysis

    results = run_comprehensive_analysis(
        base_folder=base_folder,
        distance_threshold=5.0,
        output_folder=base_folder
    )

    app_state.topology_reconciliation = results['reconciliation']
    app_state.topology_inferred = results['inferred_discrepancy']

    log_status("Topology analysis complete!")
    return results
```

## Examples

### Example 1: Basic Reconciliation

```python
import pandas as pd
from dynamics.timeseries_reader_with_dynamics import read_timeseries_csvs_with_dynamics
from dynamics.event_detector import analyze_timeseries_events
from dynamics.topology_reconciliation import reconcile_topology_and_events

# Load and analyze
df = read_timeseries_csvs_with_dynamics('/data/Run_1/time_series/')
events = analyze_timeseries_events(df)
reconciliation = reconcile_topology_and_events(df, events)

# Check results
summary = reconciliation['summary']
print(summary)
```

### Example 2: Infer Missing Events

```python
from dynamics.topology_driven_inference import infer_events_for_timeseries

# Find minimal events explaining topology
inferred = infer_events_for_timeseries(df, method='minimize_total')

# Per-transition analysis
for _, row in inferred.iterrows():
    print(f"{row['transition']}: "
          f"{row['tip_edge_fusion']} fusions, "
          f"{row['junction_breakage']} breakages")
```

### Example 3: Batch Processing

```python
import os
from dynamics.run_topology_analysis import run_comprehensive_analysis

base_path = '/data/'
for run in range(1, 11):
    folder = os.path.join(base_path, f'Run_{run}/time_series/')
    print(f"\nProcessing {folder}...")

    results = run_comprehensive_analysis(folder)

    # Extract key metrics
    summary = results['reconciliation']['summary']
    tips_explained = summary[summary['metric']=='Tips']['percent_explained'].values[0]

    print(f"Run {run}: {tips_explained:.1f}% tips explained")
```

## Limitations

1. **Underdetermined system**: More unknowns (6 events) than equations (2 topology metrics)
   - Solution is not unique
   - Multiple event combinations can explain same topology change
   - Optimization provides one plausible solution

2. **Ambiguous tip-tip events**: Tip-tip fusion/fission may create/destroy junctions
   - Currently assumes neutral effect (Δjunctions = 0)
   - May underestimate junction changes

3. **Assumes no degree-2 events**: Events involving degree-2 nodes not modeled
   - Edge rearrangements without topology change are invisible

4. **Component changes not used**: Currently only uses tips and junctions
   - Could incorporate Δcomponents as third constraint

## Future Enhancements

1. **Extended event taxonomy**: Add degree-2 events, edge rearrangements
2. **Probabilistic inference**: Bayesian approach with event priors
3. **Temporal smoothing**: Use multi-transition constraints
4. **Machine learning**: Train classifiers on topology-validated events
5. **3D visualization**: Display discrepancies in Napari

## References

- Original event detection: `event_detector.py`
- Time series reader: `timeseries_reader_with_dynamics.py`
- Topology CSV creator: See external script for basic topology metrics

## Contact

For questions or issues, please contact the development team.
