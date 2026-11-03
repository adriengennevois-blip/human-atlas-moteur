# Moteur Human Design de Human Atlas

Ce moteur calcule une carte Human Design (un « bodygraph ») à partir d'une date, d'une heure et d'un lieu de naissance. Il s'appuie sur la Swiss Ephemeris, avec les fichiers d'éphémérides officiels (`.se1`) et non l'approximation Moshier.

Il fournit :
- les activations Personnalité et Design des 13 corps : porte.ligne, avec ▲ exaltation, ▼ détriment et ★ juxtaposition, plus couleur, ton et base ;
- les canaux, les centres définis, le type, la stratégie, l'autorité, le profil, la définition, la croix d'incarnation et les flèches des variables ;
- un bodygraph en SVG, en deux thèmes de marque : `atlas` (Human Atlas, par défaut) et `gdh` (GoDesignHumain : la même carte qu'`atlas` en or et bleu nuit, sur fond ivoire), plus l'habillage `classique` (code officiel rouge et noir) ;
- une petite API web, que l'application Human Atlas appelle pour afficher la carte de chaque personne.

Le moteur ne stocke rien : il calcule, répond, puis oublie.

## Contenu du dépôt

| Chemin | Rôle |
|---|---|
| `humandesign/hd/` | le moteur : calcul (`chart.py`, `ephemeris.py`, `data.py`, `fixing.py`), heures et lieux (`timeutil.py`), résumé (`signup.py`), dessin de la carte (`bodygraph.py`), toutes ses couleurs (`themes.py`), tous les textes français des variables (`variables_fr.py`) |
| `humandesign/exemples/` | cartes d'exemple (personne fictive), dont `atlas.svg` et `gdh.svg` : la même naissance dans les deux thèmes |
| `humandesign/api_app.py` | l'API web (WSGI, sans framework) |
| `humandesign/passenger_wsgi.py` | point d'entrée pour l'hébergement (Passenger, o2switch) |
| `humandesign/ephe/` | fichiers d'éphémérides de la Swiss Ephemeris (années 1800 à 2400) |
| `humandesign/tests/` | tests automatiques, sur des naissances fictives (valeurs de non-régression). La vérification contre mybodygraph.com se fait sur des thèmes réels gardés hors du dépôt (`tests/references_privees.json`, ignoré par git) |
| `humandesign/exemples/` | cartes d'exemple de 5 naissances fictives, dans les deux habillages |
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
| `POST /v1/chart` | calcule une carte. Exige une clé (voir « Clés, débit et navigateurs ») |
| `POST /v1/composite` | composite de deux personnes : chaque canal et son type de connexion, centres et type de l'ensemble, carte SVG. Exige la même clé |
| `POST /v1/transit` | transits d'un instant (par défaut : maintenant), et leur superposition avec un thème natal. Exige la même clé |
| `GET /v1/transits/day?date=AAAA-MM-JJ&tz=Europe/Paris` | heure de chaque changement de porte et de ligne de la journée, à la minute. Exige la même clé |
| `POST /v1/return` | retours d'une année : solaire, de Saturne, de Chiron, opposition d'Uranus, avec le thème de chaque passage. Exige la même clé |
| `POST /v1/group` | groupe de 3 à 5 personnes : canaux et centres du groupe, qui apporte quoi, connexions deux à deux. Exige la même clé |
| `POST /v1/transit/chart` | un transit posé sur une carte : positions des 13 corps (sens direct ou rétrograde), portes, canaux et centres que le transit active dans la carte, carte SVG avec le transit en pointillé. Exige une clé |
| `POST /v1/ingresses` | la frise : changements de porte et de ligne de chaque corps sur un intervalle (1 an au plus), à la seconde, en UTC ; avec une naissance, quand un canal de la personne est complété. Exige une clé |
| `POST /v1/upcoming` | « à venir » : le prochain canal complété ou centre défini par le transit, avec son début et sa fin. Exige une clé |
| `POST /v1/dream` | thème de rêve (Dream Rave) : réservé, répond `501` (`pending_specification`) en attendant sa règle. Exige la même clé |

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

**Thème de la carte (`"theme"`).** La carte SVG existe en deux thèmes de marque, qui ne changent que l'apparence (jamais le calcul) : `atlas` (Human Atlas, par défaut) et `gdh` (GoDesignHumain : exactement la carte `atlas`, même fond à halo doux, mêmes formes, polices, centres et flèches, avec pour seules différences ses couleurs : Design en or, Personnalité en bleu nuit, fond ivoire et champagne, canaux inactifs beige). Pour GoDesignHumain :

```bash
curl -s -X POST https://moteur.humanatlas.fr/v1/chart -H "Authorization: Bearer $ENGINE_API_KEY" -H "Content-Type: application/json" -d '{"date":"2000-01-01","time":"12:00","time_precision":"exacte","place":"Paris, France","name":"Exemple","theme":"gdh"}'
```

La carte est dans le champ `svg` de la réponse. Une autre valeur que `atlas` ou `gdh` répond `422` (`invalid_theme`), de même que `theme` donné avec `skin` (n'en donner qu'un). Les identifiants internes de la carte gdh commencent par `gdh-` : plusieurs cartes, des deux thèmes, peuvent cohabiter dans une même page. Les couleurs des thèmes sont toutes dans `humandesign/hd/themes.py`.

**Variables : les quatre flèches (champ `variables`, toujours renvoyé).** `variables` contient les clés `determination` (Soleil Design, haut-gauche, « Digestion »), `environment` (Nœud Nord Design, bas-gauche), `motivation` (Soleil Personnalité, haut-droite) et `perspective` (Nœud Nord Personnalité, bas-droite, « Vision »). Pour chacune : `orientation` (`left` pour un ton 1, 2 ou 3, `right` pour un ton 4, 5 ou 6), `color` (1 à 6), `tone` (1 à 6), `base` (1 à 5), `title` (ex. `Digestion`) et `label`, un libellé lisible (ex. `Digestion : Son Aigu`, `Perspective : Personnel / Pouvoir`). S'y ajoutent `direction` (`gauche` ou `droite`, comme `details.variables`), le côté et le corps qui portent la flèche (`side`, `planet`), la porte et la ligne, et les noms français et anglais : `color_name`, `tone_name` et, selon la flèche, `color_side` ou `opposite_color_name`. **Tous les textes français sont dans `humandesign/hd/variables_fr.py`**, seul fichier à corriger pour changer un libellé.

**Dessiner les flèches (`"show_variables": true`).** Les quatre flèches sont dessinées de part et d'autre de la Tête, à sa hauteur : deux à gauche (Design : Digestion au-dessus d'Environnement), deux à droite (Personnalité : Motivation au-dessus de Perspective), la pointe tournée vers la gauche ou la droite selon le ton. Elles sont fines (trait de 4 px, pointe effilée, 38 px de long). Leurs couleurs viennent du thème (`variable_design` et `variable_personality` dans `hd/themes.py`), donc or et bleu nuit pour `gdh`, orange et violet pour `atlas`. Le cadre du SVG **ne change pas** (616 × 840) et le reste de la carte ne bouge pas. `"variable_labels": true` écrit le titre sous chaque flèche (Digestion, Environnement, Motivation, Perspective), en petit (8 px) et dans la couleur discrète `variable_label` du thème ; sans `show_variables`, il ne change rien. Les deux valent `false` par défaut, et alors la carte est **identique à l'octet** à celle d'avant ces options. Ce sont des réglages de `/v1/chart` : les autres routes les refusent (`unknown_field`). Exemples : [`humandesign/exemples/atlas-variables.svg`](humandesign/exemples/atlas-variables.svg) et [`humandesign/exemples/gdh-variables.svg`](humandesign/exemples/gdh-variables.svg).

