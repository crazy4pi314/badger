"""Offline garden; also pasteable into the stock Tufty browser simulator."""

import json
import math
import os
from badgeware import State


STATE_KEY = "fork_flora"
MAX_SEED = 0xFFFFFFFF
INBOX_LIMIT = 6
TRAY_SIZE = 6
GARDEN_LIMIT = 30
SCHEMA = 2
RECIPE_VERSION = 1
STAGES = ("Seed", "Sprout", "Growing", "Blooming")
CARE_MS = 60000
MAX_FRAME_MS = 250
# Garden action icons: rectangles (x, y, w, h, pen) on a 7x7 grid.
MENU = (
    ("Care", ((3, 0, 1, 1, "water"), (2, 1, 3, 1, "water"), (1, 2, 5, 3, "water"),
              (2, 5, 3, 1, "water"), (2, 3, 1, 1, "light"))),
    ("Inspect", ((1, 1, 3, 3, "glass"), (1, 0, 3, 1, "ink"), (0, 1, 1, 3, "ink"),
                 (4, 1, 1, 3, "ink"), (1, 4, 3, 1, "ink"), (4, 4, 1, 1, "wood"),
                 (5, 5, 1, 1, "wood"), (6, 6, 1, 1, "wood"))),
    ("Move to garden", ((0, 1, 3, 2, "bloom"), (1, 3, 1, 2, "leaf"), (0, 5, 3, 2, "wood"),
                        (4, 3, 3, 1, "sun"), (5, 2, 1, 1, "sun"), (5, 4, 1, 1, "sun"))),
    ("View garden", ((0, 1, 2, 2, "bloom"), (3, 0, 2, 2, "sun"), (5, 2, 2, 2, "bloom"),
                     (1, 3, 1, 3, "leaf"), (4, 2, 1, 4, "leaf"), (6, 4, 1, 2, "leaf"),
                     (0, 6, 7, 1, "leaf"))),
    ("New plant", ((2, 3, 1, 4, "leaf"), (0, 2, 2, 1, "leaf"), (3, 1, 2, 1, "leaf"),
                   (5, 0, 1, 3, "sun"), (4, 1, 3, 1, "sun"))),
    ("Seed box", ((0, 1, 7, 1, "light"), (0, 2, 7, 5, "wood"), (2, 3, 3, 2, "sun"))),
    ("Change region", ((2, 0, 3, 1, "water"), (1, 1, 5, 1, "water"), (0, 2, 7, 3, "water"),
                       (1, 5, 5, 1, "water"), (2, 6, 3, 1, "water"), (1, 2, 2, 2, "leaf"),
                       (4, 3, 2, 2, "leaf"), (3, 5, 1, 1, "leaf"))),
    ("Trade (IR)", ((0, 1, 6, 1, "bloom"), (4, 0, 1, 1, "bloom"), (4, 2, 1, 1, "bloom"),
                    (1, 5, 6, 1, "sun"), (2, 4, 1, 1, "sun"), (2, 6, 1, 1, "sun"))),
    ("Sample seed", ((2, 2, 2, 1, "wood"), (1, 3, 4, 2, "wood"), (2, 5, 2, 1, "wood"),
                     (5, 0, 1, 3, "sun"), (4, 1, 3, 1, "sun"))),
)
REGIONS = (
    ("north_america", "North America"),
    ("central_america", "Central America"),
    ("caribbean", "Caribbean"),
    ("south_america", "South America"),
    ("europe", "Europe"),
    ("north_africa", "North Africa"),
    ("sub_saharan", "Sub-Saharan Africa"),
    ("west_asia", "West / Central Asia"),
    ("south_asia", "South Asia"),
    ("east_asia", "East Asia"),
    ("southeast_asia", "Southeast Asia"),
    ("oceania", "Oceania"),
)

