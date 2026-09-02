# DB History Plotter Multiline

A Home Assistant addon that queries your HA database and generates historical sensor plots as PNG images with support for multiple sensors per graph, accessible via your HA dashboard.

Most inspiration came from https://community.home-assistant.io/t/request-graph-image-from-sensor-history-over-telegram BUT the use-case was not suitable 
and I did not want a custom integration that might break something and rather a "standalone" solution that does not harm anything at all

## Disclaimer

This App/Addon was tested with MariaDB. SQLite was not tested and has been added with the help of AI. 
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

Each entry in `plots` defines one graph image. Each plot can contain one or more sensors.

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
  - plot_id: "temperature_humidity"
    plot_title: "Temperature & Humidity - Last 24 Hours"
    hours_back: 24
    y_label: "Value"
    y_axis_position: "left"
    sensors:
      - sensor_id: "sensor.living_room_temperature"
        label: "Temperature (°C)"
        color: "#FF6B6B"
      - sensor_id: "sensor.living_room_humidity"
        label: "Humidity (%)"
        color: null  # Will use automatic color (Orange)

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

## Using the Images in a Dashboard

Images are saved to `/media/db_history_plotter/` inside the container, which maps to `/media/local/db_history_plotter/` in HA's media server.

Add a **Picture** card to your dashboard and set the URL to:

```
/media/local/db_history_plotter/0.png   ← first plot
/media/local/db_history_plotter/1.png   ← second plot
/media/local/db_history_plotter/2.png   ← third plot
```

The image index matches the order of entries in your `plots` config list.

## Using the Images with Telegram

The pictures can be used with Telegram automation.

## Using the Images with the HA Companion App

The pictures can be used with the HA Companion App (Push Message).

## Changelog

### v2.0.0
- **Breaking Change**: Configuration structure changed from `sensors` to `plots`
- Multiline graph support: multiple sensors per plot
- Customizable colors per sensor (or automatic from palette)
- Configurable Y-axis position (left/right)
- Improved legend display
- Better performance with multiple sensors

### v1.1.0
- Initial release
- Single sensor per plot support