```
curl -s -X POST https://moteur.humanatlas.fr/v1/chart -H "Authorization: Bearer $ENGINE_API_KEY" -H "Content-Type: application/json" -d '{"date":"2000-01-01","time":"12:00","time_precision":"exacte","place":"Paris, France","name":"Exemple","theme":"gdh","show_variables":true,"variable_labels":true}'
```

**Option `"details": true`** (thème complet, pour les produits premium). Sans elle, la réponse est identique. Avec elle, deux champs s'ajoutent (`variables`, décrit plus haut, est renvoyé dans tous les cas, avec ou sans `details`) :

- `activations_details` : pour chaque corps, côté `personality` et `design`, la porte, la ligne, la couleur (1 à 6), le ton (1 à 6), la base (1 à 5), et `stable_minutes` : de combien de minutes l'heure de naissance peut avancer (`before`) ou reculer (`after`) avant que chaque valeur change (`null` : plus de 24 h) ;
- `precision` : `fiable`, `à confirmer` ou `incertain`, selon que le thème (type, autorité, profil, croix, canaux) ou les variables peuvent changer dans la marge de l'heure déclarée (±5 min pour une heure exacte, ±60 min pour une heure approximative).

Ce calcul prend environ 2 secondes : ne le demander que lorsqu'il sert.