# Candidate associations, not reviewed native-range claims. See README.
# id, region, common name, scientific name, habit, flower palette, short fact
SPECIES = (
    ("poppy", "north_america", "California poppy", "Eschscholzia californica",
     "upright", 0, "A cup-shaped flower. Look for four broad petals."),
    ("dahlia", "central_america", "Dahlia", "Dahlia coccinea",
     "branching", 1, "Its flower head holds many small florets."),
    ("sea_grape", "caribbean", "Sea grape", "Coccoloba uvifera",
     "branching", 2, "Look for its rounded leaves and clustered fruits."),
    ("puya", "south_america", "Sapphire tower", "Puya alpestris",
     "rosette", 3, "A tall flower spike rises above a leaf rosette."),
    ("cornflower", "europe", "Cornflower", "Centaurea cyanus",
     "upright", 3, "Many tiny florets make up one blue flower head."),
    ("date_palm", "north_africa", "Date palm", "Phoenix dactylifera",
     "palm", 2, "Long leaflets line each arching frond."),
    ("protea", "sub_saharan", "King protea", "Protea cynaroides",
     "branching", 1, "Large colored bracts surround the flower head."),
    ("tulip", "west_asia", "Wild tulip", "Tulipa sylvestris",
     "upright", 0, "A bulb stores energy below the ground."),
    ("lotus", "south_asia", "Lotus", "Nelumbo nucifera",
     "rosette", 1, "Its leaves and flowers rise above the water."),
    ("camellia", "east_asia", "Camellia", "Camellia japonica",
     "branching", 1, "Glossy leaves frame a layered flower."),
    ("orchid", "southeast_asia", "Moon orchid", "Phalaenopsis amabilis",
     "rosette", 2, "The flower has a distinctive central lip."),
    ("banksia", "oceania", "Coast banksia", "Banksia integrifolia",
     "branching", 0, "Hundreds of tiny flowers form a dense spike."),
)
SPECIES_BY_ID = {item[0]: item for item in SPECIES}
REGION_IDS = tuple(item[0] for item in REGIONS)


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def defaults():
    return {"schema": SCHEMA, "region_id": None, "tray": [None] * TRAY_SIZE,
            "garden": [], "seed_inbox": [], "next_seed": 1}


def valid_seed(record):
    return (
        type(record) is dict
        and type(record.get("species_id")) is str
        and record.get("species_id") in SPECIES_BY_ID
        and integer(record.get("seed"), 0, MAX_SEED)
        and type(record.get("recipe")) is int
        and record.get("recipe") == RECIPE_VERSION
    )


def valid_plant(record):
    return valid_seed(record) and integer(record.get("stage"), 0, 3)


def seed_record(record):
    return {"species_id": record["species_id"], "seed": record["seed"],
            "recipe": record["recipe"]}


def validate_state(data):
    if type(data) is not dict or data.get("schema") not in (1, SCHEMA):
        raise ValueError("Unsupported garden save")
    if data["schema"] == 1:
        plant = data.get("plant")
        if plant is not None and not valid_plant(plant):
            raise ValueError("Invalid saved plant")
        data = {"schema": SCHEMA, "region_id": data.get("region_id"),
                "tray": [plant] + [None] * (TRAY_SIZE - 1), "garden": [],
                "seed_inbox": data.get("seed_inbox"), "next_seed": data.get("next_seed")}
    region = data.get("region_id")
    if region is not None and region not in REGION_IDS:
        raise ValueError("Unknown saved region")
    tray = data.get("tray")
    if type(tray) is not list or len(tray) != TRAY_SIZE or not all(
            plant is None or valid_plant(plant) for plant in tray):
        raise ValueError("Invalid seedling tray")
    flowers = data.get("garden")
    if type(flowers) is not list or len(flowers) > GARDEN_LIMIT or not all(
            valid_seed(record) for record in flowers):
        raise ValueError("Invalid garden")
    inbox = data.get("seed_inbox")
    if type(inbox) is not list or len(inbox) > INBOX_LIMIT:
        raise ValueError("Invalid seed inbox")
    if not all(valid_seed(record) for record in inbox):
        raise ValueError("Invalid inbox seed")
    if not integer(data.get("next_seed"), 1, MAX_SEED):
        raise ValueError("Invalid seed counter")
    return data


def next_random(value):
    return (1664525 * value + 1013904223) & MAX_SEED


