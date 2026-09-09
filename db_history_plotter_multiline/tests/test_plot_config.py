import json
import unittest
from pathlib import Path

from db_history_plotter_multiline.plot_config import (
    build_plot_groups,
    get_figure_size,
)

APP_DIR = Path(__file__).resolve().parents[1]


class PlotConfigTest(unittest.TestCase):
    def test_legacy_sensors_remain_in_one_panel(self):
        plot = {
            "y_label": "Value",
            "sensors": [
                {"sensor_id": "sensor.one"},
                {"sensor_id": "sensor.two"},
            ],
        }

        groups = build_plot_groups(plot)

        self.assertEqual(1, len(groups))
        self.assertIsNone(groups[0]["title"])
        self.assertEqual("Value", groups[0]["y_label"])
        self.assertEqual(
            ["sensor.one", "sensor.two"],
            [sensor["sensor_id"] for sensor in groups[0]["sensors"]],
        )

    def test_groups_follow_first_occurrence_order(self):
        plot = {
            "y_label": "Hodnota",
            "sensors": [
                {
                    "sensor_id": "sensor.outdoor_temperature",
                    "plot_group": "Teplota",
                    "y_label": "Stupne Celzia",
                },
                {
                    "sensor_id": "sensor.bedroom_temperature",
                    "plot_group": "Teplota",
                    "y_label": "Stupne Celzia",
                },
                {
                    "sensor_id": "sensor.outdoor_humidity",
                    "plot_group": "Vlhkosť",
                    "y_label": "Relatívna vlhkosť (%)",
                },
                {
                    "sensor_id": "sensor.bedroom_humidity",
                    "plot_group": "Vlhkosť",
                    "y_label": "Relatívna vlhkosť (%)",
                },
            ],
        }

        groups = build_plot_groups(plot)

        self.assertEqual(["Teplota", "Vlhkosť"], [
            group["title"] for group in groups
        ])
        self.assertEqual(
            ["sensor.outdoor_temperature", "sensor.bedroom_temperature"],
            [sensor["sensor_id"] for sensor in groups[0]["sensors"]],
        )
        self.assertEqual("Relatívna vlhkosť (%)", groups[1]["y_label"])
        self.assertEqual((12, 8), get_figure_size(len(groups)))

    def test_accidentally_nested_sensor_list_is_flattened(self):
        warnings = []
        plot = {
            "sensors": [
                {
                    "sensor_id": "sensor.temperature",
                    "plot_group": "Teplota",
                },
                {
                    "sensors": [
                        {
                            "sensor_id": "sensor.humidity",
                            "plot_group": "Vlhkosť",
                        }
                    ]
                },
            ]
        }

        groups = build_plot_groups(plot, warnings.append)

        self.assertEqual(["Teplota", "Vlhkosť"], [
            group["title"] for group in groups
        ])
        self.assertEqual(1, len(warnings))

    def test_visual_editor_schema_contains_optional_sensor_fields(self):
        config = json.loads((APP_DIR / "config.json").read_text(encoding="utf-8"))
        sensor_schema = config["schema"]["plots"][0]["sensors"][0]

        self.assertEqual("str?", sensor_schema["plot_group"])
        self.assertEqual("str?", sensor_schema["y_label"])
        self.assertEqual(
            "list(left|right)?",
            sensor_schema["y_axis_position"],
        )


if __name__ == "__main__":
    unittest.main()
