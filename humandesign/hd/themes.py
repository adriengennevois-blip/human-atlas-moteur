# Moteur Human Design de Human Atlas
# Copyright (C) 2026 Human Atlas
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
# modifier selon les termes de la GNU Affero General Public License, version 3,
# publiée par la Free Software Foundation (ou, à votre choix, toute version
# ultérieure). Il est distribué SANS AUCUNE GARANTIE. Voir le fichier LICENSE.

"""Toutes les couleurs des dessins du moteur, en un seul endroit.

Un thème ne change que l'apparence : jamais un calcul (planètes, portes, centres,
canaux). Le gabarit (géométrie) est commun à tous.

Une couleur est soit une chaîne « #rrggbb », soit un Gradient : le dessin le déclare
une fois dans la carte, sous un identifiant préfixé (préfixe de la carte, qui commence
par le nom du thème quand id_prefix est donné, ex. « gdh-hd1a2b3c4d-or »), pour que
plusieurs cartes cohabitent dans une même page.

Thèmes du bodygraph :
  atlas      Human Atlas : Design orange, Personnalité violet, fond « atmosphère »
  classique  code officiel : Design rouge, Personnalité noir, fond blanc
  composite  Human Atlas, une couleur par personne (réservé à /v1/composite)
  gdh        GoDesignHumain : exactement atlas, seules les couleurs changent (or et bleu nuit
             à la place d'orange et de violet, fond ivoire et champagne)

Les quatre flèches des variables (option « show_variables ») utilisent trois clés :
  variable_design        flèches de gauche (Design)
  variable_personality   flèches de droite (Personnalité)
  variable_label         petit libellé sous chaque flèche (option « variable_labels »)

Le transit posé sur une carte (hd.timeline, route /v1/transit/chart) se distingue des activations
de la naissance par un style propre, en pointillé :
  transit                couleur des activations du transit (ni Design, ni Personnalité)
  transit_dash           pointillé posé sur la moitié de canal activée par le transit
  transit_ring           épaisseur de l'anneau autour du numéro d'une porte activée par le transit
  transit_center_dash    contour en tirets d'un centre défini seulement le temps du transit
  transit_center_opacity teinte de ce centre
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Gradient:
    """Dégradé linéaire vertical. units « page » : sur toute la hauteur de la carte (traits
    droits compris, qui n'ont pas de largeur) ; « shape » : sur la forme qui le porte."""
    name: str
    stops: tuple  # ((décalage, couleur), …)
    units: str = "page"

    @property
    def first(self) -> str:
        return self.stops[0][1]


@dataclass(frozen=True)
class Marble:
    """Veinage de marbre : bruit fractal recoloré, à opacité très faible."""
    name: str
    color: tuple            # (r, g, b) des veines, entre 0 et 1
    opacity: float          # opacité maximale des veines (≤ 0,12)
    base_frequency: float = 0.012
    octaves: int = 3
    seed: int = 7


SANS = "Inter, 'Helvetica Neue', Arial, sans-serif"

CLASSIQUE = {
    # Code officiel : rouge = Design, noir = Personnalité.
    "design": "#c62828", "personality": "#1b1b1b",
    "design_text": "#c62828", "personality_text": "#1b1b1b",
    "both": "stripes", "both_dash": "3.2 3.2",
    "channel_inactive": "#ffffff", "channel_edge": "#9e9e9e",
    "center_open": "#ffffff", "center_open_stroke": "#8d8d8d",
    "center_stroke": "#3a3a3a",
    "center_defined": {
        "head": "#f4d03f", "ajna": "#4caf50", "throat": "#a0754d", "g": "#f4d03f",
        "heart": "#d32f2f", "sacral": "#d32f2f", "spleen": "#a0754d",
        "solar_plexus": "#a0754d", "root": "#a0754d",
    },
    "center_glow": False, "center_texture": None,
    "gate_on": "#1b1b1b", "gate_text_on": "#ffffff",
    "gate_text": "#5c5c5c", "gate_text_defined": "#1b1b1b", "gate_text_defined_opacity": 0.62,
    "text": "#1b1b1b", "muted": "#6b6b6b",
    "variable_design": "#c62828", "variable_personality": "#1b1b1b", "variable_label": "#6b6b6b",
    "transit": "#1565c0", "transit_dash": "0.1 5", "transit_ring": 1.6,
    "transit_center_dash": "5 3", "transit_center_opacity": 0.16,
    "background": {"kind": "plain", "color": "#ffffff"},
    "font_num": SANS, "font_title": SANS, "font_text": SANS,
    "embed_fonts": False, "legend": False,
}

ATLAS = {
    # Human Atlas : Design orange, Personnalité violet (couleurs de la marque). Ce n'est
    # pas le code officiel rouge/noir : une légende l'indique sur la carte.
    "design": "#e07a1f",
    "personality": "#6b2fa3",
    "design_text": "#e07a1f", "personality_text": "#6b2fa3",
    "both": "stripes", "both_dash": "3.2 3.2",
    "channel_inactive": "#d6cee2", "channel_edge": None,
    "center_open": "#fbfaff", "center_open_stroke": "#b9aec8",
    "center_stroke": "#ffffff",
    "center_defined": {
        "head": "#efcd78", "ajna": "#8fb39c", "throat": "#c9a481", "g": "#efcd78",
        "heart": "#c45b74", "sacral": "#c45b74", "spleen": "#c9a481",
        "solar_plexus": "#c9a481", "root": "#c9a481",
    },
    "center_glow": True, "center_texture": None,
    "gate_on": None, "gate_text_on": "#ffffff",
    "gate_text": "#8a8096", "gate_text_defined": "#2a2333", "gate_text_defined_opacity": 0.62,
    "text": "#2a2333", "muted": "#5d4f6d",
    "variable_design": "#e07a1f", "variable_personality": "#6b2fa3", "variable_label": "#5d4f6d",
    # Transit : turquoise, distinct de l'orange, du violet et des centres ; gdh l'hérite d'atlas.
    "transit": "#0f8b8d", "transit_dash": "0.1 5", "transit_ring": 1.6,
    "transit_center_dash": "5 3", "transit_center_opacity": 0.18,
    "background": {
        "kind": "atmosphere", "top": "#efebf3", "bottom": "#dcd6e2", "halo": "#ffffff",
        "orbit": "#7b22aa", "dot_violet": "#7b22aa", "dot_orange": "#cd7a18", "veil": "#ffffff",
    },
    "legend_design": "orange", "legend_personality": "violet",
    # Typographie du site : Instrument Serif italique (prénom, en-têtes), Jost (phrase,
    # légende), Space Grotesk (portes, valeurs porte.ligne). Embarquées dans le SVG.
    "font_num": "'Space Grotesk', 'Helvetica Neue', Arial, sans-serif",
    "font_title": "'Instrument Serif', Georgia, serif",
    "font_text": "Jost, 'Helvetica Neue', Arial, sans-serif",
    "num_weights": (600, 500), "name_gradient": True,
    # Dégradé du prénom et du filet de la légende (Design → Personnalité).
    "name_from": "#e07a1f", "name_to": "#6b2fa3",
    "embed_fonts": True, "legend": True,
}

# Human Atlas, une couleur par personne à la place de Design / Personnalité
# (personne A : vert sauge foncé, personne B : framboise), tirées de la palette Atlas.
# Réservé à /v1/composite.
COMPOSITE = {**ATLAS, "design": "#4F8A6B", "personality": "#B8476A",
             "design_text": "#4F8A6B", "personality_text": "#B8476A",
             "legend": False, "name_gradient": False}

# GoDesignHumain : le thème atlas, avec d'autres couleurs et rien d'autre. Même construction
# (halo doux, silhouette lumineuse, orbites et points, lueur des centres, formes, contours,
# polices, tailles, pastilles, flèches des variables, titre, légende) : seules les clés de
# couleur ci-dessous sont remplacées, tout le reste vient d'ATLAS.
#   orange (Design)        → or  : #B8893B (traits, pastilles, flèches), #8C6A2E (textes)
#   violet (Personnalité)  → bleu nuit : #2B3550 (textes et traits)
#   fond lavande           → ivoire et champagne (centre du halo, bords, voile)
#   canaux inactifs        → beige chaud
# Les autres couleurs d'atlas (centres, numéros de portes, texte courant) sont conservées.
GDH = {
    **ATLAS,
    "id_prefix": "gdh",  # préfixe des identifiants internes (pas une couleur) : voir hd.bodygraph
    "design": "#B8893B", "personality": "#2B3550",
    "design_text": "#8C6A2E", "personality_text": "#2B3550",
    "name_from": "#B8893B", "name_to": "#2B3550",
    "channel_inactive": "#E6DED0",
    "variable_design": "#B8893B", "variable_personality": "#2B3550",
    "background": {
        **ATLAS["background"],
        "top": "#F6F1E7", "bottom": "#EFE6D3",   # voile général, bords
        "halo": "#FFFDF8", "veil": "#FFFDF8",     # centre du halo, silhouette lumineuse
        "orbit": "#2B3550",                       # orbites (côté Personnalité)
        "dot_violet": "#2B3550", "dot_orange": "#B8893B",  # points : Personnalité, Design
    },
    "legend_design": "or", "legend_personality": "bleu nuit",
}

THEMES = {"classique": CLASSIQUE, "atlas": ATLAS, "composite": COMPOSITE, "gdh": GDH}

# Thèmes que l'API propose pour un thème individuel (paramètre « theme »).
PUBLIC_THEMES = ("atlas", "gdh")


def solid(paint) -> str:
    """Une couleur unie : la première teinte d'un dégradé."""
    return paint.first if isinstance(paint, Gradient) else paint


MIN_CONTRAST = 4.5  # WCAG 2, texte courant


def text_on(background: str, choices) -> str:
    """Parmi choices, la couleur de texte la plus contrastée avec ce fond (au moins
    MIN_CONTRAST quand l'une y arrive, sinon la meilleure des deux)."""
    return max(choices, key=lambda c: contrast(c, background))


def contrast(a: str, b: str) -> float:
    """Rapport de contraste WCAG 2 entre deux couleurs « #rrggbb »."""
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# Fiche complète de la ligne de commande (hd.svg, « python -m hd --svg ») : fond sombre.
FICHE = {
    "bg": "#2a2a2c", "body": "#3b3b3e", "empty": "#1b1b1c", "red": "#c9554f",
    "white": "#f4f4f4", "muted": "#8f8f93", "text": "#e9e9ea",
    "centers": {
        "head": "#f6f0a6", "ajna": "#6e9e90", "throat": "#5b4642", "g": "#f6f0a6",
        "heart": "#c9554f", "sacral": "#c9554f", "solar_plexus": "#5b4642", "spleen": "#5b4642",
        "root": "#5b4642",
    },
    "label_on_defined": {"head": "#77724f", "g": "#77724f", "ajna": "#dcebe6",
                         "heart": "#f1d6d4", "sacral": "#f1d6d4"},
    "personality_bar": "#555", "gate_badge": "#101010", "gate_badge_text": "#fff",
}