def plant_recipe(species_id, seed, stage):
    """Bounded pixel rectangles: (x, y, width, height, palette_index)."""
    if species_id not in SPECIES_BY_ID or not integer(seed, 0, MAX_SEED):
        raise ValueError("Unknown plant recipe")
    if not integer(stage, 0, 3):
        raise ValueError("Unknown growth stage")
    species = SPECIES_BY_ID[species_id]
    value = seed
    for letter in species_id:
        value = next_random(value ^ ord(letter))
    commands = [(14, 28, 4, 2, 0)]
    if stage == 0:
        return tuple(commands)
    height = (7, 15, 23)[stage - 1]
    top = 28 - height
    commands.append((15, top, 2, height, 1))
    habit = species[4]
    if habit == "palm":
        for direction in (-1, 1):
            for offset in range(1, 10):
                commands.append((15 + direction * offset,
                                 top + offset // 3, 2, 2, 2))
    elif habit == "rosette":
        for direction in (-1, 1):
            for offset in range(1, 10):
                commands.append((15 + direction * offset,
                                 27 - offset // 2, 2, 3, 2))
    else:
        for index in range(stage + 1):
            value = next_random(value)
            y = 25 - index * 5
            length = 4 + value % 4
            for direction in (-1, 1):
                x = 16 if direction == 1 else 15 - length
                commands.append((x, y, length, 2, 1))
                commands.append((x, y - 2, length, 2, 2))
                if habit == "branching" and stage >= 2:
                    commands.append((x, y - 5, 2, 4, 1))
                    if stage == 3:
                        commands.append((x - 1, y - 6, 4, 3, 3))
    if stage == 3:
        commands.extend(((12, top - 2, 8, 4, 3),
                         (14, top - 4, 4, 8, 3),
                         (15, top - 1, 2, 2, 4)))
    return tuple(commands)


def meadow_layout(flowers, width, height, scale):
    """Deterministic (record, x, baseline), back-to-front, for overlapping blooms."""
    ground = height * 2 // 5
    span_x = max(1, width - 32 * scale)
    span_y = max(1, height - ground - 8)
    placed = []
    for index, record in enumerate(flowers):
        value = next_random((record["seed"] + index * 7919) & MAX_SEED)
        x = (value >> 8) % span_x
        value = next_random(value)
        baseline = ground + 6 + (value >> 8) % span_y
        placed.append((baseline, index, record, x))
    placed.sort()
    return [(record, x, baseline) for baseline, index, record, x in placed]


class Garden:
    def __init__(self, data=None):
        self.data = validate_state(data) if data is not None else defaults()

    def shelf(self):
        region = self.data["region_id"]
        return tuple(s for s in SPECIES if region is None or s[1] == region)

    def choose_region(self, region):
        if region is not None and region not in REGION_IDS:
            raise ValueError("Unknown region")
        self.data["region_id"] = region

    def new_seed(self, species_id):
        if species_id not in SPECIES_BY_ID:
            raise ValueError("Unknown species")
        seed = self.data["next_seed"]
        self.data["next_seed"] = next_random(seed) or 1
        return {"species_id": species_id, "seed": seed, "recipe": RECIPE_VERSION}

    def plant(self, record, slot):
        if not valid_seed(record):
            raise ValueError("Invalid seed")
        if not integer(slot, 0, TRAY_SIZE - 1):
            raise ValueError("Unknown tray slot")
        self.data["tray"][slot] = dict(seed_record(record), stage=0)

    def open_slot(self, preferred):
        tray = self.data["tray"]
        if tray[preferred] is None:
            return preferred
        for slot in range(TRAY_SIZE):
            if tray[slot] is None:
                return slot
        return None

    def care(self, slot):
        plant = self.data["tray"][slot]
        if plant is None or plant["stage"] == 3:
            return False
        plant["stage"] += 1
        return True

    def move_to_garden(self, slot):
        plant = self.data["tray"][slot]
        flowers = self.data["garden"]
        if plant is None:
            return False, "This pot is empty. Choose New plant to sow a seed."
        if plant["stage"] < 3:
            return False, "Only blooming plants can move to the garden. Keep caring!"
        if len(flowers) >= GARDEN_LIMIT:
            return False, "The garden is full of flowers."
        flowers.append(seed_record(plant))
        self.data["tray"][slot] = None
        return True, "Moved to the garden! " + str(len(flowers)) + " flowers bloom there."

    def receive(self, record):
        if not valid_seed(record):
            raise ValueError("Incompatible seed")
        inbox = self.data["seed_inbox"]
        identity = (record["species_id"], record["seed"], record["recipe"])
        if any((r["species_id"], r["seed"], r["recipe"]) == identity for r in inbox):
            return "Already in your seed box"
        if len(inbox) >= INBOX_LIMIT:
            return "Seed box full: discard one first"
        inbox.append(dict(record))
        return "Sample seed saved (not IR)"

    def plant_inbox(self, index, slot):
        record = self.data["seed_inbox"][index]
        self.plant(record, slot)
        self.data["seed_inbox"].pop(index)


class App:
    def __init__(self, garden):
        self.garden = garden
        data = garden.data
        started = data["garden"] or any(data["tray"])
        self.scene = "tray" if started else "welcome"
        self.slot = 0
        for slot in range(TRAY_SIZE):
            if data["tray"][slot] is not None:
                self.slot = slot
                break
        self.care_slot = 0
        self.cursor = 0
        self.return_scene = "tray"
        self.detail_id = None
        self.pending = None
        self.message = ""
        self.dirty = False
        self.menu = tuple(item[0] for item in MENU)
        self.care_ms = 0

    def selected(self):
        return self.garden.data["tray"][self.slot]

    def go(self, scene):
        self.scene = scene
        self.cursor = 0

    def options(self):
        if self.scene == "regions":
            return tuple(r[1] for r in REGIONS) + ("Skip / all plants", "Choose for me", "Back")
        if self.scene == "shelf":
            return tuple(s[2] for s in self.garden.shelf()) + ("Back",)
        if self.scene == "tray":
            return self.menu
        if self.scene == "inbox":
            return tuple(SPECIES_BY_ID[r["species_id"]][2]
                         for r in self.garden.data["seed_inbox"]) + ("Back",)
        if self.scene == "seed":
            return ("Plant seed", "Discard seed", "Back")
        if self.scene == "replace":
            return ("Keep my seedlings", "Replace selected pot")
        return ()

    def handle(self, action):
        if self.message:
            if action in ("select", "back", "down"):
                self.message = ""
            return
        if action in ("up", "down"):
            if self.scene == "tray":
                self.slot = (self.slot + (1 if action == "down" else -1)) % TRAY_SIZE
                return
            action = "previous" if action == "up" else "back"
        options = self.options()
        if action in ("next", "previous") and options:
            self.cursor = (self.cursor + (1 if action == "next" else -1)) % len(options)
            return
        if action == "back":
            destinations = {"welcome": "welcome", "tray": "tray",
                            "regions": self.return_scene, "shelf": "regions",
                            "card": "shelf", "inspect": "tray", "garden": "tray",
                            "inbox": "tray", "seed": "inbox", "replace": "tray",
                            "trade": "tray"}
            if self.scene == "care":
                self.care_ms = 0
                self.go("tray")
                self.message = "Care paused. No harm done."
                return
            self.pending = None
            self.go(destinations[self.scene])
            return
        if action != "select":
            return
        scene = self.scene
        if scene == "welcome":
            self.return_scene = "welcome"
            self.go("regions")
        elif scene == "regions":
            if self.cursor == len(REGIONS) + 2:
                self.go(self.return_scene)
                return
            if self.cursor == len(REGIONS) + 1:
                index = self.garden.data["next_seed"] % len(REGIONS)
                region = REGIONS[index][0]
            else:
                region = REGIONS[self.cursor][0] if self.cursor < len(REGIONS) else None
            self.garden.choose_region(region)
            self.dirty = True
            self.go("shelf")
        elif scene == "shelf":
            shelf = self.garden.shelf()
            if self.cursor == len(shelf):
                self.go("regions")
            else:
                self.detail_id = shelf[self.cursor][0]
                self.go("card")
        elif scene == "card":
            self.pending = ("new", self.detail_id)
            self.confirm_plant()
        elif scene == "tray":
            self.tray_action(self.menu[self.cursor])
        elif scene == "inbox":
            if self.cursor == len(self.garden.data["seed_inbox"]):
                self.go("tray")
            else:
                self.inbox_index = self.cursor
                self.detail_id = self.garden.data["seed_inbox"][self.cursor]["species_id"]
                self.go("seed")
        elif scene == "seed":
            if self.cursor == 0:
                self.pending = ("inbox", self.inbox_index)
                self.confirm_plant()
            elif self.cursor == 1:
                self.garden.data["seed_inbox"].pop(self.inbox_index)
                self.dirty = True
                self.go("inbox")
            else:
                self.go("inbox")
        elif scene == "replace":
            if self.cursor == 1:
                self.apply_plant(self.slot)
            else:
                self.pending = None
                self.go("tray")
        elif scene in ("inspect", "trade", "garden"):
            self.go("tray")

    def tray_action(self, choice):
        plant = self.selected()
        empty = "This pot is empty. Choose New plant to sow a seed."
        if choice == "Care":
            if plant is None:
                self.message = empty
            elif plant["stage"] == 3:
                self.message = "Already blooming! Move it to the garden."
            else:
                self.care_ms = 0
                self.care_slot = self.slot
                self.scene = "care"
        elif choice == "Inspect":
            if plant is None:
                self.message = empty
            else:
                self.detail_id = plant["species_id"]
                self.go("inspect")
        elif choice == "Move to garden":
            moved, self.message = self.garden.move_to_garden(self.slot)
            self.dirty = moved or self.dirty
        elif choice == "View garden":
            self.go("garden")
        elif choice == "Seed box":
            self.go("inbox")
        elif choice == "New plant":
            self.go("shelf")
        elif choice == "Change region":
            self.return_scene = "tray"
            self.go("regions")
        elif choice == "Trade (IR)":
            self.go("trade")
        elif choice == "Sample seed":
            seed = self.garden.data["next_seed"]
            species_id = SPECIES[seed % len(SPECIES)][0]
            record = self.garden.new_seed(species_id)
            self.message = self.garden.receive(record)
            self.dirty = True

    def tick(self, delta_ms):
        if self.scene != "care" or self.message:
            return
        self.care_ms += max(0, min(delta_ms, MAX_FRAME_MS))
        if self.care_ms < CARE_MS:
            return
        self.care_ms = 0
        self.go("tray")
        self.slot = self.care_slot
        if self.garden.care(self.slot):
            self.dirty = True
            plant = self.selected()
            self.message = "Care complete! " + SPECIES_BY_ID[plant["species_id"]][2] + \
                " is now " + STAGES[plant["stage"]] + "."
            if plant["stage"] == 3:
                self.message += " Move it to the garden!"

    def confirm_plant(self):
        slot = self.garden.open_slot(self.slot)
        if slot is None:
            self.go("replace")
        else:
            self.apply_plant(slot)

    def apply_plant(self, slot):
        kind, value = self.pending
        if kind == "new":
            self.garden.plant(self.garden.new_seed(value), slot)
        else:
            self.garden.plant_inbox(value, slot)
        self.pending = None
        self.dirty = True
        self.slot = slot
        self.go("tray")


def load_garden():
    path = "/state/" + STATE_KEY + ".json"
    try:
        # The web simulator's WASI errno numbers differ from its errno module.
        if "state" not in os.listdir("/") or STATE_KEY + ".json" not in os.listdir("/state"):
            return Garden(), ""
        with open(path) as saved:
            return Garden(json.load(saved)), ""
    except OSError as error:
        print("Fork & Flora load error:", error)
        return Garden(), "Save unreadable. Changes not saved."
    except (ValueError, TypeError) as error:
        print("Fork & Flora invalid save:", error)
        return Garden(), "Save invalid. Changes not saved."


def save_garden(garden):
    # State implementations may swallow write errors; verify before claiming saved.
    State.save(STATE_KEY, garden.data)
    with open("/state/" + STATE_KEY + ".json") as saved:
        if json.load(saved) != garden.data:
            raise OSError("Garden save verification failed")


def start():
    import builtins
    logical = hasattr(builtins, "BUTTON_SELECT")
    if logical:
        previous, following, select = BUTTON_LEFT, BUTTON_RIGHT, BUTTON_SELECT
    else:
        previous, following, select = BUTTON_A, BUTTON_C, BUTTON_B
    back = getattr(builtins, "BUTTON_BACK", None)
    screen.font = font.sins
    screen.antialias = image.OFF
    garden, load_error = load_garden()
    app = App(garden)
    app.message = load_error
    save_enabled = not load_error
    palette = (
        color.rgb(31, 30, 38), color.rgb(42, 100, 76),
        color.rgb(124, 182, 91), color.rgb(249, 179, 63),
        color.rgb(255, 235, 173),
    )
    flowers = (color.rgb(249, 179, 63), color.rgb(238, 136, 162),
               color.rgb(241, 237, 216), color.rgb(96, 184, 212))
    background = color.rgb(20, 39, 40)
    ink = color.rgb(245, 240, 217)
    muted = color.rgb(163, 199, 175)
    highlight = color.rgb(44, 82, 67)
    soil = color.rgb(140, 91, 64)
    icon_pens = {
        "water": color.rgb(96, 184, 230), "light": color.rgb(230, 248, 255),
        "glass": color.rgb(150, 210, 230), "ink": ink, "wood": soil,
        "sun": color.rgb(255, 214, 80), "leaf": color.rgb(124, 182, 91),
        "bloom": color.rgb(238, 136, 162),
    }
    sun_pen = color.rgb(255, 214, 80)
    sun_glow = color.rgb(255, 170, 60)
    bar_back = color.rgb(36, 60, 55)
    recipes = {}

    def text(label, x, y, width=None, pen=ink):
        screen.pen = pen
        if width is not None:
            while label and screen.measure_text(label)[0] > width:
                label = label[:-1]
        screen.text(label, x, y)

    def paragraph(label, y, width, max_lines=5):
        line = ""
        row = 0
        for word in label.split():
            candidate = (line + " " + word).strip()
            if line and screen.measure_text(candidate)[0] > width:
                text(line, 8, y + row * 12)
                row += 1
                line = word
                if row >= max_lines:
                    return
            else:
                line = candidate
        text(line, 8, y + row * 12, width)

    def draw_plant(species_id, seed, stage, x, baseline, scale, pot=True):
        key = (species_id, seed, stage)
        recipe = recipes.get(key)
        if recipe is None:
            if len(recipes) > 64:
                recipes.clear()
            recipe = recipes[key] = plant_recipe(*key)
        bloom = flowers[SPECIES_BY_ID[species_id][5]]
        for px, py, width, height, pen in recipe:
            if pen == 0 and not pot:
                continue
            screen.pen = bloom if pen == 3 else palette[pen]
            screen.rectangle(x + px * scale, baseline + (py - 30) * scale,
                             width * scale, height * scale)
        if pot:
            draw_pot(x, baseline, scale, soil)

    def draw_pot(x, baseline, scale, pen):
        screen.pen = pen
        screen.rectangle(x + 8 * scale, baseline, 16 * scale, 3 * scale)
        screen.rectangle(x + 10 * scale, baseline + 3 * scale, 12 * scale, 4 * scale)

    def draw_icon(rects, x, y, unit):
        for px, py, w, h, pen in rects:
            screen.pen = icon_pens[pen]
            screen.rectangle(x + px * unit, y + py * unit, w * unit, h * unit)

    def centered(label, y, pen=ink):
        screen.pen = pen
        screen.text(label, (screen.width - screen.measure_text(label)[0]) // 2, y)

    def bar_layout(height):
        unit = max(1, height // 120)
        bar_top = height - 17 * unit
        return unit, bar_top, bar_top - 11 * unit

    def draw_focus_plant(plant, width, height):
        unit, bar_top, label_y = bar_layout(height)
        scale = max(1, min((label_y - 35) // 37, (width - 16) // 32))
        baseline = label_y - 2 - 7 * scale
        text(SPECIES_BY_ID[plant["species_id"]][2], 6, 21, width - 12)
        text(STAGES[plant["stage"]], 6, 31, width - 12, muted)
        draw_plant(plant["species_id"], plant["seed"], plant["stage"],
                   width // 2 - 16 * scale, baseline, scale)
        return unit, bar_top, label_y, scale, baseline

    def draw_tray(width, height):
        unit, bar_top, label_y = bar_layout(height)
        plant = app.selected()
        title = "Pot " + str(app.slot + 1) + ": "
        if plant is None:
            title += "empty"
        else:
            title += SPECIES_BY_ID[plant["species_id"]][2]
            stage = STAGES[plant["stage"]]
            text(stage, width - 6 - screen.measure_text(stage)[0], 3, None,
                 sun_pen if plant["stage"] == 3 else muted)
        text(title, 6, 3, width - 60)
        top = 18
        cell_w = width // 3
        cell_h = (label_y - top) // 2
        scale = max(1, min(cell_h // 37, cell_w // 34))
        for slot in range(TRAY_SIZE):
            x = (slot % 3) * cell_w
            y = top + (slot // 3) * cell_h
            if slot == app.slot:
                screen.pen = highlight
                screen.rectangle(x + 1, y, cell_w - 2, cell_h - 1)
            px = x + (cell_w - 32 * scale) // 2
            baseline = y + cell_h - 8 * scale
            seedling = garden.data["tray"][slot]
            if seedling is None:
                draw_pot(px, baseline, scale, bar_back)
            else:
                draw_plant(seedling["species_id"], seedling["seed"], seedling["stage"],
                           px, baseline, scale)
                if seedling["stage"] == 3:
                    screen.pen = sun_pen
                    screen.rectangle(x + cell_w - 6 * unit, y + 2 * unit, 3 * unit, 3 * unit)
        draw_icon_bar(unit, bar_top, label_y)

    def draw_meadow(width, height):
        flowers_here = garden.data["garden"]
        count = str(len(flowers_here)) + "/" + str(GARDEN_LIMIT)
        text("Your garden", 6, 3, width - 50)
        text(count, width - 6 - screen.measure_text(count)[0], 3, None, muted)
        unit = max(1, height // 120)
        ground = height * 2 // 5
        screen.pen = palette[1]
        screen.rectangle(0, ground, width, height - ground)
        screen.pen = highlight
        screen.rectangle(0, ground, width, unit)
        if not flowers_here:
            paragraph("No flowers yet. Grow a seedling to Blooming, then choose "
                      "Move to garden.", 24, width - 16, 4)
            return
        for record, x, baseline in meadow_layout(flowers_here, width, height, unit):
            draw_plant(record["species_id"], record["seed"], 3, x, baseline, unit, False)

    def draw_icon_bar(unit, bar_top, label_y):
        cell = 2 * unit
        size = 7 * cell
        spacing = size + 8 * unit
        middle = screen.width // 2
        count = len(MENU)
        for offset in range(-2, 3):
            index = (app.cursor + offset) % count
            x = middle - size // 2 + offset * spacing
            y = bar_top + 2 * unit
            if offset == 0:
                screen.pen = highlight
                screen.rectangle(x - 3 * unit, y - 2 * unit, size + 6 * unit, size + 4 * unit)
                screen.pen = sun_pen
                screen.rectangle(x - 3 * unit, y + size + 2 * unit - unit, size + 6 * unit, unit)
            draw_icon(MENU[index][1], x, y, cell)
        screen.pen = muted
        screen.text("<", 2, bar_top + 5 * unit)
        screen.text(">", screen.width - 2 - screen.measure_text(">")[0], bar_top + 5 * unit)
        centered(MENU[app.cursor][0], label_y)

    def draw_care(plant, width, height):
        unit, bar_top, label_y, scale, baseline = draw_focus_plant(plant, width, height)
        elapsed = app.care_ms
        seconds = elapsed / 1000
        # Sun with slowly rotating, pulsing rays.
        sun_x, sun_y, radius = width - 20 * unit, 34 * unit, 6 * unit
        angle = seconds * 0.9
        screen.pen = sun_glow
        for ray in range(8):
            a = angle + ray * math.pi / 4
            reach = radius + (3 + (ray % 2) * 2 + int(math.sin(seconds * 4) + 1)) * unit
            screen.rectangle(int(sun_x + math.cos(a) * reach) - unit,
                             int(sun_y + math.sin(a) * reach) - unit, 2 * unit, 2 * unit)
        screen.pen = sun_pen
        screen.shape(shape.circle(sun_x, sun_y, radius))
        # Water drops falling onto the plant, positioned from elapsed time.
        left = width // 2 - 14 * scale
        top = 38 * unit
        fall = max(1, baseline - top)
        for drop in range(6):
            x = left + (drop * 37 % 28) * scale
            y = top + int(seconds * 45 * unit + drop * fall / 6) % fall
            screen.pen = icon_pens["water"]
            screen.rectangle(x, y, unit, unit)
            screen.rectangle(x - unit, y + unit, 3 * unit, 2 * unit)
            screen.pen = icon_pens["light"]
            screen.rectangle(x - unit, y + unit, unit, unit)
        # Progress bar.
        remaining = max(0, (CARE_MS - elapsed + 999) // 1000)
        status = "Caring " + str(remaining) + "s"
        text("Down: stop", 6, label_y, width - 12, muted)
        text(status, width - 6 - screen.measure_text(status)[0], label_y)
        bar_x, bar_w, bar_h = 8, width - 16, 8 * unit
        bar_y = bar_top + 4 * unit
        screen.pen = bar_back
        screen.rectangle(bar_x, bar_y, bar_w, bar_h)
        filled = bar_w * min(elapsed, CARE_MS) // CARE_MS
        screen.pen = icon_pens["water"]
        screen.rectangle(bar_x, bar_y, filled, bar_h)
        screen.pen = sun_pen
        screen.rectangle(bar_x, bar_y, filled, unit)

    def draw():
        width, height = screen.width, screen.height
        screen.pen = background
        screen.rectangle(screen.clip)
        bottom = height - 13
        scene = app.scene
        if scene in ("tray", "garden") and not app.message:
            if scene == "tray":
                draw_tray(width, height)
            else:
                draw_meadow(width, height)
            return
        text("Fork & Flora", 6, 3, width - 12)
        screen.pen = highlight
        screen.rectangle(0, 16, width, 1)
        if app.message:
            paragraph(app.message, 30, width - 16)
            text("Select / Down: dismiss", 6, bottom, width - 12, muted)
            return
        if scene == "welcome":
            paragraph("A tiny garden. Grow up to six seedlings, then move blooms "
                      "into your garden.", 24, width - 16, 4)
            text("Draft botanical catalog", 8, 82, width - 16, muted)
        elif scene in ("regions", "shelf", "inbox", "replace"):
            headings = {"regions": "Choose a broad region", "shelf": "Candidate plants",
                        "inbox": "Seed box (local samples)",
                        "replace": "Tray full! Replace pot " + str(app.slot + 1) + "?"}
            text(headings[scene], 6, 21, width - 12, muted)
            options = app.options()
            first = max(0, app.cursor - 3)
            for index in range(first, min(first + 5, len(options))):
                y = 37 + (index - first) * 13
                if index == app.cursor:
                    screen.pen = highlight
                    screen.rectangle(3, y - 1, width - 6, 12)
                text(("> " if index == app.cursor else "  ") + options[index],
                     6, y, width - 12)
        elif scene == "care":
            draw_care(garden.data["tray"][app.care_slot], width, height)
            return
        elif scene in ("card", "inspect"):
            species = SPECIES_BY_ID[app.detail_id]
            text(species[2], 6, 21, width - 12)
            plant = app.selected() if scene == "inspect" else None
            draw_plant(species[0], plant["seed"] if plant else 1,
                       plant["stage"] if plant else 3, width - 40, 80, 1)
            text(species[3], 6, 35, width - 12, muted)
            paragraph(species[6], 51, width - 56, 4)
        elif scene == "seed":
            text(SPECIES_BY_ID[app.detail_id][2], 6, 23, width - 12)
            record = garden.data["seed_inbox"][app.inbox_index]
            draw_plant(record["species_id"], record["seed"], 3, width // 2 - 16, 83, 1)
            text("< " + app.options()[app.cursor] + " >", 6, bottom - 10, width - 12)
        elif scene == "trade":
            paragraph("IR trading is not wired yet. No seed was sent. Use Sample seed to test the inbox.", 27, width - 16, 6)
        hint = "Select: plant  Down: back" if scene == "card" else "Select: OK  Down: back"
        text(hint, 6, bottom, width - 12, muted)

    def update():
        nonlocal save_enabled
        action = None
        if back is not None and badge.pressed(back):
            action = "back"
        elif badge.pressed(BUTTON_DOWN):
            action = "down"
        elif badge.pressed(BUTTON_UP):
            action = "up"
        elif badge.pressed(previous):
            action = "previous"
        elif badge.pressed(following):
            action = "next"
        elif badge.pressed(select):
            action = "select"
        if action is not None:
            app.handle(action)
        app.tick(badge.ticks_delta)
        if app.dirty:
            if save_enabled:
                try:
                    save_garden(garden)
                except (OSError, ValueError) as error:
                    print("Fork & Flora save error:", error)
                    app.message = "Save failed. This visit is not saved."
                    save_enabled = False
            app.dirty = False
        draw()

    run(update)


if __name__ == "__main__" or "badge" in globals() or hasattr(__import__("builtins"), "badge"):
    start()
