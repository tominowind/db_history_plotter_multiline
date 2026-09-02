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
with open("/data/options.json") as f:
    OPT = json.load(f)

DB_TYPE       = OPT["db_type"]
DB_HOST       = OPT["db_host"]
DB_NAME       = OPT["db_name"]
DB_USER       = OPT["db_user"]
DB_PASSWORD   = OPT["db_password"]
SQLITE_FILE   = OPT["sqlite_file"]
TIMEZONE_NAME = OPT.get("timezone", "UTC")
PLOTS         = OPT.get("plots", [])

# Paths inside the container
CSV_DIR   = "/tmp/db_history_plotter"
IMAGE_DIR = "/media/db_history_plotter"

TZ       = ZoneInfo(TIMEZONE_NAME)
TZ_LABEL = TIMEZONE_NAME

os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)


# ============================================================================
# Color Palette
# ============================================================================

DEFAULT_COLOR_PALETTE = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
    "#bcbd22",  # olive
    "#17becf",  # cyan
]


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

print(f"{'─' * 60}")
print(f"  {run_start.strftime('%Y-%m-%d %H:%M:%S')} {TZ_LABEL}")
print(
    f"  DB:       {DB_TYPE}"
    f"{' @ ' + DB_HOST if DB_TYPE == 'mariadb' else ''}"
)
print(f"  Plots:    {len(PLOTS)}")
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
# Per-plot loop
# ============================================================================

processed_plots = 0

for plot_idx, plot_config in enumerate(PLOTS):

    plot_id        = plot_config.get("plot_id", f"plot_{plot_idx}")
    plot_title     = plot_config.get("plot_title", f"Plot {plot_idx}")
    hours_back     = int(plot_config.get("hours_back", 24))
    y_label        = plot_config.get("y_label", "Value")
    y_axis_position = plot_config.get("y_axis_position", "left")
    sensors_config = plot_config.get("sensors", [])

    image_file = os.path.join(
        IMAGE_DIR,
        f"{plot_idx}.png"
    )

    print()
    print(
        f"[Plot {plot_idx}] {plot_id} "
        f"({len(sensors_config)} sensor(s), last {hours_back}h)"
    )

    if not sensors_config:
        print(f"[Plot {plot_idx}] No sensors configured, skipping.")
        continue

    # Fetch data for all sensors in this plot
    all_dataframes = []
    all_labels = []
    all_colors = []

    for sensor_idx, sensor_config in enumerate(sensors_config):

        sensor_id = sensor_config.get("sensor_id")
        label     = sensor_config.get("label", sensor_id)
        color     = sensor_config.get("color")

        if not color:
            # Use default color from palette
            color = DEFAULT_COLOR_PALETTE[
                (sensor_idx + plot_idx) % len(DEFAULT_COLOR_PALETTE)
            ]

        print(f"  [{sensor_idx}] {sensor_id} → {label} (color: {color})")

        csv_file = os.path.join(
            CSV_DIR,
            f"plot_{plot_idx}_sensor_{sensor_idx}.csv"
        )

        # Build query
        if DB_TYPE == "sqlite":

            sql_query = f"""
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

        # Fetch
        t_query = time.monotonic()

        try:

            cursor = conn.cursor()
            cursor.execute(sql_query, sql_params)
            rows = cursor.fetchall()
            cursor.close()

        except Exception as e:

            print(
                f"  [{sensor_idx}] ERROR querying "
                f"{sensor_id}: {e}"
            )
            continue

        elapsed_ms = (time.monotonic() - t_query) * 1000

        print(
            f"  [{sensor_idx}] Fetched {len(rows)} rows "
            f"({elapsed_ms:.0f} ms)"
        )

        if not rows:
            print(
                f"  [{sensor_idx}] No data for {sensor_id}, "
                f"skipping this sensor."
            )
            continue

        # Write CSV
        with open(csv_file, "w", newline="") as f:
            csv.writer(f).writerows(rows)

        time.sleep(0.2)

        # Load DataFrame
        df = pd.read_csv(
            csv_file,
            names=[
                "timestamp",
                "value",
                "entity_id"
            ],
            dtype={
                "timestamp": object,
                "value": object,
                "entity_id": object,
            },
        )

        # Convert timestamp/value to numeric
        df["timestamp"] = pd.to_numeric(
            df["timestamp"],
            errors="coerce"
        )

        df["value"] = pd.to_numeric(
            df["value"],
            errors="coerce"
        )

        df = df.dropna(
            subset=[
                "timestamp",
                "value"
            ]
        )

        # Convert Unix timestamp UTC → configured timezone
        df["timestamp"] = pd.to_datetime(
            df["timestamp"].astype("float64"),
            unit="s",
            utc=True,
            errors="raise"
        ).dt.tz_convert(TZ)

        all_dataframes.append(df)
        all_labels.append(label)
        all_colors.append(color)

    # Plot all sensors
    if not all_dataframes:
        print(
            f"[Plot {plot_idx}] No valid data for any sensor, "
            f"skipping plot."
        )
        continue

    current_time_local = datetime.now(TZ)

    t_plot = time.monotonic()

    plt.figure(
        figsize=(14, 7)
    )

    for df, label, color in zip(all_dataframes, all_labels, all_colors):

        plt.plot(
            df["timestamp"],
            df["value"],
            marker="o",
            linestyle="-",
            linewidth=2,
            label=label,
            color=color,
        )

    plt.title(
        f"{plot_title}\n"
        f"Generated: "
        f"{current_time_local.strftime('%Y-%m-%d %H:%M:%S')} "
        f"{TZ_LABEL}"
    )

    plt.xlabel(
        f"Timestamp ({TZ_LABEL})"
    )

    plt.ylabel(y_label)

    plt.legend(loc="best")

    plt.grid(True, alpha=0.3)

    plt.xticks(
        rotation=45
    )

    plt.tight_layout()

    plt.savefig(
        image_file,
        format="png",
        dpi=100
    )

    plt.close()

    plot_ms = (time.monotonic() - t_plot) * 1000

    print(
        f"[Plot {plot_idx}] Saved → "
        f"{image_file} "
        f"({plot_ms:.0f} ms)"
    )

    processed_plots += 1


# ============================================================================
# Close database
# ============================================================================

conn.close()


# ============================================================================
# Summary
# ============================================================================

run_end = datetime.now(TZ)

elapsed_total = (
    run_end - run_start
).total_seconds()

print()
print(f"{'─' * 60}")
print(
    f"  Done. "
    f"{processed_plots}/{len(PLOTS)} plot(s) "
    f"processed in {elapsed_total:.1f}s"
)
print(f"{'─' * 60}")
print()