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
  gdh        GoDesignHumain : marbre, or et ciel nocturne
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
    "embed_fonts": True, "legend": True,
}

# Human Atlas, une couleur par personne à la place de Design / Personnalité
# (personne A : bleu canard, personne B : framboise). Réservé à /v1/composite.
COMPOSITE = {**ATLAS, "design": "#13777b", "personality": "#c2416b",
             "design_text": "#13777b", "personality_text": "#c2416b",
             "legend": False, "name_gradient": False}

# GoDesignHumain : marbre ivoire, or (Design, l'inconscient) et bleu nuit (Personnalité,
# le conscient) ; centres définis aux couleurs officielles. Les textes en couleur utilisent la teinte la plus foncée de chaque
# dégradé, pour rester lisibles sur l'ivoire.
# Veinage du fond.
GDH_MARBLE = Marble("marbre", color=(0.55, 0.50, 0.42), opacity=0.12)
GDH = {
    **ATLAS,
    "id_prefix": "gdh",
    "design": Gradient("or", ((0, "#8C6A2E"), (1, "#6B5020"))),  # or bronze, assez foncé pour des numéros ivoire
    "personality": Gradient("nuit", ((0, "#2B3550"), (1, "#141A2B"))),
    "design_text": "#8C6A2E", "personality_text": "#2B3550",
    "both": "stripes", "both_dash": "3.2 3.2",
    "channel_inactive": "#E6DED0", "channel_edge": None,
    "center_open": "#FBF8F1", "center_open_stroke": "#C9A45C",
    "center_stroke": "#8C6A2E",
    # Centres définis : couleurs officielles Human Design, celles du thème classique.
    "center_defined": CLASSIQUE["center_defined"],
    "center_glow": False, "center_texture": None,
    # Numéros sur un centre défini ou une pastille : ivoire ou brun, le plus contrasté
    # avec la couleur réelle dessous (voir text_on).
    "gate_on": None, "gate_text_on": "auto",
    "gate_text": "#3A3326", "gate_text_defined": "auto", "gate_text_defined_opacity": None,
    "text_choices": ("#FBF8F1", "#3A3326"),
    "text": "#3A3326", "muted": "#6E6452",
    "background": {"kind": "marble", "color": "#F6F1E7", "texture": GDH_MARBLE},
    "legend_design": "or", "legend_personality": "bleu nuit",
}

THEMES = {"classique": CLASSIQUE, "atlas": ATLAS, "composite": COMPOSITE, "gdh": GDH}

# Thèmes que l'API propose pour un thème individuel (paramètre « theme »).
PUBLIC_THEMES = ("atlas", "gdh")


def solid(paint) -> str:
    """Une couleur unie : la première teinte d'un dégradé."""
    return paint.first if isinstance(paint, Gradient) else paint


def color_at(paint, y: float, height: float) -> str:
    """Couleur réelle d'une peinture à la hauteur y (dégradé « page » interpolé)."""
    if not isinstance(paint, Gradient):
        return paint
    t = min(max(y / height, 0.0), 1.0)
    stops = paint.stops
    for (o0, c0), (o1, c1) in zip(stops, stops[1:]):
        if t <= o1:
            k = 0 if o1 == o0 else (t - o0) / (o1 - o0)
            a, b = (int(c0[i:i + 2], 16) for i in (1, 3, 5)), (int(c1[i:i + 2], 16) for i in (1, 3, 5))
            return "#" + "".join(f"{round(x + (z - x) * k):02x}" for x, z in zip(a, b))
    return stops[-1][1]


def contrast(a: str, b: str) -> float:
    """Rapport de contraste WCAG 2 entre deux couleurs « #rrggbb »."""
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def text_on(backgrounds, choices) -> str:
    """Parmi choices, la couleur de texte dont le pire contraste sur ces fonds est le meilleur."""
    return max(choices, key=lambda c: min(contrast(c, b) for b in backgrounds))


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
