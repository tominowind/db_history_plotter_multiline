
import os
import csv
import json
import time
import matplotlib
matplotlib.use("Agg")   # headless backend — no display needed
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, UTC
from zoneinfo import ZoneInfo


# ============================================================================
# Configuration
# ============================================================================

# Read config from Home Assistant App Configuration
OPTIONS_FILE = os.environ.get("OPTIONS_FILE", "/data/options.json")

with open(OPTIONS_FILE) as f:
    OPT = json.load(f)

DB_TYPE       = OPT["db_type"]
DB_HOST       = OPT["db_host"]
DB_NAME       = OPT["db_name"]
DB_USER       = OPT["db_user"]
DB_PASSWORD   = OPT["db_password"]
SQLITE_FILE   = OPT["sqlite_file"]
TIMEZONE_NAME = OPT.get("timezone", "UTC")
PLOTS         = OPT["plots"]

# Paths inside the container
CSV_DIR   = os.environ.get("CSV_DIR", "/tmp/db_history_plotter")
IMAGE_DIR = os.environ.get("IMAGE_DIR", "/media/db_history_plotter")

TZ       = ZoneInfo(TIMEZONE_NAME)
TZ_LABEL = TIMEZONE_NAME

os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)


# ============================================================================
# Minimal filesystem / mount diagnostics
# ============================================================================

print()
print(f"{'─' * 60}")
print("  Filesystem / mount diagnostics")
print(f"{'─' * 60}")

print(f"[FS] Current working directory: {os.getcwd()}")


def check_directory(path):
    """Basic access check for an expected mounted directory."""

    print(f"\n[FS] Checking: {path}")

    if not os.path.exists(path):
        print("[FS]   EXISTS: NO")
        return

    if not os.path.isdir(path):
        print("[FS]   EXISTS: YES")
        print("[FS]   DIRECTORY: NO")
        return

    try:
        entries = os.listdir(path)

        print("[FS]   EXISTS: YES")
        print("[FS]   DIRECTORY: YES")
        print("[FS]   ACCESS: YES")
        print(f"[FS]   ENTRIES: {len(entries)}")

    except Exception as e:
        print("[FS]   EXISTS: YES")
        print("[FS]   DIRECTORY: YES")
        print(f"[FS]   ACCESS: NO ({e})")


check_directory("/data")
check_directory("/homeassistant")
check_directory("/media")


# Check configured SQLite path
sqlite_path = os.path.abspath(SQLITE_FILE)

print()
print("[FS] SQLite configuration:")
print(f"[FS]   Configured path: {SQLITE_FILE}")
print(f"[FS]   Absolute path:   {sqlite_path}")
print(f"[FS]   Exists:          {os.path.exists(sqlite_path)}")
print(f"[FS]   Is file:         {os.path.isfile(sqlite_path)}")

if os.path.isfile(sqlite_path):
    print(
        f"[FS]   Size:            "
        f"{os.path.getsize(sqlite_path):,} bytes"
    )

print(f"{'─' * 60}")
print()


# ============================================================================
# Startup log
# ============================================================================

run_start = datetime.now(TZ)

total_sensors = sum(len(p.get("sensors", [])) for p in PLOTS)

print(f"{'─' * 60}")
print(f"  {run_start.strftime('%Y-%m-%d %H:%M:%S')} {TZ_LABEL}")
print(
    f"  DB:       {DB_TYPE}"
    f"{'  @ ' + DB_HOST if DB_TYPE == 'mariadb' else ''}"
)
print(f"  Plots:    {len(PLOTS)}")
print(f"  Sensors:  {total_sensors}")
print(f"{'─' * 60}")


# ============================================================================
# Database connection
# ============================================================================

try:

    if DB_TYPE == "sqlite":

        import sqlite3

        if not os.path.isfile(SQLITE_FILE):
            raise FileNotFoundError(
                f"SQLite database does not exist: {SQLITE_FILE}"
            )

        db_size = os.path.getsize(SQLITE_FILE)

        if db_size == 0:
            raise RuntimeError(
                f"SQLite database is empty (0 bytes): {SQLITE_FILE}"
            )

        conn = sqlite3.connect(SQLITE_FILE)

        print(
            f"[DB] Connected to SQLite: "
            f"{SQLITE_FILE} ({db_size:,} bytes)"
        )

    elif DB_TYPE == "mariadb":

        import MySQLdb

        conn = MySQLdb.connect(
            host=DB_HOST,
            user=DB_USER,
            passwd=DB_PASSWORD,
            db=DB_NAME,
        )

        print(
            f"[DB] Connected to MariaDB: "
            f"{DB_USER}@{DB_HOST}/{DB_NAME}"
        )

    else:

        raise ValueError(
            f"Unknown DB_TYPE '{DB_TYPE}'. "
            f"Choose 'sqlite' or 'mariadb'."
        )