**Composite (`/v1/composite`).** Le corps contient `people` (exactement 2 personnes, chacune au format de `/v1/chart`, sans `include_svg`, `skin`, `details`, `show_variables` ni `variable_labels`) et, au besoin, `include_svg`. Pour chaque canal présent dans la composite, `connection` vaut :

- `electromagnetic` (électromagnétique) : chacun a une porte du canal ;
- `compromise` (compromis) : l'un a le canal complet (`holder`), l'autre une seule de ses portes ;
- `dominance` : l'un a le canal complet (`holder`), l'autre aucune de ses portes ;
- `companionship` (compagnonnage) : tous les deux ont le canal.

La réponse donne aussi le type et la définition de la composite, ses centres définis, les centres et les canaux qui n'existent qu'à deux (`centers_only_together`, `channels_only_together`), et un résumé de chaque personne. La carte utilise l'habillage `composite` (vert sauge foncé pour la première personne, framboise pour la seconde), réservé à cette route.

**Transits (`/v1/transit`).** Corps facultatif : `at` (instant ISO 8601 avec fuseau, ex. `2026-10-28T14:00:00Z` ; par défaut, maintenant) et `chart` (un thème natal au format de `/v1/chart`). La réponse donne, pour les 13 corps, porte, ligne, couleur, ton, base et ▲▼★ (évalués entre les planètes du transit), pas de côté Design, ainsi que les canaux et les centres que le transit définit à lui seul (`channels`, `defined_centers`). Vérifié sur HumanDesignApp (transits du 28 octobre 2026 : 13 corps, symboles, canaux et centres identiques). Avec `chart`, `overlay` liste les canaux que le transit complète avec une porte du thème (`completed_channels`), ceux qu'il forme seul (`transit_channels`) et les centres qu'il définit le temps du transit (`temporarily_defined_centers`).

**Vue du jour (`/v1/transits/day`).** Pour chaque corps : sa porte.ligne à 00:00 (heure locale), puis chaque changement de porte ou de ligne avec son heure locale à la minute (`time`) et son instant UTC exact. Les heures sont trouvées par recherche de racine sur la longitude. Une journée de changement d'heure dure 23 h ou 25 h. Cette route ne contient aucune donnée personnelle : une journée calculée est gardée en mémoire et resservie. Elle accepte aussi une clé dédiée, `TRANSITS_API_KEY` (facultative, au moins 32 caractères), qui n'ouvre que cette route : on peut la confier à un autre site sans donner accès aux calculs de naissance.

**Retours (`/v1/return`).** Corps : `chart` (le thème natal, au format de `/v1/chart`), `kind` (`solar`, `saturn`, `chiron` ou `uranus_opposition`) et `year`. La réponse liste tous les passages du retour qui a lieu cette année-là : une planète rétrograde peut repasser trois fois sur le même point, et un retour peut déborder sur l'année voisine. Pour chaque passage : l'instant exact (UTC), si la planète est rétrograde, l'âge, le thème complet de cet instant (même règle qu'une naissance : le Design est l'instant où le Soleil était 88° avant) et sa superposition avec le thème natal. Si l'année n'a pas de passage, `years_with_returns` indique les bonnes années. Les passages dans l'année qui suit la naissance ne sont pas des retours et sont ignorés.

