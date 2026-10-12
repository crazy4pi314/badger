import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


PATH = Path(__file__).resolve().parents[1] / "badge" / "apps" / "fork_flora" / "__init__.py"
spec = importlib.util.spec_from_file_location("fork_flora_test", PATH)
flora = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"badgeware": types.SimpleNamespace(State=object)}):
    spec.loader.exec_module(flora)


class GardenTests(unittest.TestCase):
    def test_region_catalog(self):
        garden = flora.Garden()
        self.assertEqual(len(garden.shelf()), 12)
        for region, _ in flora.REGIONS:
            garden.choose_region(region)
            self.assertTrue(garden.shelf())
            self.assertTrue(all(s[1] == region for s in garden.shelf()))

    def test_growth_is_bounded_and_identity_stable(self):
        garden = flora.Garden()
        record = garden.new_seed("poppy")
        garden.plant(record, 2)
        for _ in range(10):
            garden.care(2)
        self.assertEqual(garden.data["tray"][2]["stage"], 3)
        self.assertFalse(garden.care(2))
        self.assertFalse(garden.care(0))
        self.assertEqual(garden.data["tray"][2]["seed"], record["seed"])

    def test_tray_slots_and_move_to_garden(self):
        garden = flora.Garden()
        self.assertEqual(garden.open_slot(3), 3)
        garden.plant(garden.new_seed("poppy"), 3)
        self.assertEqual(garden.open_slot(3), 0)
        moved, message = garden.move_to_garden(3)
        self.assertFalse(moved)
        self.assertIn("blooming", message)
        for _ in range(3):
            garden.care(3)
        record = flora.seed_record(garden.data["tray"][3])
        moved, message = garden.move_to_garden(3)
        self.assertTrue(moved)
        self.assertIsNone(garden.data["tray"][3])
        self.assertEqual(garden.data["garden"], [record])
        self.assertFalse(garden.move_to_garden(3)[0])
        for slot in range(flora.TRAY_SIZE):
            garden.plant(garden.new_seed("lotus"), slot)
        self.assertIsNone(garden.open_slot(0))

    def test_garden_limit(self):
        garden = flora.Garden()
        garden.data["garden"] = [garden.new_seed("poppy") for _ in range(flora.GARDEN_LIMIT)]
        garden.plant(garden.new_seed("lotus"), 0)
        garden.data["tray"][0]["stage"] = 3
        moved, message = garden.move_to_garden(0)
        self.assertFalse(moved)
        self.assertIn("full", message)
        self.assertIsNotNone(garden.data["tray"][0])

    def test_schema_1_migrates_plant_into_tray(self):
        plant = {"species_id": "poppy", "seed": 5, "recipe": 1, "stage": 2}
        old = {"schema": 1, "region_id": "europe", "plant": plant,
               "seed_inbox": [], "next_seed": 9}
        data = flora.Garden(old).data
        self.assertEqual(data["schema"], flora.SCHEMA)
        self.assertEqual(data["tray"][0], plant)
        self.assertEqual(data["tray"][1:], [None] * (flora.TRAY_SIZE - 1))
        self.assertEqual(data["garden"], [])
        self.assertNotIn("plant", data)
        old["plant"] = None
        self.assertEqual(flora.Garden(old).data["tray"], [None] * flora.TRAY_SIZE)

    def test_meadow_layout_is_deterministic_and_back_to_front(self):
        garden = flora.Garden()
        flowers = [garden.new_seed(s[0]) for s in flora.SPECIES] * 2
        layout = flora.meadow_layout(flowers, 160, 120, 1)
        self.assertEqual(layout, flora.meadow_layout(flowers, 160, 120, 1))
        self.assertEqual(len(layout), len(flowers))
        baselines = [baseline for _, _, baseline in layout]
        self.assertEqual(baselines, sorted(baselines))
        for _, x, baseline in layout:
            self.assertTrue(0 <= x <= 160 - 32)
            self.assertTrue(48 <= baseline <= 120)

    def test_recipes_deterministic_and_bounded(self):
        varied = set()
        for species in flora.SPECIES:
            for seed in (0, 1, 2, 42, flora.MAX_SEED):
                for stage in range(4):
                    recipe = flora.plant_recipe(species[0], seed, stage)
                    self.assertEqual(recipe, flora.plant_recipe(species[0], seed, stage))
                    self.assertLessEqual(len(recipe), 50)
                    for x, y, w, h, pen in recipe:
                        self.assertGreaterEqual(x, 0)
                        self.assertGreaterEqual(y, 0)
                        self.assertLessEqual(x + w, 32)
                        self.assertLessEqual(y + h, 32)
                        self.assertIn(pen, range(5))
                if species[0] == "poppy":
                    varied.add(flora.plant_recipe(species[0], seed, 3))
        self.assertGreater(len(varied), 1)

    def test_inbox_full_duplicate_and_plant(self):
        garden = flora.Garden()
        record = garden.new_seed("poppy")
        garden.receive(record)
        self.assertIn("Already", garden.receive(record))
        for _ in range(5):
            garden.receive(garden.new_seed("dahlia"))
        self.assertEqual(len(garden.data["seed_inbox"]), 6)
        self.assertIn("full", garden.receive(garden.new_seed("lotus")))
        garden.plant_inbox(0, 4)
        self.assertEqual(len(garden.data["seed_inbox"]), 5)
        self.assertEqual(garden.data["tray"][4]["seed"], record["seed"])
        self.assertEqual(garden.data["tray"][4]["stage"], 0)

    def test_invalid_state_and_payload(self):
        for field, value in (("schema", 9), ("region_id", "Mars"),
                             ("next_seed", True), ("seed_inbox", [None]),
                             ("tray", [None]), ("tray", [{"species_id": "poppy"}] * 6),
                             ("garden", [None]), ("garden", None)):
            data = flora.defaults()
            data[field] = value
            with self.assertRaises(ValueError):
                flora.validate_state(data)
        garden = flora.Garden()
        for record in (None, {"species_id": "unknown", "seed": 1, "recipe": 1},
                       {"species_id": "poppy", "seed": True, "recipe": 1},
                       {"species_id": "poppy", "seed": 1, "recipe": 2}):
            with self.assertRaises(ValueError):
                garden.receive(record)

    def test_state_round_trip(self):
        garden = flora.Garden()
        garden.choose_region("europe")
        garden.plant(garden.new_seed("cornflower"), 1)
        garden.care(1)
        garden.data["garden"].append(garden.new_seed("poppy"))
        saved = flora.json.loads(flora.json.dumps(garden.data))
        self.assertEqual(flora.Garden(saved).data, garden.data)

    def test_missing_save_does_not_depend_on_errno(self):
        with patch.object(flora.os, "listdir", return_value=[]):
            with patch("builtins.open") as opened:
                garden, message = flora.load_garden()
                opened.assert_not_called()
        self.assertEqual(garden.data, flora.defaults())
        self.assertEqual(message, "")

    def test_unreadable_save_is_reported(self):
        with patch.object(flora.os, "listdir", side_effect=OSError(13)):
            _, message = flora.load_garden()
        self.assertIn("not saved", message)

    def test_remote_field_types(self):
        for species, recipe in (([], 1), ("poppy", True), ({}, 1)):
            self.assertFalse(flora.valid_seed(
                {"species_id": species, "seed": 1, "recipe": recipe}))