except Exception as e:

    print(f"[DB] ERROR: {e}")
    raise SystemExit(1)


# ============================================================================
# Helper: fetch history for one sensor
# ============================================================================

def fetch_sensor_history(sensor_id, hours_back, csv_path):
    """Query DB for one sensor's history and return a cleaned DataFrame."""

    if DB_TYPE == "sqlite":

        sql_query = """
        SELECT
            states.last_updated_ts,
            states.state,
            states_meta.entity_id
        FROM states
        JOIN states_meta
            ON states.metadata_id = states_meta.metadata_id
        WHERE states_meta.entity_id = ?
          AND states.state NOT IN ('unavailable', 'unknown')
          AND states.last_updated_ts >=
              strftime('%s', 'now', ?)
        ORDER BY states.state_id ASC;
        """

        sql_params = (
            sensor_id,
            f"-{hours_back} hours",
        )

    else:

        cutoff_ts = (
            datetime.now(UTC).timestamp()
            - hours_back * 3600
        )

        sql_query = """
        SELECT
            states.last_updated_ts,
            states.state,
            states_meta.entity_id
        FROM states
        JOIN states_meta
            ON states.metadata_id = states_meta.metadata_id
        WHERE states_meta.entity_id = %s
          AND states.state NOT IN ('unavailable', 'unknown')
          AND states.last_updated_ts >= %s
        ORDER BY states.state_id ASC;
        """

        sql_params = (
            sensor_id,
            cutoff_ts,
        )

    t_query = time.monotonic()

    try:
        cursor = conn.cursor()
        cursor.execute(sql_query, sql_params)
        rows = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"    ERROR querying {sensor_id}: {e}")
        return None

    elapsed_ms = (time.monotonic() - t_query) * 1000
    print(f"    Fetched {len(rows)} rows ({elapsed_ms:.0f} ms)")

    if not rows:
        print(f"    No data for {sensor_id}, skipping.")
        return None

    with open(csv_path, "w", newline="") as f:
        csv.writer(f).writerows(rows)

    df = pd.read_csv(
        csv_path,
        names=["timestamp", "value", "entity_id"],
        dtype={
            "timestamp": object,
            "value": object,
            "entity_id": object,
        },
    )

    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["timestamp", "value"])

    df["timestamp"] = pd.to_datetime(
        df["timestamp"].astype("float64"),
        unit="s",
        utc=True,
        errors="raise"
    ).dt.tz_convert(TZ)

    return df


# ============================================================================
# Helpers: organize sensors into vertically stacked plot groups
# ============================================================================

def build_plot_groups(plot):
    """Return ordered subplot groups while preserving legacy plot behavior."""

    groups = {}
    fallback_y_label = plot.get("y_label", "Value")

    for sensor in plot.get("sensors", []):
        configured_group = sensor.get("plot_group")
        group_key = configured_group or "__default__"
        sensor_y_label = sensor.get("y_label")

        if group_key not in groups:
            groups[group_key] = {
                "title": configured_group,
                "y_label": sensor_y_label,
                "sensors": [],
            }
        elif sensor_y_label:
            if groups[group_key]["y_label"] is None:
                groups[group_key]["y_label"] = sensor_y_label
            elif sensor_y_label != groups[group_key]["y_label"]:
                print(
                    f"  WARNING: plot group "
                    f"'{configured_group or 'default'}' uses multiple "
                    f"y_label values; keeping "
                    f"'{groups[group_key]['y_label']}'."
                )

        groups[group_key]["sensors"].append(sensor)

    plot_groups = list(groups.values())

    for group in plot_groups:
        group["y_label"] = group["y_label"] or fallback_y_label

        if len(plot_groups) > 1:
            if group["title"] is None:
                group["title"] = "Other"

    return plot_groups


def get_figure_size(group_count):
    """Keep legacy dimensions for one panel and add height for each extra panel."""

    return (12, max(6, group_count * 4))


# ============================================================================
# Per-plot loop
# ============================================================================

processed_plots = 0

