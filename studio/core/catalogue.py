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
    "highway",
    "harbour_dawn",
    "metropolis",
    "airport",
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
ROLES = ("civilian", "shopper", "child", "nurse", "doctor", "paramedic", "worker", "farmer", "police", "soldier", "fisherman")
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
    "scatter",
)
EVENTS = ("water_level", "hide", "show", "move", "spin", "flicker", "flash", "scale", "deplete", "sun", "blackout")
SFX = ("whoosh", "impact", "riser", "drip", "alarm", "siren", "rumble", "tick", "swell", "thud", "crowd", "fire", "horns", "helicopter", "heartbeat", "glass", "gulls", "flapping", "drone_buzz", "loudspeaker", "jets", "splat")
PROPS = ("jerrycan", "bottle", "bucket", "box", "pan")
CARD_KINDS = ("title", "caption", "chapter")
