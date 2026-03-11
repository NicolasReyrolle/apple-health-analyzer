# Apple Health Analyzer - Next Implementation Steps

## Current State Analysis

### Completed Features

- ✅ Core parsing infrastructure (ExportParser with streaming XML)
- ✅ WorkoutManager with comprehensive metrics aggregation (by_activity and by_period methods)
- ✅ UI tabs: Overview, Activities (with pie/rose charts), and Trends (with bar charts + moving average)
- ✅ Data export (JSON/CSV)
- ✅ Activity filtering (dropdown with activity type selection)
- ✅ **Date range filtering** (date picker with start/end dates)
- ✅ **Trends period aggregation** (week/month/quarter/year selector)
- ✅ **Health Data tab** with period-based charts for resting heart rate, body mass, and VO2 max
- ✅ Gap-aware health-data time series (missing periods shown explicitly, not coerced to zero)
- ✅ Multilingual support (EN/FR) via gettext (`.pot`/`.po`/`.mo`) with runtime language switching
- ✅ Localized progress/loading status text in the UI (parser remains language-agnostic internally)
- ✅ Localized date-picker day/month labels sourced from gettext catalogs
- ✅ **Best Segments tab** with asynchronous loading, expandable rows, and localized labels
- ✅ Standard running segment catalog from **100m to 100km**, including named half-marathon and marathon distances
- ✅ Best-segment label formatting extracted to reusable UI helpers (`distance`, `duration`, `date`)
- ✅ Multi-file workout route handling with merged route geometry and `routeFiles` metadata retention
- ✅ Startup compilation of gettext catalogs (`.po` → `.mo`) with `.mo` files ignored in git
- ✅ Comprehensive test coverage for all metrics methods and filtering features

### Work In Progress

1. **Health Data breadth** - Additional record types and richer health analytics are still limited.
2. **Best-segments analytics depth** - Current implementation focuses on fastest segments; richer split/pace analytics are still limited.

## Recommended Next Steps

### Priority 1: Expand Health Data Coverage

**Why:** The Health Data tab is now available, but only a subset of metrics is visualized.

**Implementation:**

1. Extend [src/logic/export_parser.py](src/logic/export_parser.py):
   - Improve normalization for additional record types (sleep, blood pressure, respiratory rate, etc.)
   - Keep metadata parsing behavior stable for enumerated values

2. Extend [src/logic/records_by_type.py](src/logic/records_by_type.py):
   - Add convenience accessors + period aggregations for new metrics
   - Keep missing periods explicit (None) for chart continuity

3. Update [src/ui/layout.py](src/ui/layout.py):
   - Add new health charts while preserving current simple tab layout
   - Keep JSON-safe NA serialization for ECharts

4. Add end-to-end fixture-based tests for each new metric path

**Complexity:** Medium-High | **Impact:** High | **Estimated effort:** 8-12 hours

---

### Priority 2: Enhanced Visualizations

**Why:** Current charts are functional but basic - adding interactivity and more visualization types would enhance analysis capabilities.

**Implementation:**

1. Add interactive chart features in [src/ui/layout.py](src/ui/layout.py):
   - Zoom/pan capabilities for trend charts
   - Click-through from charts to detailed workout lists
   - Tooltip enhancements showing more metrics
2. Add new chart types:
   - Scatter plots (distance vs pace, heart rate vs speed)
   - Heat maps (activity by day of week/hour)
   - Box plots for performance distribution

3. Personal records tracker:
   - Longest run, fastest pace, most elevation, etc.
   - Display as cards in Overview tab

4. Best-segments UX enhancements:
   - Add filters (distance subset, date range)
   - Optional route context links for segment entries
   - Optional activity-type extension beyond running

**Complexity:** Medium-High | **Impact:** Medium | **Estimated effort:** 8-12 hours

---

### Priority 3: Route Visualization

**Why:** The parser now merges split route files into a single route and retains source file metadata (`routeFiles`). Visualizing GPS routes would be valuable for runners/cyclists.

**Implementation:**

1. Extend [src/logic/export_parser.py](src/logic/export_parser.py):
   - Enhance GPX parsing (already has `_load_route()` method)
   - Store route data more efficiently

2. Add interactive map component in [src/ui/layout.py](src/ui/layout.py):
   - Use Leaflet.js or similar mapping library
   - Display routes on map with elevation profile
   - Show routes colored by pace/heart rate

3. Add route comparison features:
   - Overlay multiple routes
   - Compare performance on same route over time

**Complexity:** High | **Impact:** High | **Estimated effort:** 16-20 hours

---

### Priority 4: Advanced Analytics

**Why:** Transform from data viewer to true analytics tool with actionable insights.

**Implementation:**

1. Add statistical analysis methods to [src/logic/workout_manager.py](src/logic/workout_manager.py):
   - Trend analysis (improving/declining performance)
   - Seasonal patterns
   - Training load calculations
   - Recovery time recommendations

2. Create analytics dashboard tab:
   - Performance trends over time
   - Training zone analysis
   - Goal tracking and recommendations

3. Export enhanced reports:
   - PDF report generation with charts
   - Markdown summary reports

**Complexity:** Very High | **Impact:** Very High | **Estimated effort:** 20-24 hours

---

## Quick Wins (Low hanging fruit)

1. **Add unit preferences** - Let users choose km/mi, kg/lbs globally
2. **Add workout details table** - Sortable/filterable table view of all workouts
3. **Add search/filter** - Filter workouts by name, date, distance range
4. **Keyboard shortcuts** - Load file (Ctrl+O), Export (Ctrl+E)
5. **Error handling improvements** - Better error messages for corrupted files

---

## Verification Plan

After implementing each priority:

1. Run full test suite: `pytest --cov=src tests/`
2. Verify no linting/typing errors: `mypy src tests && pylint src tests`
3. Manual UI testing on multiple screen sizes
4. Test with real Apple Health export files of various sizes
5. Check code coverage remains >90%

---

## Decision Points

**Choose based on user needs:**

- **For casual users:** Priority 2 (Enhanced Visualizations) + Quick Wins
- **For data enthusiasts:** Priority 1 (Health Data) + Priority 2 (Enhanced Visualizations)
- **For athletes/coaches:** Priority 3 (Routes) + Priority 4 (Analytics)

The most logical progression is **Priority 1 → Priority 2 → Priority 3**, as each builds on the existing health + workout visualization foundation.