**Groupes (`/v1/group`).** Corps : `people`, de 3 à 5 personnes au format de `/v1/chart` (numérotées à partir de 1, dans l'ordre). Pour chaque canal du groupe : les personnes qui apportent chacune de ses portes (`gates`), celles qui ont le canal complet (`holders`), et s'il n'existe qu'ensemble (`only_together`). La réponse donne aussi les centres et canaux qui n'existent qu'ensemble, et la composite de chaque paire (`pairs`, comme `/v1/composite`). La Penta n'est pas encore calculée : `penta.status` vaut `pending_rules` en attendant ses règles.

**Clés de contenu (option `"content_keys": true` de `/v1/chart`).** Pour chaque élément du thème, une clé stable à laquelle rattacher un texte d'interprétation : `type.generator`, `authority.sacral`, `profile.5-1`, `definition.triple-split`, `cross.left-angle.plane.2`, `center.throat.defined` ou `center.throat.open`, `gate.24`, `gate.24.line.6`, `channel.24-61`, `variable.determination.right`, `variable.determination.color-3`. La liste complète des 756 clés possibles est dans [`humandesign/content-keys.json`](humandesign/content-keys.json) (régénérée par `python -m hd.content_keys > content-keys.json`). **Ce dépôt ne contient aucun texte d'interprétation** : les textes appartiennent à leur auteur et sont gardés ailleurs, dans un dépôt privé.

**Clés, débit et navigateurs.** Toute route (sauf `GET /` et `GET /source`) exige une clé d'API, jamais dans le dépôt : des variables d'environnement du serveur.
- **Une clé par client** : `API_KEY_ATLAS`, `API_KEY_GDH`… (tout nom `API_KEY_<CLIENT>`, au moins 32 caractères), envoyée dans l'en-tête `X-API-Key`. Sans clé, ou avec une mauvaise : `401`.
- **Transition (Human Atlas ne change pas)** : tant que `REQUIRE_API_KEY` n'est pas `true`, l'ancienne clé `ENGINE_API_KEY` (en-tête `Authorization: Bearer`) reste acceptée. Avec `REQUIRE_API_KEY=true`, seules les clés par client ouvrent le service. Un appel **sans clé** n'est jamais accepté (il ne l'était déjà pas avant).
- **Débit** : 120 requêtes par minute et par client (`RATE_LIMIT_PER_MINUTE`, `0` pour désactiver), puis `429` (`rate_limited`) avec l'en-tête `Retry-After`. Les erreurs `401` ne comptent pas. L'ancienne clé de la transition n'est pas limitée. Le décompte est tenu par processus de l'hébergeur.
- **Navigateurs** : le moteur n'est appelé que par des serveurs. Aucun en-tête CORS n'est envoyé, et tout appel portant un en-tête `Origin` (donc venu d'un navigateur) est refusé en `403` (`browser_not_allowed`).
- **Journaux** : jamais de date, d'heure ni de lieu de naissance (seul le type d'erreur est journalisé).

**Transit posé sur une carte (`/v1/transit/chart`).** Corps : `chart` (la naissance, au format de `/v1/chart`), `at` (instant ISO 8601 avec fuseau ; par défaut maintenant), `theme` (`atlas` ou `gdh`), `include_svg` (`true` par défaut), `show_variables` et `variable_labels` (pour la carte SVG). Réponse : `positions` (pour chaque corps : porte, ligne, couleur, ton, base, `fixing`, `retrograde`), `activates` (`gates` : chaque porte du transit avec ses corps et `in_natal` ; `channels_completed` : une porte du transit et une de la carte ; `channels_transit_only` ; `centers_newly_defined` ; `centers_defined`) et `svg`. Dans le SVG, le transit est **distinct de la naissance** : un anneau autour de chaque porte activée, un pointillé sur la moitié de canal, une teinte et un contour en tirets sur un centre défini par le transit. Les couleurs viennent du thème (clés `transit…` de `hd/themes.py`) ; gdh hérite d'atlas. `/v1/transit` ne change pas.

