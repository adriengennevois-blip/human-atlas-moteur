# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Tous les textes français des quatre variables (les « flèches »), en un seul endroit.

À VALIDER PAR ADRIEN : ce fichier ne contient que du texte, aucun calcul. Corriger un mot
ici suffit : le JSON de l'API (champ « variables »), le SVG et la ligne de commande le
reprennent tels quels.

Les quatre flèches (côté et corps qui les portent, voir hd.precision.VARIABLES) :
  determination  Soleil Design           haut-gauche   Digestion (aussi appelée Détermination)
  environment    Nœud Nord Design        bas-gauche    Environnement
  motivation     Soleil Personnalité     haut-droite   Motivation
  perspective    Nœud Nord Personnalité  bas-droite    Perspective (aussi appelée Vision)

La COULEUR (1 à 6) choisit le nom dans VARIABLE_COLOR_NAMES ; le TON (1 à 6) décide du côté
de la flèche (1 à 3 vers la gauche, 4 à 6 vers la droite) et du sous-libellé gauche/droite
de VARIABLE_COLOR_SIDES.

Chaque nom est un couple (français, anglais).
"""

# ---------------------------------------------------------------- titres des flèches

# À valider par Adrien. Titre court, affiché sous la flèche du SVG (variable_labels=true)
# et en tête du libellé lisible du JSON.
ARROW_TITLES = {
    "determination": "Digestion",       # aussi appelée « Détermination »
    "environment": "Environnement",
    "motivation": "Motivation",
    "perspective": "Perspective",       # aussi appelée « Vision »
}

# À valider par Adrien. Libellé lisible de chaque flèche (champ « label » du JSON).
# Mots-clés : titre, couleur, cote (sous-libellé gauche/droite), opposee (couleur opposée).
LABEL_FORMATS = {
    "determination": "{titre} : {couleur} {cote}",     # ex. « Digestion : Son Aigu »
    "environment": "{titre} : {couleur} {cote}",       # ex. « Environnement : Montagnes Passif »
    "motivation": "{titre} : {couleur}",               # ex. « Motivation : Besoin »
    "perspective": "{titre} : {couleur} / {opposee}",  # ex. « Perspective : Personnel / Pouvoir »
}

# Phrase lue par les lecteurs d'écran pour chaque flèche du SVG. À valider par Adrien.
ARROW_ARIA = "{label}, flèche vers la {sens}"
ARROW_SENS = {"left": "gauche", "right": "droite"}

# ---------------------------------------------------------------- noms des couleurs, tons, sous-libellés

# À valider par Adrien. Les tableaux ci-dessous viennent de hd/data.py, où ils portaient la
# mention « validé le 2026-10-28 » : déplacés ici sans changer un mot.

VARIABLE_LABELS = {
    "design_sun": "Détermination (Digestion)",
    "design_node": "Environnement",
    "personality_sun": "Motivation",
    "personality_node": "Perspective",
}

# Noms des couleurs, des tons et des sous-libellés des variables (tableau validé le
# 2026-10-28). Chaque nom : (français, anglais). Sous-libellés : (gauche, droite), le ton
# décidant du côté (1 à 3 gauche, 4 à 6 droite). Motivation et Perspective n'ont pas de
# sous-libellé : chaque couleur y est liée à une couleur opposée (1↔4, 2↔5, 3↔6).
VARIABLE_COLOR_NAMES = {
    "determination": {1: ("Appétit", "Appetite"), 2: ("Goût", "Taste"), 3: ("Soif", "Thirst"),
                      4: ("Toucher", "Touch"), 5: ("Son", "Sound"), 6: ("Lumière", "Light")},
    "environment": {1: ("Grottes", "Caves"), 2: ("Marchés", "Markets"), 3: ("Cuisines", "Kitchens"),
                    4: ("Montagnes", "Mountains"), 5: ("Vallées", "Valleys"), 6: ("Rivages", "Shores")},
    "motivation": {1: ("Peur", "Fear"), 2: ("Espoir", "Hope"), 3: ("Désir", "Desire"),
                   4: ("Besoin", "Need"), 5: ("Culpabilité", "Guilt"), 6: ("Innocence", "Innocence")},
    "perspective": {1: ("Survie", "Survival"), 2: ("Possibilité", "Possibility"), 3: ("Pouvoir", "Power"),
                    4: ("Envie", "Wanting"), 5: ("Probabilité", "Probability"), 6: ("Personnel", "Personal")},
}
VARIABLE_COLOR_SIDES = {
    "determination": {
        1: (("Consécutif", "Consecutive"), ("Alterné", "Alternating")),
        2: (("Ouvert", "Open"), ("Fermé", "Closed")),
        3: (("Chaud", "Hot"), ("Froid", "Cold")),
        4: (("Calme", "Calm"), ("Nerveux", "Nervous")),
        5: (("Aigu", "High"), ("Grave", "Low")),
        6: (("Directe", "Direct"), ("Indirecte", "Indirect")),
    },
    "environment": {
        1: (("Sélectif", "Selective"), ("Mêlé", "Blending")),
        2: (("Interne", "Internal"), ("Externe", "External")),
        3: (("Humide", "Wet"), ("Sec", "Dry")),
        4: (("Actif", "Active"), ("Passif", "Passive")),
        5: (("Étroite", "Narrow"), ("Large", "Wide")),
        6: (("Naturel", "Natural"), ("Artificiel", "Artificial")),
    },
}

TONE_SENSES = {1: ("Odorat", "Smell"), 2: ("Goût", "Taste"), 3: ("Vision extérieure", "Outer Vision"),
               4: ("Vision intérieure", "Inner Vision"), 5: ("Ressenti", "Feeling"), 6: ("Toucher", "Touch")}
