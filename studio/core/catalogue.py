"""Names shared by configuration validation (venv Python) and the Blender-side builders."""

ENVIRONMENTS = (
    "coastal_city",
    "residential_street",
    "kitchen_interior",
    "supermarket_interior",
    "distribution_point",
    "hospital_exterior",
    "farm",
    "industrial",
    "reservoir",
    "port",
    "desert",
)
SHOTS = (
    "aerial_establish",
    "push_in",
    "tracking",
    "orbit",
    "side_follow",
    "first_person",
    "close_up",
    "wide",
    "reveal",
    "static",
)
# storyboard transition name -> FFmpeg xfade transition
TRANSITIONS = {
    "cut": "fade",
    "dissolve": "fade",
    "fade_black": "fadeblack",
    "fade_white": "fadewhite",
    "whip": "slideleft",
    "whip_right": "slideright",
    "wipe": "wipeleft",
    "zoom": "zoomin",
    "circle": "circleopen",
    "blur": "hblur",
}
LIGHTING = (
    "soft_daylight",
    "golden_hour",
    "overcast",
    "harsh_noon",
    "dusk_urgent",
    "night_emergency",
    "interior_day",
)
ROLES = ("civilian", "shopper", "child", "nurse", "doctor", "paramedic", "worker", "farmer", "police")
ACTIONS = (
    "idle",
    "walk",
    "run",
    "look_around",
    "point",
    "fall",
    "carry",
    "gather",
    "react",
    "queue",
    "crouch",
    "stand",
)
EVENTS = ("water_level", "hide", "show", "move", "spin", "flicker", "flash", "scale", "deplete", "sun")
SFX = ("whoosh", "impact", "riser", "drip", "alarm", "siren", "rumble", "tick", "swell", "thud", "crowd")
PROPS = ("jerrycan", "bottle", "bucket", "box", "pan")