**Frise (`/v1/ingresses`).** Corps : `from` et `to` (instants ISO 8601 avec fuseau ; **366 jours au plus**, sinon `400`), `level` (`line` par défaut : portes et lignes ; `gate` : portes seulement), et facultativement `chart` (une naissance). Réponse : pour chaque corps (Terre et Nœud Sud compris), `at_start` (porte.ligne au début) puis `changes` : `utc` (à la seconde, UTC), `kind` (`gate` ou `line`), `from`, `to`, `retrograde`. Avec `chart` : `person_events`, les moments où un canal de la personne est complété par le transit (`kind: "channel"`) ou un centre défini par lui (`kind: "center"`), avec `start_utc` et `end_utc` (`null` et `started_before` / `open_ended` quand l'événement dépasse la fenêtre). Les ingressions ne dépendent de personne : elles sont calculées par jour UTC et gardées en mémoire, donc des fenêtres qui se recouvrent partagent leur calcul. Mesuré : 28 jours en 0,03 s, 1 an en 0,35 s (à froid, sur un ordinateur ; les ingressions sont vérifiées contre les éphémérides et contre `/v1/transits/day`).

**À venir (`/v1/upcoming`).** Corps : `chart`, `at` (par défaut maintenant), `days` (7 par défaut, 14 au plus). Réponse : `next` (le tout premier événement de la fenêtre), `next_channel`, `next_center`, `upcoming` (tous), `current` (ce qui est déjà en cours). Chaque événement : `kind`, `channel` (avec `natal_gates` et `transit_gates`) ou `center`, `start_utc`, `end_utc`, `duration_hours`.

**Fiche de lecture (option `"reading": true` de `/v1/chart`).** Des **données** structurées, aucun texte d'interprétation. `reading.entries` : une entrée par rubrique, chacune avec un `id` stable auquel le site rattache les textes d'Adrien : `channels` (canaux définis : numéros, nom français, circuit), `type`, `strategy`, `authority`, `profile`, `definition`, `cross`, `signature`, `not_self_theme`, `centers.defined`, `centers.open`, puis pour chaque flèche (`digestion`, `environment`, `motivation`, `perspective`) `.orientation`, `.color`, `.tone`, `.subcategory` (Digestion et Environnement : le côté du sous-libellé que décide le ton) et `.base`, enfin deux rubriques **sans calcul**, `relations.me_vs_others` (statut `pending_statistics`) et `sleep.rhythm` (statut `pending_rules`, avec seulement les données brutes : type, aura, centres définis et ouverts). `reading.to_validate` liste ce qui reste à valider par Adrien. Les noms français sont dans `humandesign/hd/variables_fr.py` et `humandesign/hd/reading_fr.py`.

**Vérifications.** Les portes, lignes et flèches sont comparées à des applis de référence (mybodygraph, HumanDesignApp). Les couleurs et tons des variables ont été contrôlés sur un thème. **Les bases ne sont vérifiées par aucune appli de référence** (aucune ne les affiche) : seule leur cohérence interne est testée (les 69 120 bases du cercle se suivent, et basculent avec le ton, la couleur, la ligne et la porte aux frontières).

## Précision

- **Heure locale vers UTC** : base IANA tzdata historique (`zoneinfo`), qui couvre l'heure d'été, l'heure allemande en France de 1940 à 1944, l'absence d'heure d'été en France de 1946 à 1975 et les règles locales des États-Unis. Une heure qui n'a pas existé (saut d'heure) ou qui a existé deux fois est signalée.
- **Design** : l'instant exact où le Soleil se trouvait 88° d'arc solaire avant sa position de naissance, calculé par itération de Newton à 1e-10° près.
- **Nœuds lunaires** : nœud vrai (True Node), comme Jovian Archive et mybodygraph.
- **Roue** : la porte 41 commence à 302° (2° Verseau). Une porte fait 5,625° et une ligne 0,9375°.
- **Validation** : 5 thèmes réels relevés sur mybodygraph.com (130 activations, triangles ▲▼★ compris) sont identiques. Ce sont des personnes réelles : leurs naissances restent hors du dépôt public, dans un fichier local ignoré par git ; les tests publics utilisent des naissances fictives.

## Licences

- **Le moteur** (tout le code de ce dépôt) : © 2026 Human Atlas, sous licence **GNU Affero General Public License v3** (AGPL v3, ou toute version ultérieure). Texte complet : [LICENSE](LICENSE). Si vous faites tourner ce moteur, même modifié, sur un serveur pour d'autres personnes, vous devez leur donner accès à son code source.
- **La Swiss Ephemeris** (bibliothèque pyswisseph et fichiers `humandesign/ephe/*.se1`) : © Astrodienst AG, Zurich (Suisse), distribuée sous licence AGPL ou sous licence commerciale d'Astrodienst. Ce dépôt l'utilise sous AGPL.
- **Les polices de l'habillage « atlas »** (`humandesign/hd/fonts/`) : sous-ensembles de Instrument Serif (© 2022 The Instrument Serif Project Authors), Jost (© 2020 The Jost Project Authors) et Space Grotesk (© 2020 The Space Grotesk Project Authors), toutes sous SIL Open Font License 1.1. Voir [OFL.txt](humandesign/hd/fonts/OFL.txt) et les textes complets des licences : [Instrument Serif](humandesign/hd/fonts/OFL-1.1-InstrumentSerif.txt), [Jost](humandesign/hd/fonts/OFL-1.1-Jost.txt), [Space Grotesk](humandesign/hd/fonts/OFL-1.1-SpaceGrotesk.txt).
- **La table des exaltations et détriments** (`humandesign/hd/fixing_table.json`) : issue de [SharpAstrology.HumanDesign](https://github.com/CReizner/SharpAstrology.HumanDesign), © 2023 Christian Reizner, sous licence MIT. Voir [fixing_table.LICENSE](humandesign/hd/fixing_table.LICENSE).
