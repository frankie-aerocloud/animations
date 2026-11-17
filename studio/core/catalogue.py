"""Names shared by configuration validation (venv Python) and the Blender-side builders."""

CORE = "studio.blender.environments"
NYC = "studio.blender.environments_nyc"
VEGAS = "studio.blender.environments_vegas"
LONDON = "studio.blender.environments_london"
# environment type -> module that builds it; the Blender entry point imports only that module,
# so a scene's recorded code dependencies never include other productions' environments
ENVIRONMENTS = {
    "coastal_city": CORE,
    "residential_street": CORE,
    "kitchen_interior": CORE,
    "supermarket_interior": CORE,
    "distribution_point": CORE,
    "hospital_exterior": CORE,
    "farm": CORE,
    "industrial": CORE,
    "reservoir": CORE,
    "port": CORE,
    "desert": CORE,
    "highway": CORE,
    "harbour_dawn": NYC,
    "metropolis": NYC,
    "airport": NYC,
    "mojave": VEGAS,
    "vegas_strip": VEGAS,
    "casino_floor": VEGAS,
    "desert_airport": VEGAS,
    "desert_suburb": VEGAS,
    "london_street": LONDON,
    "london_park": LONDON,
    "london_aerial": LONDON,
    "westminster": LONDON,
    "thames": LONDON,
    "london_interior": LONDON,
    "sports_hall": LONDON,
    "london_works": LONDON,
    "london_hospital": LONDON,
}
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
SFX = ("whoosh", "impact", "riser", "drip", "alarm", "siren", "rumble", "tick", "swell", "thud", "crowd", "fire", "horns", "helicopter", "heartbeat", "glass", "gulls", "flapping", "drone_buzz", "loudspeaker", "jets", "splat", "roar", "alert", "radio", "thunder", "birds", "gust")
PROPS = ("jerrycan", "bottle", "bucket", "box", "pan")
CARD_KINDS = ("title", "caption", "chapter", "alert")
ACTOR_KINDS = ("person", "lion")
LION_ACTIONS = ("walk", "prowl", "run", "idle", "roar", "lie")
