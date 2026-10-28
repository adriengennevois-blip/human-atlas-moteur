# Moteur Human Design de Human Atlas

Ce moteur calcule une carte Human Design (un « bodygraph ») à partir d'une date, d'une heure et d'un lieu de naissance. Il s'appuie sur la Swiss Ephemeris, avec les fichiers d'éphémérides officiels (`.se1`) et non l'approximation Moshier.

Il fournit :
- les activations Personnalité et Design des 13 corps : porte.ligne, avec ▲ exaltation, ▼ détriment et ★ juxtaposition, plus couleur, ton et base ;
- les canaux, les centres définis, le type, la stratégie, l'autorité, le profil, la définition, la croix d'incarnation et les flèches des variables ;
- un bodygraph en SVG, en deux habillages : `atlas` (couleurs Human Atlas) et `classique` (code officiel rouge et noir) ;
- une petite API web, que l'application Human Atlas appelle pour afficher la carte de chaque personne.

Le moteur ne stocke rien : il calcule, répond, puis oublie.

## Contenu du dépôt

| Chemin | Rôle |
|---|---|
| `humandesign/hd/` | le moteur : calcul (`chart.py`, `ephemeris.py`, `data.py`, `fixing.py`), heures et lieux (`timeutil.py`), résumé (`signup.py`), dessin de la carte (`bodygraph.py`) |
| `humandesign/api_app.py` | l'API web (WSGI, sans framework) |
| `humandesign/passenger_wsgi.py` | point d'entrée pour l'hébergement (Passenger, o2switch) |
| `humandesign/ephe/` | fichiers d'éphémérides de la Swiss Ephemeris (années 1800 à 2400) |
| `humandesign/tests/` | tests automatiques, dont 5 thèmes de référence relevés sur mybodygraph.com |
| `humandesign/exemples/` | cartes d'exemple des 5 thèmes de référence, dans les deux habillages |
| `humandesign/outils/` | `compiler_pyswisseph_linux.py` : fabrique pyswisseph pour un serveur Linux sans compilateur (o2switch) |
| `humandesign/DEPLOIEMENT.md` | guide de mise en ligne pas à pas |

## Installation

Python 3.10 ou plus récent est nécessaire.