class AppTests(unittest.TestCase):
    def setUp(self):
        self.garden = flora.Garden()
        self.app = flora.App(self.garden)

    def tray(self):
        return self.garden.data["tray"]

    def act(self, label):
        self.app.cursor = self.app.menu.index(label)
        self.app.handle("select")

    def plant_first(self):
        for _ in range(4):
            self.app.handle("select")
        self.assertEqual(self.app.scene, "tray")

    def plant_new(self):
        self.act("New plant")
        self.app.handle("select")
        self.app.handle("select")

    def finish_care(self):
        self.act("Care")
        self.assertEqual(self.app.scene, "care")
        for _ in range(flora.CARE_MS // 100):
            self.app.tick(100)
        self.app.handle("select")

    def test_onboarding_and_care(self):
        self.plant_first()
        self.assertEqual(self.app.slot, 0)
        self.app.handle("select")
        self.assertEqual(self.app.scene, "care")
        self.assertEqual(self.tray()[0]["stage"], 0)
        for _ in range(flora.CARE_MS // 100 - 1):
            self.app.tick(100)
        self.assertEqual(self.tray()[0]["stage"], 0)
        self.app.tick(100)
        self.assertEqual(self.app.scene, "tray")
        self.assertEqual(self.tray()[0]["stage"], 1)
        self.assertIn("Sprout", self.app.message)
        self.assertTrue(self.app.dirty)

    def test_care_frame_clamp_and_cancel(self):
        self.plant_first()
        self.app.handle("select")
        self.app.tick(flora.CARE_MS)
        self.assertEqual(self.app.care_ms, flora.MAX_FRAME_MS)
        self.app.handle("next")
        self.assertEqual(self.app.scene, "care")
        self.app.handle("down")
        self.assertEqual(self.app.scene, "tray")
        self.assertEqual(self.tray()[0]["stage"], 0)
        self.assertIn("paused", self.app.message)
        self.app.handle("down")
        self.assertEqual(self.app.message, "")
        self.app.handle("select")
        self.assertEqual(self.app.care_ms, 0)

    def test_menu_icons_fit_grid(self):
        self.assertEqual(self.app.menu[0], "Care")
        self.assertEqual(len(set(self.app.menu)), len(flora.MENU))
        for label, rects in flora.MENU:
            self.assertTrue(rects, label)
            for x, y, w, h, pen in rects:
                self.assertTrue(0 <= x and 0 <= y and w > 0 and h > 0, label)
                self.assertTrue(x + w <= 7 and y + h <= 7, label)

    def test_up_down_select_pots_only_on_tray(self):
        self.plant_first()
        self.app.handle("down")
        self.assertEqual(self.app.slot, 1)
        self.app.handle("up")
        self.app.handle("up")
        self.assertEqual(self.app.slot, flora.TRAY_SIZE - 1)
        self.assertEqual(self.app.scene, "tray")
        self.act("Seed box")
        self.app.handle("down")
        self.assertEqual(self.app.scene, "tray")
        self.assertEqual(self.app.slot, flora.TRAY_SIZE - 1)

    def test_empty_pot_actions_explain(self):
        self.plant_first()
        self.app.handle("down")
        for label in ("Care", "Inspect", "Move to garden"):
            self.act(label)
            self.assertIn("empty", self.app.message)
            self.app.handle("select")
            self.assertEqual(self.app.scene, "tray")

    def test_second_plant_goes_into_tray(self):
        self.plant_first()
        first = dict(self.tray()[0])
        self.plant_new()
        self.assertEqual(self.app.scene, "tray")
        self.assertEqual(self.tray()[0], first)
        self.assertIsNotNone(self.tray()[1])
        self.assertEqual(self.app.slot, 1)
        self.app.handle("down")
        self.app.handle("down")
        self.app.handle("down")
        self.plant_new()
        self.assertIsNotNone(self.tray()[4])
        self.assertEqual(self.app.slot, 4)

    def test_full_tray_replace_cancel_and_confirm(self):
        self.plant_first()
        for _ in range(flora.TRAY_SIZE - 1):
            self.plant_new()
        self.assertTrue(all(self.tray()))
        self.app.slot = 2
        original = list(self.tray())
        self.plant_new()
        self.assertEqual(self.app.scene, "replace")
        self.app.handle("select")
        self.assertEqual(self.tray(), original)
        self.plant_new()
        self.app.handle("next")
        self.app.handle("select")
        self.assertNotEqual(self.tray()[2]["seed"], original[2]["seed"])
        self.assertEqual(self.tray()[1], original[1])

    def test_grow_move_and_view_garden(self):
        self.plant_first()
        for _ in range(3):
            self.finish_care()
        self.assertEqual(self.tray()[0]["stage"], 3)
        self.act("Care")
        self.assertIn("Move it", self.app.message)
        self.app.handle("select")
        self.app.dirty = False
        self.act("Move to garden")
        self.assertIn("1 flowers", self.app.message)
        self.assertTrue(self.app.dirty)
        self.assertIsNone(self.tray()[0])
        self.assertEqual(len(self.garden.data["garden"]), 1)
        self.app.handle("select")
        self.act("View garden")
        self.assertEqual(self.app.scene, "garden")
        self.app.handle("down")
        self.assertEqual(self.app.scene, "tray")
        self.assertEqual(flora.App(self.garden).scene, "tray")

    def test_skip_and_back(self):
        self.app.handle("select")
        self.app.cursor = 12
        self.app.handle("select")
        self.assertIsNone(self.garden.data["region_id"])
        self.assertEqual(len(self.garden.shelf()), 12)
        self.app.handle("back")
        self.assertEqual(self.app.scene, "regions")

    def test_sample_inbox_and_trade_unavailable(self):
        self.plant_first()
        self.act("Sample seed")
        self.assertIn("not IR", self.app.message)
        self.app.handle("select")
        self.act("Seed box")
        self.app.handle("select")
        self.assertEqual(self.app.scene, "seed")
        self.app.handle("select")
        self.assertEqual(self.app.scene, "tray")
        self.assertEqual(len(self.garden.data["seed_inbox"]), 0)
        self.assertIsNotNone(self.tray()[1])
        self.act("Trade (IR)")
        self.assertEqual(self.app.scene, "trade")
        self.app.handle("back")
        self.assertEqual(self.app.scene, "tray")

    def test_choose_for_me_and_region_preserves_tray(self):
        self.app.handle("select")
        self.app.cursor = 13
        self.app.handle("select")
        self.assertIn(self.garden.data["region_id"], flora.REGION_IDS)
        self.app.handle("select")
        self.app.handle("select")
        original = list(self.tray())
        self.act("Change region")
        self.app.cursor = 4
        self.app.handle("select")
        self.assertEqual(self.garden.data["region_id"], "europe")
        self.assertEqual(self.tray(), original)

    def test_discard_seed(self):
        self.plant_first()
        self.garden.receive(self.garden.new_seed("lotus"))
        self.app.go("inbox")
        self.app.handle("select")
        self.app.handle("back")
        self.assertEqual(len(self.garden.data["seed_inbox"]), 1)
        self.app.handle("select")
        self.app.handle("next")
        self.app.handle("select")
        self.assertEqual(len(self.garden.data["seed_inbox"]), 0)
        self.assertEqual(self.app.scene, "inbox")


if __name__ == "__main__":
    unittest.main()
