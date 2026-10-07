# Mettre le moteur HD en ligne : guide pas à pas

**Ce que ça fait :** l'app `real-world-weavers` envoie au moteur une date, une heure et un lieu de naissance. Le moteur, hébergé chez o2switch, calcule le thème (type, autorité, profil, croix, canaux…) et renvoie le bodygraph en SVG. Il ne stocke rien : il calcule, répond, puis oublie.

Compte **30 minutes**, une seule fois. Quatre étapes, dans cet ordre.

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

## 2. o2switch : mettre le moteur en ligne (20 min)

Voici comment il a été installé, pour pouvoir le refaire.

**a. Créer le sous-domaine :** cPanel → *Domaines* → *Créer un nouveau domaine* → `moteur.humanatlas.fr`. Le DNS de `humanatlas.fr` étant chez o2switch, l'enregistrement est créé automatiquement.

**b. Activer le HTTPS :** cPanel → *Let's Encrypt™ SSL* → ligne `moteur.humanatlas.fr` → *+ Issue* → *Issue*. (AutoSSL n'est pas inclus dans l'offre : c'est cet outil qu'il faut utiliser. Le renouvellement est automatique.)

**c. Récupérer le code :** en SSH (voir plus bas pour l'accès), cloner le dépôt public **hors** de `public_html` :

```bash
git clone https://github.com/adriengennevois-blip/human-atlas-moteur.git ~/moteur-hd
```

**d. Créer l'application :** cPanel → *Setup Python App* → *Create Application*.

| Champ | Valeur |
|---|---|
| Python version | 3.12 |
| Application root | `moteur-hd/humandesign` |
| Application URL | `moteur.humanatlas.fr` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

Variables d'environnement, dans la même page (*Add Variable*) :

| Nom | Valeur |
|---|---|
| `ENGINE_API_KEY` | la clé de l'étape 1 |
| `SOURCE_URL` | `https://github.com/adriengennevois-blip/human-atlas-moteur` |

`SOURCE_URL` sert à respecter la licence AGPL : le moteur doit indiquer à ceux qui l'utilisent où trouver son code source. Il la renvoie sur `https://moteur.humanatlas.fr/source`. Sans elle, cette adresse répond `503`.

⚠️ **cPanel remplace `passenger_wsgi.py` par son propre modèle** à la création. Il faut ensuite remettre le nôtre : `cd ~/moteur-hd && git checkout -- humandesign/passenger_wsgi.py`.

⚠️ cPanel range les variables dans `~/moteur.humanatlas.fr/.htaccess`, **clé comprise**. Ce fichier n'est pas lisible depuis le web (erreur 403), mais ne l'affiche jamais et ne le copie jamais ailleurs.

**e. Installer les dépendances.** o2switch **interdit le compilateur C**, et `pyswisseph` n'existe pas en version précompilée pour Linux. `pip install -r requirements.txt` échoue donc avec « gcc: Permission denied ». La solution :

1. Sur un Mac (ou tout autre ordinateur), fabriquer le module Linux avec le script fourni :
   ```bash
   pip install ziglang
   ssh <identifiant-cpanel>@<serveur>.o2switch.net 'tar czf - -C /opt/alt/python312/include python3.12' > pyinc.tgz
   mkdir pyinc && tar xzf pyinc.tgz -C pyinc
   python humandesign/outils/compiler_pyswisseph_linux.py --include pyinc/python3.12 --sortie dist/
   ```
2. Envoyer `dist/pyswisseph-2.10.3.2-cp312-cp312-linux_x86_64.whl` sur le serveur (par exemple dans `~/moteur-wheels/`), puis, en SSH :
   ```bash
   source ~/virtualenv/moteur-hd/humandesign/3.12/bin/activate
   pip install ~/moteur-wheels/pyswisseph-2.10.3.2-cp312-cp312-linux_x86_64.whl
   cd ~/moteur-hd/humandesign && pip install -r requirements.txt
   python -m pytest -q -p no:cacheprovider     # doit afficher « 111 passed » (ou plus)
   ```
3. cPanel → *Setup Python App* → l'application → *Restart*.

**f. Tout forcer en HTTPS :** en tête de `~/moteur.humanatlas.fr/.htaccess`, **au-dessus** des blocs « CLOUDLINUX », ajouter :

```apache
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

Ainsi, la clé ne peut jamais circuler en clair par erreur.

**g. Vérifier :** ouvre `https://moteur.humanatlas.fr` dans ton navigateur. Tu dois lire :
> ok

**Accès SSH :** cPanel → *Autorisation SSH* → ajouter son adresse IP (port 22). Puis, depuis le Mac :

```bash
ssh <identifiant-cpanel>@<serveur>.o2switch.net
```

### Mettre le moteur à jour

Après une modification poussée sur GitHub, en SSH :

```bash
cd ~/moteur-hd && git pull
source ~/virtualenv/moteur-hd/humandesign/3.12/bin/activate && cd humandesign && python -m pytest -q -p no:cacheprovider
touch ~/moteur-hd/humandesign/tmp/restart.txt
```

La dernière ligne redémarre l'application (équivalent du bouton *Restart*).

---

## 3. Tester avec `curl` (2 min)

Dans le Terminal du Mac, remplace `TA_CLE` par la clé de l'étape 1 :

```bash
curl -s -X POST https://moteur.humanatlas.fr/v1/chart -H "Authorization: Bearer TA_CLE" -H "Content-Type: application/json" -d '{"date":"2000-01-01","time":"12:00","time_precision":"exacte","place":"Paris, France","name":"Exemple","include_svg":false}'
```

Tu dois recevoir un JSON qui commence par `{"type": "Manifesting Generator", "type_fr": "M-Générateur", "authority": "Emotional", …` avec `"profile": "1/4"` (personne fictive née le 1er janvier 2000 à midi, à Paris).

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

`type`, `type_fr`, `authority`, `authority_fr`, `profile`, `profile_label`, `cross`, `channels`, `defined_centers`, `definition`, `active_gates`, `summary`, `place_resolved`, `time_warning`, `details`, et `svg` si demandé.

`details` contient le thème complet : `birth_utc`, `design_utc`, `cross_gates`, `quarter`, `variables` (les 4 flèches), et pour `personality` comme pour `design`, chacune des 13 planètes avec `gate`, `line`, `color`, `tone`, `base`, `fixing` (▲ ▼ ★), `label` (ex. `6.5▼`) et `longitude`.

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
