import json
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]


class VisualEditorSchemaTest(unittest.TestCase):
    def test_all_subplot_sensor_fields_are_optional_and_editable(self):
        config = json.loads((APP_DIR / "config.json").read_text(encoding="utf-8"))
        sensor_schema = config["schema"]["plots"][0]["sensors"][0]

        self.assertEqual("str?", sensor_schema["plot_group"])
        self.assertEqual("str?", sensor_schema["y_label"])
        self.assertEqual(
            "list(left|right)?",
            sensor_schema["y_axis_position"],
        )

    def test_legacy_sensor_fields_remain_unchanged(self):
        config = json.loads((APP_DIR / "config.json").read_text(encoding="utf-8"))
        sensor_schema = config["schema"]["plots"][0]["sensors"][0]

        self.assertEqual("str", sensor_schema["sensor_id"])
        self.assertEqual("str", sensor_schema["label"])
        self.assertEqual("str?", sensor_schema["color"])

    def test_translations_cover_all_sensor_editor_fields(self):
        sensor_fields = {
            "sensor_id",
            "label",
            "color",
            "plot_group",
            "y_label",
            "y_axis_position",
        }

        for language in ("en", "sk"):
            with self.subTest(language=language):
                translation = (
                    APP_DIR / "translations" / f"{language}.yaml"
                ).read_text(
                    encoding="utf-8"
                )

                for field in sensor_fields:
                    self.assertIn(f"\n  {field}:\n", translation)


if __name__ == "__main__":
    unittest.main()
