import math


DEFAULT_GROUP_KEY = "__default__"


def get_sensor_multiplier(sensor):
    """Return a finite numeric multiplier, defaulting to one when omitted."""

    raw_multiplier = sensor.get("multiplier", 1)
    sensor_id = sensor.get("sensor_id", "<unknown>")

    if isinstance(raw_multiplier, bool):
        raise ValueError(
            f"Invalid multiplier {raw_multiplier!r} for '{sensor_id}'; "
            "expected a finite number."
        )

    try:
        multiplier = float(raw_multiplier)
    except (OverflowError, TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid multiplier {raw_multiplier!r} for '{sensor_id}'; "
            "expected a finite number."
        ) from error

    if not math.isfinite(multiplier):
        raise ValueError(
            f"Invalid multiplier {raw_multiplier!r} for '{sensor_id}'; "
            "expected a finite number."
        )

    return multiplier


def apply_sensor_multiplier(values, sensor):
    """Scale numeric sensor history values using validated configuration."""

    return values * get_sensor_multiplier(sensor)


def normalize_sensor_entries(sensor_entries, warn=print):
    """Flatten the legacy accidental '- sensors:' nesting into one sensor list."""

    normalized = []

    for entry in sensor_entries:
        if not isinstance(entry, dict):
            raise ValueError("Each sensors entry must be an object.")

        if "sensor_id" in entry:
            normalized.append(entry)
            continue

        nested_sensors = entry.get("sensors")
        if isinstance(nested_sensors, list):
            warn(
                "  WARNING: Found a nested sensors list; flattening it into "
                "the parent sensors list."
            )
            normalized.extend(normalize_sensor_entries(nested_sensors, warn))
            continue

        raise ValueError("Each sensors entry must contain sensor_id.")

    return normalized


def build_plot_groups(plot, warn=print):
    """Build ordered subplot groups and preserve legacy single-panel plots."""

    groups = {}
    group_order = []
    fallback_y_label = plot.get("y_label", "Value")
    sensors = normalize_sensor_entries(plot.get("sensors", []), warn)

    for sensor in sensors:
        sensor = dict(sensor)
        sensor["multiplier"] = get_sensor_multiplier(sensor)
        configured_group = sensor.get("plot_group")
        group_key = configured_group or DEFAULT_GROUP_KEY
        sensor_y_label = sensor.get("y_label")

        if group_key not in groups:
            group_order.append(group_key)
            groups[group_key] = {
                "title": configured_group,
                "y_label": sensor_y_label,
                "sensors": [],
            }
        elif sensor_y_label:
            if groups[group_key]["y_label"] is None:
                groups[group_key]["y_label"] = sensor_y_label
            elif sensor_y_label != groups[group_key]["y_label"]:
                warn(
                    f"  WARNING: plot group "
                    f"'{configured_group or 'default'}' uses multiple "
                    f"y_label values; keeping "
                    f"'{groups[group_key]['y_label']}'."
                )

        groups[group_key]["sensors"].append(sensor)

    plot_groups = [groups[group_key] for group_key in group_order]

    for group in plot_groups:
        group["y_label"] = group["y_label"] or fallback_y_label

        if len(plot_groups) > 1 and group["title"] is None:
            group["title"] = "Other"

    return plot_groups


def get_figure_size(group_count):
    """Keep legacy dimensions for one panel and add height for extra panels."""

    return (12, max(6, group_count * 4))