for p_idx, plot in enumerate(PLOTS):

    plot_id       = plot.get("plot_id", f"plot_{p_idx}")
    plot_title    = plot.get("plot_title", plot_id)
    hours_back    = int(plot.get("hours_back", 24))
    y_axis_pos    = plot.get("y_axis_position", "left")
    plot_groups   = build_plot_groups(plot)
    sensor_count  = sum(len(group["sensors"]) for group in plot_groups)

    image_file = os.path.join(IMAGE_DIR, f"{plot_id}.png")

    print()
    print(
        f"[{plot_id}] '{plot_title}' — {sensor_count} sensor(s), "
        f"{len(plot_groups)} panel(s), last {hours_back}h"
    )

    if not plot_groups:
        print(f"[{plot_id}] No sensors configured, skipping plot.")
        continue

    fig, axes = plt.subplots(
        nrows=len(plot_groups),
        ncols=1,
        figsize=get_figure_size(len(plot_groups)),
        sharex=len(plot_groups) > 1,
        squeeze=False,
    )
    axes = axes[:, 0]

    plotted_any = False
    sensor_index = 0

    for group_index, (group, ax_left) in enumerate(zip(plot_groups, axes)):
        ax_right = None
        lines_for_legend = []
        group_plotted = False
        left_plotted = False
        right_plotted = False

        for sensor in group["sensors"]:
            sensor_id = sensor["sensor_id"]
            label     = sensor.get("label", sensor_id)
            color     = sensor.get("color") or None
            position  = sensor.get("y_axis_position", y_axis_pos)

            csv_file = os.path.join(
                CSV_DIR,
                f"{plot_id}_{sensor_index}.csv",
            )

            print(
                f"  [{group_index}:{sensor_index}] "
                f"{sensor_id} ({label})"
            )

            df = fetch_sensor_history(sensor_id, hours_back, csv_file)
            sensor_index += 1

            if df is None or df.empty:
                continue

            # Keep this because the original working implementation
            # used a short delay before reading the CSV.
            time.sleep(0.5)

            target_ax = ax_left

            if position == "right":
                if ax_right is None:
                    ax_right = ax_left.twinx()
                target_ax = ax_right
                right_plotted = True
            else:
                left_plotted = True

            (line,) = target_ax.plot(
                df["timestamp"],
                df["value"],
                marker="o",
                linestyle="-",
                linewidth=2,
                label=label,
                color=color,
            )

            lines_for_legend.append(line)
            group_plotted = True
            plotted_any = True

            v_min = df["value"].min()
            v_max = df["value"].max()

            print(
                f"      Values: min={v_min:.2f}  max={v_max:.2f}  "
                f"points={len(df)}"
            )

        if group["title"]:
            ax_left.set_title(group["title"], fontsize=11)

        if left_plotted or not right_plotted:
            ax_left.set_ylabel(group["y_label"])
        ax_left.grid(True)

        if group_index == len(plot_groups) - 1:
            ax_left.set_xlabel(f"Timestamp ({TZ_LABEL})")

        if right_plotted:
            ax_right.set_ylabel(f"{group['y_label']} (right axis)")

        if lines_for_legend:
            ax_left.legend(
                handles=lines_for_legend,
                loc="best",
                ncols=min(3, len(lines_for_legend)),
                fontsize="small",
            )
        elif not group_plotted:
            ax_left.text(
                0.5,
                0.5,
                "No data available",
                ha="center",
                va="center",
                transform=ax_left.transAxes,
            )

    if not plotted_any:
        print(f"[{plot_id}] No data for any sensor, skipping plot.")
        plt.close(fig)
        continue

    current_time_local = datetime.now(TZ)

    generated_title = (
        f"{plot_title}\n"
        f"Generated: "
        f"{current_time_local.strftime('%Y-%m-%d %H:%M:%S')} {TZ_LABEL}"
    )

    if len(plot_groups) == 1 and plot_groups[0]["title"] is None:
        axes[0].set_title(generated_title)
    else:
        fig.suptitle(generated_title)

    for label_tick in axes[-1].get_xticklabels():
        label_tick.set_rotation(45)
        label_tick.set_horizontalalignment("right")

    fig.tight_layout(rect=(0, 0, 1, 0.95))

    t_plot = time.monotonic()
    fig.savefig(image_file, format="png")
    plt.close(fig)
    plot_ms = (time.monotonic() - t_plot) * 1000

    print(f"[{plot_id}] Saved → {image_file} ({plot_ms:.0f} ms)")

    processed_plots += 1


# ============================================================================
# Close database
# ============================================================================

conn.close()


# ============================================================================
# Summary
# ============================================================================

run_end = datetime.now(TZ)
elapsed_total = (run_end - run_start).total_seconds()

print()
print(f"{'─' * 60}")
print(
    f"  Done. {processed_plots}/{len(PLOTS)} plot(s) processed "
    f"in {elapsed_total:.1f}s"
)
print(f"{'─' * 60}")
print()
