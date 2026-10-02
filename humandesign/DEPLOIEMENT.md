# Mettre le moteur HD en ligne : guide pas à pas

**Ce que ça fait :** l'app `real-world-weavers` envoie au moteur une date, une heure et un lieu de naissance. Le moteur, hébergé chez o2switch, calcule le thème (type, autorité, profil, croix, canaux…) et renvoie le bodygraph en SVG. Il ne stocke rien : il calcule, répond, puis oublie.

Compte **20 minutes**, une seule fois. Quatre étapes, dans cet ordre.

---

## 1. Créer la clé secrète du moteur (2 min)

L'app et le moteur partagent une clé secrète. Sans elle, le moteur refuse tout appel (réponse `401`). Si la clé manque côté serveur, ou si elle fait moins de 32 caractères, le moteur refuse **tous** les appels.

Génère une clé aléatoire de 64 caractères. Sur Mac, ouvre le Terminal et tape :

```bash
openssl rand -hex 32
```

Copie le résultat (par exemple `3f9a…`, 64 caractères). Range-le dans ton gestionnaire de mots de passe. **Tu devras donner cette même clé à l'app** (étape 4).

Ne mets jamais cette clé dans le code, dans un dépôt git ou dans le navigateur. L'app doit appeler le moteur depuis son serveur (fonction serveur TanStack Start ou fonction Supabase), jamais depuis la page web.

---

## 2. o2switch : mettre le moteur en ligne (15 min)

**a. Créer un sous-domaine :** cPanel → *Domaines* (ou *Sous-domaines*) → `moteur.humanatlas.fr`.
Le HTTPS s'active tout seul en quelques minutes. Vérifie-le dans *SSL/TLS Status* si besoin.

**b. Envoyer les fichiers :** cPanel → *Gestionnaire de fichiers*.
- Crée un dossier `moteur-hd` à la racine de ton compte, **pas** dans `public_html`.
- Envoie le zip dedans et extrais-le.
- Le contenu du dossier `humandesign` (les dossiers `hd/`, `ephe/`, les fichiers `api_app.py`, `passenger_wsgi.py`…) doit se retrouver directement dans `moteur-hd`.

**c. Créer l'application :** cPanel → *Setup Python App* → *Create Application*.

| Champ | Valeur |
|---|---|
| Python version | 3.11 ou plus récent (3.10 au minimum) |
| Application root | `moteur-hd` |
| Application URL | `moteur.humanatlas.fr` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

**d. Variable d'environnement**, dans la même page (*Add Variable*) :

| Nom | Valeur |
|---|---|
| `ENGINE_API_KEY` | la clé de l'étape 1 |
| `SOURCE_URL` | l'adresse du dépôt public, par exemple `https://github.com/<ton-compte>/human-atlas-moteur` |

`SOURCE_URL` sert à respecter la licence AGPL : le moteur doit indiquer à ceux qui l'utilisent où trouver son code source. Il la renvoie sur `https://moteur.humanatlas.fr/source`. Sans elle, cette adresse répond `503`.

Clique sur *Create*.

**e. Installer les dépendances :** dans l'application, champ *Configuration files* → saisis `requirements.txt` → *Add*, puis *Run Pip Install*. Clique ensuite sur *Restart*.

**f. Vérifier :** ouvre `https://moteur.humanatlas.fr` dans ton navigateur. Tu dois lire :
> ok

---

## 3. Tester avec `curl` (2 min)

Dans le Terminal du Mac, remplace `TA_CLE` par la clé de l'étape 1 :

```bash
curl -s -X POST https://moteur.humanatlas.fr/v1/chart -H "Authorization: Bearer TA_CLE" -H "Content-Type: application/json" -d '{"date":"2000-01-01","time":"12:00","time_precision":"exacte","place":"Paris, France","name":"Exemple","include_svg":false}'
```

Tu dois recevoir un JSON qui commence par `{"type": "Manifesting Generator", "type_fr": "Générateur Manifesteur", "authority": "Emotional", …` avec `"profile": "1/4"` (personne fictive née le 1er janvier 2000 à midi, à Paris).

