# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Noms français de la fiche de lecture (hd.reading), hors variables.

À VALIDER PAR ADRIEN : tout ce fichier. Ce sont des NOMS COURTS, pas des textes
d'interprétation (ceux-ci appartiennent à Adrien et restent hors du moteur). Les noms des
quatre variables (flèches) sont, eux, dans hd/variables_fr.py.

Corriger un mot ici suffit : le champ « reading » de l'API le reprend tel quel.
"""

# ---------------------------------------------------------------- canaux : nom français

# À valider par Adrien. Clé : (porte, porte), la plus petite d'abord, comme hd.data.CHANNELS.
CHANNEL_NAMES_FR = {
    (1, 8): "Inspiration", (2, 14): "Le Battement", (3, 60): "Mutation", (4, 63): "Logique",
    (5, 15): "Rythme", (6, 59): "Intimité", (7, 31): "L'Alpha", (9, 52): "Concentration",
    (10, 20): "Éveil", (10, 34): "Exploration", (10, 57): "Forme parfaite", (11, 56): "Curiosité",
    (12, 22): "Ouverture", (13, 33): "Le Prodigue", (16, 48): "La Longueur d'onde",
    (17, 62): "Acceptation", (18, 58): "Jugement", (19, 49): "Synthèse", (20, 34): "Charisme",
    (20, 57): "L'Onde cérébrale", (21, 45): "Argent", (23, 43): "Structuration",
    (24, 61): "Conscience", (25, 51): "Initiation", (26, 44): "Reddition",
    (27, 50): "Préservation", (28, 38): "Lutte", (29, 46): "Découverte",
    (30, 41): "Reconnaissance", (32, 54): "Transformation", (34, 57): "Pouvoir",
    (35, 36): "Éphémère", (37, 40): "Communauté", (39, 55): "Émotion", (42, 53): "Maturation",
    (47, 64): "Abstraction",
}

# ---------------------------------------------------------------- circuits

# À valider par Adrien (groupes de circuits et circuits). Chaque entrée : (groupe, circuit).
CIRCUIT_GROUPS_FR = {"individual": "Individuel", "tribal": "Tribal", "collective": "Collectif"}
CIRCUITS_FR = {
    "knowing": "Connaissance", "centering": "Centrage", "integration": "Intégration",
    "ego": "Ego", "defense": "Défense",
    "logic": "Logique", "abstract": "Abstrait (sensoriel)",
}
CHANNEL_CIRCUITS = {
    # Individuel
    (3, 60): ("individual", "knowing"), (12, 22): ("individual", "knowing"),
    (23, 43): ("individual", "knowing"), (24, 61): ("individual", "knowing"),
    (28, 38): ("individual", "knowing"), (39, 55): ("individual", "knowing"),
    (1, 8): ("individual", "centering"), (2, 14): ("individual", "centering"),
    (25, 51): ("individual", "centering"),
    (10, 20): ("individual", "integration"), (10, 34): ("individual", "integration"),
    (10, 57): ("individual", "integration"), (20, 34): ("individual", "integration"),
    (20, 57): ("individual", "integration"), (34, 57): ("individual", "integration"),
    # Tribal
    (19, 49): ("tribal", "ego"), (21, 45): ("tribal", "ego"), (26, 44): ("tribal", "ego"),
    (37, 40): ("tribal", "ego"),
    (6, 59): ("tribal", "defense"), (27, 50): ("tribal", "defense"), (32, 54): ("tribal", "defense"),
    # Collectif
    (4, 63): ("collective", "logic"), (5, 15): ("collective", "logic"), (7, 31): ("collective", "logic"),
    (9, 52): ("collective", "logic"), (16, 48): ("collective", "logic"),
    (17, 62): ("collective", "logic"), (18, 58): ("collective", "logic"),
    (11, 56): ("collective", "abstract"), (13, 33): ("collective", "abstract"),
    (29, 46): ("collective", "abstract"), (30, 41): ("collective", "abstract"),
    (35, 36): ("collective", "abstract"), (42, 53): ("collective", "abstract"),
    (47, 64): ("collective", "abstract"),
}

# ---------------------------------------------------------------- croix d'incarnation

# À valider par Adrien. Angle de la croix : nom court.
CROSS_ANGLES_FR = {"right-angle": "Angle droit", "left-angle": "Angle gauche",
                   "juxtaposition": "Juxtaposition"}

# ---------------------------------------------------------------- aura (donnée brute du rythme de sommeil)

# À valider par Adrien. Nom court de l'aura de chaque type.
AURA_FR = {
    "Generator": "Ouverte et enveloppante",
    "Manifesting Generator": "Ouverte et enveloppante",
    "Manifestor": "Fermée et repoussante",
    "Projector": "Concentrée et pénétrante",
    "Reflector": "Résistante (échantillonnage)",
}

# ---------------------------------------------------------------- rubriques sans calcul

# Noms des deux rubriques dont les règles et les statistiques viendront d'Adrien.
RUBRICS_FR = {
    "relations.me_vs_others": "Moi face aux autres",
    "sleep.rhythm": "Rythme de sommeil",
}

# Nom de chaque rubrique de la fiche (identifiant stable → nom court). À valider par Adrien.
SECTION_NAMES_FR = {
    "channels": "Canaux",
    "other": "Autres informations",
    "variables": "Variables",
    "relations": "Moi face aux autres",
    "sleep": "Rythme de sommeil",
}
