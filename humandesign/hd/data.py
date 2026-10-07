# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

GATE_ORDER = [
    41, 19, 13, 49, 30, 55, 37, 63, 22, 36, 25, 17, 21, 51, 42, 3,
    27, 24, 2, 23, 8, 20, 16, 35, 45, 12, 15, 52, 39, 53, 62, 56,
    31, 33, 7, 4, 29, 59, 40, 64, 47, 6, 46, 18, 48, 57, 32, 50,
    28, 44, 1, 43, 14, 34, 9, 5, 26, 11, 10, 58, 38, 54, 61, 60,
]
WHEEL_START = 302.0  # gate 41 line 1 begins at 2°00' Aquarius
GATE_ARC = 360 / 64
LINE_ARC = GATE_ARC / 6
COLOR_ARC = LINE_ARC / 6
TONE_ARC = COLOR_ARC / 6
BASE_ARC = TONE_ARC / 5

DESIGN_SOLAR_ARC = 88.0

CENTERS = {
    "head": [64, 61, 63],
    "ajna": [47, 24, 4, 17, 43, 11],
    "throat": [62, 23, 56, 16, 35, 20, 31, 8, 33, 12, 45],
    "g": [1, 13, 25, 46, 2, 15, 10, 7],
    "heart": [21, 40, 26, 51],
    "sacral": [5, 14, 29, 34, 27, 59, 42, 3, 9],
    "solar_plexus": [36, 22, 37, 6, 49, 55, 30],
    "spleen": [48, 57, 44, 50, 32, 28, 18],
    "root": [53, 60, 52, 54, 38, 58, 19, 39, 41],
}
GATE_CENTER = {g: c for c, gates in CENTERS.items() for g in gates}
MOTORS = {"heart", "sacral", "solar_plexus", "root"}

CENTER_NAMES_FR = {
    "head": "Tête", "ajna": "Ajna", "throat": "Gorge", "g": "G (Identité)",
    "heart": "Cœur (Ego)", "sacral": "Sacral", "solar_plexus": "Plexus solaire",
    "spleen": "Rate", "root": "Racine",
}

CHANNELS = [
    (1, 8), (2, 14), (3, 60), (4, 63), (5, 15), (6, 59), (7, 31), (9, 52),
    (10, 20), (10, 34), (10, 57), (11, 56), (12, 22), (13, 33), (16, 48), (17, 62),
    (18, 58), (19, 49), (20, 34), (20, 57), (21, 45), (23, 43), (24, 61), (25, 51),
    (26, 44), (27, 50), (28, 38), (29, 46), (30, 41), (32, 54), (34, 57), (35, 36),
    (37, 40), (39, 55), (42, 53), (47, 64),
]

PLANETS = [
    "sun", "earth", "moon", "north_node", "south_node", "mercury", "venus",
    "mars", "jupiter", "saturn", "uranus", "neptune", "pluto",
]
PLANET_GLYPHS = {
    "sun": "☉", "earth": "⊕", "moon": "☽", "north_node": "☊",
    "south_node": "☋", "mercury": "☿", "venus": "♀", "mars": "♂",
    "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆",
    "pluto": "♇",
}
PLANET_NAMES_FR = {
    "sun": "Soleil", "earth": "Terre", "moon": "Lune", "north_node": "Nœud Nord",
    "south_node": "Nœud Sud", "mercury": "Mercure", "venus": "Vénus", "mars": "Mars",
    "jupiter": "Jupiter", "saturn": "Saturne", "uranus": "Uranus", "neptune": "Neptune",
    "pluto": "Pluton",
}

TYPES_FR = {
    "Generator": ("Générateur", "Répondre", "Satisfaction", "Frustration"),
    "Manifesting Generator": ("M-Générateur", "Répondre, puis informer",
                              "Satisfaction", "Frustration / Colère"),
    "Manifestor": ("Manifesteur", "Informer", "Paix", "Colère"),
    "Projector": ("Projecteur", "Attendre l'invitation", "Succès", "Amertume"),
    "Reflector": ("Réflecteur", "Attendre un cycle lunaire (~28 jours)", "Surprise", "Déception"),
}

AUTHORITY_FR = {
    "Emotional": "Émotionnelle (Plexus solaire)",
    "Sacral": "Sacrale",
    "Splenic": "Splénique",
    "Ego Manifested": "Ego manifestée",
    "Ego Projected": "Ego projetée",
    "Self-Projected": "Auto-projetée (G)",
    "Mental": "Mentale / Environnementale",
    "Lunar": "Lunaire",
}