Vérifie aussi `https://moteur.humanatlas.fr/source` : il doit afficher l'adresse du dépôt public.

Le premier appel après un redémarrage peut prendre une dizaine de secondes. Les suivants sont rapides.

**Si ça ne marche pas :**
- `401` : la clé envoyée n'est pas celle de `ENGINE_API_KEY`, ou la variable n'est pas réglée. Après avoir modifié une variable, clique sur *Restart*.
- `503` avec `geocoding_unavailable` : le service OpenStreetMap ne répond pas. Réessaie, ou envoie `tz` (ex. `"Europe/Paris"`) ou `lat` + `lon` à la place de `place`.
- Page d'erreur o2switch (pas du JSON) : l'application ne démarre pas. Le journal se trouve dans cPanel → *Setup Python App* → ton application → fichier de log.

---

## 4. Brancher l'app (côté real-world-weavers)

- Ajoute la même clé dans les secrets du serveur de l'app, par exemple `ENGINE_API_KEY` dans les variables d'environnement, ou dans un secret Supabase si l'appel part d'une fonction Supabase.
- L'app appelle `POST https://moteur.humanatlas.fr/v1/chart` avec l'en-tête `Authorization: Bearer <clé>`.

### Ce que l'app envoie

| Champ | Contenu |
|---|---|
| `date` | `AAAA-MM-JJ` (entre 1801 et 2399) |
| `time` | `HH:MM` |
| `time_precision` | `exacte`, `approximative` ou `inconnue` |
| lieu (un seul des trois) | `tz` (fuseau IANA, ex. `Europe/Paris`), ou `lat` + `lon`, ou `place` (texte, ex. `Lyon, France`) |
| `name` | optionnel : le prénom affiché sur la carte (60 caractères maximum) |
| `skin` | `atlas` (par défaut) ou `classique` |
| `include_svg` | `true` (par défaut) ou `false` |

### Ce que le moteur répond

`type`, `type_fr`, `authority`, `authority_fr`, `profile`, `profile_label`, `cross`, `channels`, `defined_centers`, `definition`, `active_gates`, `summary`, `place_resolved`, `time_warning`, et `svg` si demandé.

En cas d'erreur : `{"error": {"code": "…", "message": "…"}}` avec le code HTTP correspondant (`400` entrée invalide, `401` clé, `413` corps de plus de 10 Ko, `422` heure inconnue ou lieu introuvable, `503` géocodage indisponible).

---

## Règles de calcul

- **Heure inconnue** (`time_precision: "inconnue"`) → réponse `422`, pas de calcul. Sans heure, le type et l'autorité peuvent être faux.
- **Heure approximative** → calcul fait, signalé dans `time_warning`.
- **Changement d'heure** → une heure qui n'a pas existé (saut de printemps) ou qui a existé deux fois (retour d'automne) est signalée dans `time_warning`, avec le décalage retenu.
- **Lieu** → trouvé via OpenStreetMap. Le lieu réellement retenu est renvoyé dans `place_resolved`, pour que l'app puisse le montrer et repérer une erreur. Si un autre lieu du même nom se trouve dans un autre fuseau horaire (par exemple Saint-Denis en Île-de-France et Saint-Denis de La Réunion), `place_resolved.ambiguous` vaut `true`, `place_resolved.alternatives` liste les autres lieux, et `time_warning` le signale.
- **Données personnelles** → rien n'est enregistré sur le serveur. Les journaux ne contiennent aucune donnée de naissance.

## Licence

Le moteur est publié sous licence AGPL v3, comme la Swiss Ephemeris qu'il utilise (voir le `README.md` à la racine du dépôt). L'AGPL impose d'offrir le code source à ceux qui utilisent le service : c'est le rôle de `GET /source` et de `SOURCE_URL`. Dans l'app, ajoute un lien visible vers ce code source, par exemple en pied de page ou à côté de la carte (« Code source du moteur »).
