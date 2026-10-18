# Le workflow de l'organisation — une charte graphique imposée à toutes les images

Démonstration du module 2 de la série « Clic par clic » **Générer des images dans Open WebUI avec
ComfyUI** : dans Open WebUI, l'utilisateur ne choisit que sa description ; tout le reste (modèle,
taille, étapes, dossier des fichiers et désormais **charte graphique**) est fixé dans le workflow
ComfyUI, qui devient un document de l'organisation, versionné.

Vidéo : {{video}}

## But

- Dans ComfyUI, un nœud **Concaténer** (`StringConcatenate`) place la charte de l'organisation
  devant chaque description : premier champ (`string_a`) : la charte ; second champ (`string_b`)
  vide, rempli par Open WebUI ; délimiteur « . ». Sa sortie est reliée au texte de l'encodeur
  (nœud 27).
- Le préfixe d'enregistrement devient `openwebui/affiche` : les images de ce workflow ont leur
  propre dossier.
- Le graphe est testé dans ComfyUI, puis réexporté au format API sous un **nouveau nom**
  (`affiches-v2.json`) : la version 1 reste disponible pour revenir en arrière.
- Dans Open WebUI, la nouvelle version est téléversée et la ligne « Prompt* » de la correspondance
  passe de `text` / `27` à `string_b` / `34` (le **piège du lien écrasé** : voir
  `open-webui/correspondance-v2.md`).

Charte de la démonstration :

> Style imposé : illustration vectorielle plate, uniquement rose et bleu nuit, fond clair,
> personnages souriants, aucune marque, aucun texte

| Fichier | Contenu |
|---|---|
| `workflows/affiches-v1.json` | Version 1 au format API (celle du module 1 : la description va dans le texte du nœud 27) |
| `workflows/affiches-v1.interface.json` | Version 1 au format de l'interface de ComfyUI (place libre en bas de la première colonne pour la concaténation) |
| `workflows/affiches-v2.json` | Version 2 au format API, **telle qu'exportée dans la vidéo** : nœud 34 `StringConcatenate`, encodeur relié, préfixe `openwebui/affiche` |
| `workflows/affiches-v2.interface.json` | Version 2 au format de l'interface (graphe à la fin de la vidéo) |
| `workflows/affiches-v2.en.json`, `affiches-v2.de.json` | La même version 2, charte rédigée en anglais et en allemand (même structure, même correspondance) |
| `open-webui/correspondance-v2.md` | Les six lignes de la correspondance, le piège du lien écrasé, le retour arrière |
| `publier.py` | Publication par l'API d'Open WebUI : version 2, retour à la version 1, contrôle de la correspondance, essai |

## Prérequis

- Le serveur d'images du module 1 : ComfyUI v0.41 sur une carte graphique, modèle Z-Image Turbo
  (Apache 2.0), branché dans Open WebUI 0.11 (page Images) —
  [`clic-par-clic-comfyui-01-brancher`](https://github.com/guilhem-/clic-par-clic-comfyui-01-brancher).
- Le nœud `StringConcatenate` (inclus dans ComfyUI, aucun nœud personnalisé).
- Un compte **administrateur** d'Open WebUI.

## Installation pas à pas

### 1. Ajouter la charte, dans ComfyUI

1. Ouvrez `workflows/affiches-v1.interface.json` (glisser-déposer dans l'interface).
2. Double-cliquez sur une place libre du canevas, tapez `concat`, choisissez **Concaténer**, posez
   le nœud.
3. Premier champ : la charte ; délimiteur : `. ` (point, espace) ; second champ : vide.
4. Reliez la sortie **CHAÎNE** au texte de l'encodeur « CLIP Text Encode » (nœud 27) : son champ
   disparaît, sa valeur vient de la concaténation.
5. Nœud « Enregistrer Image » : préfixe `openwebui/affiche`.
6. **Testez** : une description dans le second champ, **Exécuter**. Puis videz ce champ.
7. Menu **Fichier › Exporter (API)**, nom `affiches-v2`.

Le numéro du nœud de concaténation (34 ici, le workflow s'arrêtant à 33) se lit sur son badge
(Paramètres, « badge » : mode de badge d'identifiant de nœud, « Afficher tout ») et dans le fichier
exporté.

### 2. Publier, dans Open WebUI, à la main comme dans la vidéo

Panneau d'administration › Réglages › Images : « Workflow ComfyUI » › **Téléverser**
`affiches-v2.json`, puis ligne « Prompt* » : clé `string_b`, ID des noeuds `34`. Enregistrer.
Détail : `open-webui/correspondance-v2.md`.

### 2 bis. Publier par l'API

```bash
cp .env.example .env          # OWUI_URL, OWUI_JETON (administrateur), COMFYUI_URL…
python publier.py --verifier  # contrôle des deux versions (et du piège, montré sur la version 2)
python publier.py             # sauvegarde la configuration en place (images-avant.json), publie la version 2
python publier.py --essai     # une image d'essai, générée par Open WebUI
python publier.py --revenir   # republie la version 1
python publier.py --retablir  # revient à la configuration sauvegardée
```

La page Images est un réglage **de toute l'instance** : `images-avant.json` garde la configuration
précédente, clés comprises (fichier ignoré par git, ne le partagez pas).

## Essai

Avec un compte utilisateur : nouvelle conversation, menu « Intégrations » › « Image », puis
« Une illustration sans texte : une équipe qui fait une pause café sur la terrasse du bureau. »
L'image suit la charte ; dépliez l'appel `generate_image` : la description rédigée par le modèle de
conversation ne contient pas la charte, c'est le workflow qui la place devant elle.

## Bon à savoir

- **Prompt négatif** : Open WebUI n'en transmet pas à ComfyUI (l'outil `generate_image` ne
  l'envoie jamais) et Z-Image Turbo, réglé sans guidage (CFG 1), l'ignorerait. Les interdits
  passent par la charte et par les consignes du modèle de conversation.
- **La charte en premier** : le modèle de conversation rédige souvent une description très stylée
  (« illustration éditoriale… semi-réaliste, palette harmonieuse… »). Ajoutée **après** elle, la
  charte a perdu à l'essai (image sans la palette) ; placée **devant**, formulée « Style imposé :
  … uniquement rose et bleu nuit… », elle l'emporte.
- **Formulation de la charte** : à CFG 1, un interdit n'est qu'une indication. À l'essai, « rose
  framboise » faisait apparaître une enseigne « FRAMBOISHE », et une scène de stand de salon des
  bannières au texte écorché ; « rose et bleu nuit » et des scènes sans support d'écriture donnent
  des images sans texte. Testez la charte sur plusieurs descriptions avant de la publier.
- Traitez le workflow comme un document : rangé dans un dépôt, avec ses versions, testé avant
  publication, correspondance relue à chaque version, ancienne version prête pour revenir en arrière.

## Série

- Module précédent : **Brancher ComfyUI dans Open WebUI** —
  [`clic-par-clic-comfyui-01-brancher`](https://github.com/guilhem-/clic-par-clic-comfyui-01-brancher).
- Module suivant : **Retoucher une image** (second workflow, modèle de retouche) —
  [`clic-par-clic-comfyui-03-retouche`](https://github.com/guilhem-/clic-par-clic-comfyui-03-retouche).

## Licence

MIT (voir `LICENSE`). ComfyUI : GPL-3.0 ; modèle Z-Image Turbo : Apache 2.0 ; Open WebUI : sa
propre licence (le code cité dans la vidéo reste le sien, il n'est pas recopié ici).