```bash
cd humandesign
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancement

**En ligne de commande :**

```bash
python -m hd --date 2000-01-01 --time 12:00 --place "Paris, France" --name "Exemple" --svg carte.svg
```

- `--place` : lieu géocodé via OpenStreetMap (nécessite Internet). Sans Internet, utilisez `--lat` et `--lon`, ou `--tz Europe/Paris`.
- `--fold 1` : pour une heure qui a existé deux fois lors du passage à l'heure d'hiver, retient la deuxième occurrence.

**Les tests :**

```bash
python -m pytest -q
```

**L'API, sur votre ordinateur :**

```bash
export ENGINE_API_KEY="$(openssl rand -hex 32)"
python -c "from wsgiref.simple_server import make_server; import api_app; make_server('127.0.0.1', 8000, api_app.application).serve_forever()"
```

Pour la mise en ligne, voir [humandesign/DEPLOIEMENT.md](humandesign/DEPLOIEMENT.md).

## L'API

| Adresse | Rôle |
|---|---|
| `GET /` | renvoie `ok` (le service fonctionne) |
| `GET /source` | renvoie l'adresse de ce dépôt (code source du service, obligation de l'AGPL) |
| `POST /v1/chart` | calcule une carte. Exige l'en-tête `Authorization: Bearer <clé>` |

**Exemple d'appel** (personne fictive) :

```bash
curl -s -X POST https://moteur.humanatlas.fr/v1/chart -H "Authorization: Bearer $ENGINE_API_KEY" -H "Content-Type: application/json" -d '{"date":"2000-01-01","time":"12:00","time_precision":"exacte","place":"Paris, France","name":"Exemple","include_svg":false}'
```

**Réponse** (abrégée) :

```json
{
  "type": "Manifesting Generator",
  "type_fr": "M-Générateur",
  "authority": "Emotional",
  "authority_fr": "Émotionnelle (Plexus solaire)",
  "profile": "1/4",
  "profile_label": "1/4 (Investigateur / Opportuniste)",
  "cross": "Right Angle Cross of Tension 4",
  "channels": ["10-34", "13-33", "26-44", "27-50", "30-41"],
  "defined_centers": ["throat", "g", "heart", "sacral", "solar_plexus", "spleen", "root"],
  "definition": 2,
  "active_gates": {"2": ["design"], "5": ["personality"], "…": "…"},
  "summary": "M-Générateur à autorité émotionnelle (Plexus solaire), profil 1/4 (Investigateur / Opportuniste)",
  "place_resolved": {"name": "Paris, Île-de-France, France métropolitaine, France", "lat": 48.8534951, "lon": 2.3483915, "tz": "Europe/Paris"},
  "time_warning": null,
  "details": {
    "birth_utc": "2000-01-01T11:00:00+00:00",
    "cross_gates": "38/39 | 48/21",
    "personality": {"sun": {"gate": 38, "line": 1, "color": 6, "tone": 2, "base": 4, "fixing": "", "label": "38.1", "longitude": 280.326442}, "…": "…"},
    "design": {"…": "…"},
    "…": "…"
  }
}
```

Le détail des champs d'entrée et de sortie, et des codes d'erreur, se trouve dans [DEPLOIEMENT.md](humandesign/DEPLOIEMENT.md).

**Option `"details": true`** (thème complet, pour les produits premium). Sans elle, la réponse est identique. Avec elle, trois champs s'ajoutent :

- `activations_details` : pour chaque corps, côté `personality` et `design`, la porte, la ligne, la couleur (1 à 6), le ton (1 à 6), la base (1 à 5), et `stable_minutes` : de combien de minutes l'heure de naissance peut avancer (`before`) ou reculer (`after`) avant que chaque valeur change (`null` : plus de 24 h) ;
- `variables` : les quatre flèches (`determination`, `environment`, `motivation`, `perspective`), avec leur direction (`gauche` ou `droite`) et la couleur, le ton et la base qui les portent ;
- `precision` : `fiable`, `à confirmer` ou `incertain`, selon que le thème (type, autorité, profil, croix, canaux) ou les variables peuvent changer dans la marge de l'heure déclarée (±5 min pour une heure exacte, ±60 min pour une heure approximative).

Ce calcul prend environ 2 secondes : ne le demander que lorsqu'il sert.

**Vérifications.** Les portes, lignes et flèches sont comparées à des applis de référence (mybodygraph, HumanDesignApp). Les couleurs et tons des variables ont été contrôlés sur un thème. **Les bases ne sont vérifiées par aucune appli de référence** (aucune ne les affiche) : seule leur cohérence interne est testée (les 69 120 bases du cercle se suivent, et basculent avec le ton, la couleur, la ligne et la porte aux frontières).

## Précision

- **Heure locale vers UTC** : base IANA tzdata historique (`zoneinfo`), qui couvre l'heure d'été, l'heure allemande en France de 1940 à 1944, l'absence d'heure d'été en France de 1946 à 1975 et les règles locales des États-Unis. Une heure qui n'a pas existé (saut d'heure) ou qui a existé deux fois est signalée.
- **Design** : l'instant exact où le Soleil se trouvait 88° d'arc solaire avant sa position de naissance, calculé par itération de Newton à 1e-10° près.
- **Nœuds lunaires** : nœud vrai (True Node), comme Jovian Archive et mybodygraph.
- **Roue** : la porte 41 commence à 302° (2° Verseau). Une porte fait 5,625° et une ligne 0,9375°.
- **Validation** : les 5 thèmes de référence de mybodygraph.com (130 activations, triangles ▲▼★ compris) sont identiques.

## Licences

- **Le moteur** (tout le code de ce dépôt) : © 2026 Human Atlas, sous licence **GNU Affero General Public License v3** (AGPL v3, ou toute version ultérieure). Texte complet : [LICENSE](LICENSE). Si vous faites tourner ce moteur, même modifié, sur un serveur pour d'autres personnes, vous devez leur donner accès à son code source.
- **La Swiss Ephemeris** (bibliothèque pyswisseph et fichiers `humandesign/ephe/*.se1`) : © Astrodienst AG, Zurich (Suisse), distribuée sous licence AGPL ou sous licence commerciale d'Astrodienst. Ce dépôt l'utilise sous AGPL.
- **Les polices de l'habillage « atlas »** (`humandesign/hd/fonts/`) : sous-ensembles de Instrument Serif (© 2022 The Instrument Serif Project Authors), Jost (© 2020 The Jost Project Authors) et Space Grotesk (© 2020 The Space Grotesk Project Authors), toutes sous SIL Open Font License 1.1. Voir [OFL.txt](humandesign/hd/fonts/OFL.txt) et les textes complets des licences : [Instrument Serif](humandesign/hd/fonts/OFL-1.1-InstrumentSerif.txt), [Jost](humandesign/hd/fonts/OFL-1.1-Jost.txt), [Space Grotesk](humandesign/hd/fonts/OFL-1.1-SpaceGrotesk.txt).
- **La table des exaltations et détriments** (`humandesign/hd/fixing_table.json`) : issue de [SharpAstrology.HumanDesign](https://github.com/CReizner/SharpAstrology.HumanDesign), © 2023 Christian Reizner, sous licence MIT. Voir [fixing_table.LICENSE](humandesign/hd/fixing_table.LICENSE).