DEFINITION_FR = {
    0: "Aucune définition", 1: "Définition simple", 2: "Split (double)",
    3: "Triple split", 4: "Quadruple split",
}

LINE_NAMES_FR = {1: "Investigateur", 2: "Ermite", 3: "Martyr",
                 4: "Opportuniste", 5: "Hérétique", 6: "Modèle"}

QUARTERS = ["Initiation", "Civilisation", "Dualité", "Mutation"]

RIGHT_ANGLE_CROSSES = {
    "the Sphinx": [1, 2, 7, 13],
    "the Vessel of Love": [10, 15, 25, 46],
    "the Four Ways": [19, 24, 33, 44],
    "Contagion": [8, 14, 29, 30],
    "Eden": [6, 11, 12, 36],
    "Explanation": [4, 23, 43, 49],
    "Laws": [3, 50, 56, 60],
    "Maya": [32, 42, 61, 62],
    "Penetration": [51, 53, 54, 57],
    "Planning": [9, 16, 37, 40],
    "Rulership": [22, 26, 45, 47],
    "Service": [17, 18, 52, 58],
    "the Sleeping Phoenix": [20, 34, 55, 59],
    "Tension": [21, 38, 39, 48],
    "the Unexpected": [27, 28, 31, 41],
    "Consciousness": [5, 35, 63, 64],
}
RAX_BY_GATE = {g: n for n, gates in RIGHT_ANGLE_CROSSES.items() for g in gates}

LEFT_ANGLE_CROSSES = {
    "Defiance": (1, 2), "Wishes": (3, 50), "Revolution": (4, 49),
    "Separation": (5, 35), "the Plane": (6, 36), "Masks": (7, 13),
    "Uncertainty": (8, 14), "Identification": (9, 16), "Prevention": (10, 15),
    "Education": (11, 12), "Upheaval": (17, 18), "Refinement": (19, 33),
    "Duality": (20, 34), "Endeavor": (21, 48), "Informing": (22, 47),
    "Dedication": (23, 43), "Incarnation": (24, 44), "Healing": (25, 46),
    "Confrontation": (26, 45), "Alignment": (27, 28), "Industry": (29, 30),
    "the Alpha": (31, 41), "Limitation": (32, 42), "Migration": (37, 40),
    "Individualism": (38, 39), "the Clarion": (51, 57), "Demands": (52, 58),
    "Cycles": (53, 54), "Spirit": (55, 59), "Distraction": (56, 60),
    "Obscuration": (61, 62), "Dominion": (63, 64),
}
LAX_BY_GATE = {g: n for n, pair in LEFT_ANGLE_CROSSES.items() for g in pair}

JUXTAPOSITION_CROSSES = {
    1: "Self-Expression", 2: "the Driver", 3: "Mutation", 4: "Formulization",
    5: "Habits", 6: "Conflict", 7: "Interaction", 8: "Contribution",
    9: "Focus", 10: "Behavior", 11: "Ideas", 12: "Articulation",
    13: "Listening", 14: "Empowering", 15: "Extremes", 16: "Experimentation",
    17: "Opinions", 18: "Correction", 19: "Need", 20: "the Now",
    21: "Control", 22: "Grace", 23: "Assimilation", 24: "Rationalization",
    25: "Innocence", 26: "the Trickster", 27: "Caring", 28: "Risks",
    29: "Commitment", 30: "Fates", 31: "Influence", 32: "Conservation",
    33: "Retreat", 34: "Power", 35: "Experience", 36: "Crisis",
    37: "Bargains", 38: "Opposition", 39: "Provocation", 40: "Denial",
    41: "Fantasy", 42: "Completion", 43: "Insight", 44: "Alertness",
    45: "Possession", 46: "Serendipity", 47: "Oppression", 48: "Depth",
    49: "Principles", 50: "Values", 51: "Shock", 52: "Stillness",
    53: "Beginnings", 54: "Ambition", 55: "Moods", 56: "Stimulation",
    57: "Intuition", 58: "Vitality", 59: "Strategy", 60: "Limitation",
    61: "Thinking", 62: "Detail", 63: "Doubts", 64: "Confusion",
}

VARIABLE_LABELS = {
    "design_sun": "Détermination (Digestion)",
    "design_node": "Environnement",
    "personality_sun": "Motivation",
    "personality_node": "Perspective",
}
