
# DB History Plotter Multiline

A Home Assistant addon that queries your HA database and generates historical sensor plots as PNG images with support for multiple sensors and vertically stacked subplots, accessible via your HA dashboard.

This addon is a fork of [The-May/ha-addons – db_history_plotter](https://github.com/The-May/ha-addons/tree/main/db_history_plotter), extended with support for **multiple sensors per graph**, optional plot groups, configurable Y-axis position, and per-sensor colors.


## Disclaimer

This App/Addon was tested with SQLite was not tested and has been added with the help of AI. 
Feel free to report if it works or not.

## Installation

1. Add this HA Repo
   [![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Ftominowind%2Fdb_history_plotter_multiline)
2. In HA, go to **Settings → Add-ons → Add-on Store**
3. Find **DB History Plotter Multiline** and install it.
4. Profit.

## Configuration

All settings are edited via the addon's **Configuration** tab in the HA UI.

### Global Settings

| Option | Description |
|---|---|
| `db_type` | `mariadb` or `sqlite` |
| `db_host` | MariaDB hostname (default: `core-mariadb`) |
| `db_name` | Database name (default: `homeassistant`) |
| `db_user` | Database username |
| `db_password` | Database password |
| `timezone` | Use a Timezone (default: `Europe/Berlin`) |
| `plots` | List of plot configurations (see below) |

### Plot Configuration

Each entry in `plots` defines one image. Its sensors can share one graph or be assigned to named plot groups that are stacked vertically.

| Option | Description |
|---|---|
| `plot_id` | Unique identifier for this plot |
| `plot_title` | Title shown on the graph |
| `hours_back` | How many hours back to query (default: 24) |
| `y_label` | Label for Y-axis (e.g., "Temperature (°C)" or "Humidity (%)") |
| `y_axis_position` | Position of Y-axis: `left` or `right` (default: `left`) |
| `sensors` | List of sensors to plot on this graph (see below) |

### Sensor Configuration

Each sensor in a plot can have its own color and label.

| Option | Description |
|---|---|
| `sensor_id` | Home Assistant entity ID (e.g., `sensor.temperature`) |
| `label` | Label for this sensor in the legend (e.g., "Living Room Temperature") |
| `color` | Hex color code (e.g., `#FF0000` for red), or `null` for automatic color from palette |
| `plot_group` | Optional subplot name. Sensors with the same value share one panel. Omit it for the original single-panel behavior. |
| `y_label` | Optional Y-axis label for this sensor's plot group. The first configured value in a group is used. |
| `y_axis_position` | Optional `left` or `right`, overriding the plot-level axis position for this sensor. |

### Vertically Stacked Plot Groups

Set `plot_group` on each sensor to place related series in the same subplot. Groups are rendered in first-occurrence order, use aligned/shared time axes, and retain independent Y-axis scales. The exported PNG remains 12 × 6 inches for a single panel and grows vertically by four inches per panel for multi-panel plots.

Existing configurations need no changes: sensors without `plot_group` continue to render together as one graph. If grouped and ungrouped sensors are mixed, the ungrouped sensors appear in an `Other` panel.

In the visual Configuration editor:

1. Open the item under **Plots**.
2. Open each item under that plot's **Sensors** list.
3. Set **Plot group (subplot)**, **Y-axis label**, and **Y-axis position** in the sensor dialog.

To refresh the visual-editor schema, reload the app repository and then install version 2.1.1 or newer. The fields are optional so existing single-panel configurations remain valid.

#### Default Color Palette

If `color` is not specified or set to `null`, colors are automatically assigned from this palette:

1. Blue (#1f77b4)
2. Orange (#ff7f0e)
3. Green (#2ca02c)
4. Red (#d62728)
5. Purple (#9467bd)
6. Brown (#8c564b)
7. Pink (#e377c2)
8. Gray (#7f7f7f)
9. Olive (#bcbd22)
10. Cyan (#17becf)

### Example Configuration

```yaml
plots:
  - plot_id: "indoor_climate"
    plot_title: "Indoor Climate - Last 24 Hours"
    hours_back: 24
    y_label: "Value"
    y_axis_position: "left"
    sensors:
      - sensor_id: "sensor.living_room_temperature"
        label: "Living Room"
        color: "#FF6B6B"
        plot_group: "Temperatures"
        y_label: "Temperature (°C)"
      - sensor_id: "sensor.bedroom_temperature"
        label: "Bedroom"
        color: null
        plot_group: "Temperatures"
        y_label: "Temperature (°C)"
      - sensor_id: "sensor.living_room_humidity"
        label: "Living Room"
        color: "#4D96FF"
        plot_group: "Humidity"
        y_label: "Humidity (%)"
      - sensor_id: "sensor.bedroom_humidity"
        label: "Bedroom"
        color: null
        plot_group: "Humidity"
        y_label: "Humidity (%)"

  - plot_id: "outdoor_weather"
    plot_title: "Outdoor Weather - Last 48 Hours"
    hours_back: 48
    y_label: "Temperature (°C)"
    y_axis_position: "left"
    sensors:
      - sensor_id: "sensor.outdoor_temperature"
        label: "Temperature"
        color: null  # Automatic color

  - plot_id: "power_consumption"
    plot_title: "Power Usage - Last 7 Days"
    hours_back: 168
    y_label: "Power (W)"
    y_axis_position: "left"
    sensors:
      - sensor_id: "sensor.kitchen_power"
        label: "Kitchen"
        color: "#FFD700"
      - sensor_id: "sensor.bedroom_power"
        label: "Bedroom"
        color: "#4169E1"
      - sensor_id: "sensor.living_room_power"
        label: "Living Room"
        color: null
```
### Using the Images in a Dashboard

Images are saved to  /media/db_history_plotter/  inside the container, which maps to  /media/local/db_history_plotter/  in HA's media server.

Each image is named after its  plot_id  from the configuration.

### Add a Picture card to your dashboard and set the URL to:
```
/media/local/db_history_plotter/<plot_id>.png
```
### For example, with the example configuration above:
```
/media/local/db_history_plotter/indoor_climate.png
/media/local/db_history_plotter/outdoor_weather.png
/media/local/db_history_plotter/power_consumption.png
```
### Using the Images with Telegram

The pictures can be used with Telegram automation.

### Using the Images with the HA Companion App

The pictures can be used with the HA Companion App (Push Message).

### Changelog

v2.1.1

• Added English and Slovak visual-editor labels for subplot fields
• Documented how to edit subplot settings in the sensor dialog

v2.1.0

• Vertically stacked plot groups in one exported image
• Shared time axis with independent Y-axis scales per group
• Adaptive image height and per-panel legends
• Existing single-panel configurations remain supported

v2.0.0

• Breaking Change: Configuration structure changed from  sensors  to  plots 
• Multiline graph support: multiple sensors per plot
• Customizable colors per sensor (or automatic from palette)
• Configurable Y-axis position (left/right)
• Improved legend display
• Better performance with multiple sensors

v1.1.0

• Initial release
• Single sensor per plot support
