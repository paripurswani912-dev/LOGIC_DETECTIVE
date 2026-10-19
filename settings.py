# settings.py
# Shared settings for Logic Detective

GAME_TITLE = "Logic Detective: The Digital Escape Room"

# Window settings
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 650
FPS = 60

# Player settings
PLAYER_WIDTH = 30
PLAYER_HEIGHT = 36
PLAYER_SPEED = 220

# Interaction settings
INTERACTION_DISTANCE = 65

# Final level timer
FINAL_LEVEL_TIME = 120

# --------------------------------------------------
# RETRO PIXEL LABORATORY COLOUR PALETTE
# --------------------------------------------------

# General colours
BLACK = (20, 24, 30)
WHITE = (231, 226, 213)

# Environment
DARK_BLUE = (27, 36, 44)
PANEL_BLUE = (40, 52, 63)

FLOOR_COLOR = (53, 70, 87)
FLOOR_ALT_COLOR = (44, 59, 74)

WALL_COLOR = (100, 119, 137)
WALL_SHADOW = (32, 40, 51)

# CRT computer screens
CRT_BACKGROUND = (20, 41, 31)
CRT_GREEN = (140, 219, 140)
CRT_DIM_GREEN = (65, 116, 76)

# Status colours
CYAN = (122, 183, 190)
GREEN = (140, 219, 140)

YELLOW = (233, 173, 85)
AMBER = (233, 173, 85)

RED = (200, 92, 85)
GREY = (133, 146, 155)

# Laboratory doors
DOOR_COLOR = (111, 92, 73)
LOCKED_DOOR_COLOR = RED
UNLOCKED_DOOR_COLOR = GREEN

# UI styling
UI_BACKGROUND = (27, 36, 44)
UI_BORDER = (100, 119, 137)
UI_HIGHLIGHT = AMBER

# Pixel-art rendering
PIXEL_SCALE = 3