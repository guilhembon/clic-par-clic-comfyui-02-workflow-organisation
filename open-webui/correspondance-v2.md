# Correspondance des nœuds — version 2 (charte imposée)

Panneau d'administration › Réglages › Images › « Noeuds du workflow ComfyUI », après avoir
téléversé `workflows/affiches-v2.json` (« Workflow ComfyUI » › « Téléverser »).

| Ligne | Clé | ID des noeuds | Nœud visé | Changement par rapport à la version 1 |
|---|---|---|---|---|
| Prompt* | `string_b` | `34` | `StringConcatenate` (« Concaténer »), second champ (le premier porte la charte) | **oui** : avant, `text` du nœud `27` |
| Model | `unet_name` | `28` | `UNETLoader` (« Charger Modèle Diffusion ») | non |
| Width | `width` | `13` | `EmptySD3LatentImage` (image vide) | non |
| Height | `height` | `13` | idem | non |
| Steps | `steps` | `3` | `KSampler` (échantillonneur) | non |
| Seed | `seed` | `3` | idem | non |

Champs inchangés : moteur ComfyUI, « Base URL » `http://comfyui.comfyui.svc.cluster.local:8188`,
modèle `z_image_turbo_int8_convrot.safetensors`, taille `1024x1024`, 8 étapes. Enregistrer.

## Le piège du lien écrasé

Dans la version 2, le texte de l'encodeur (nœud `27`) n'est plus une phrase mais un lien :

```json
"27": { "inputs": { "text": ["34", 0], "clip": ["30", 0] }, "class_type": "CLIPTextEncode" }
```

Open WebUI (`open_webui/utils/images/comfyui.py`, fonction `_apply_workflow_nodes`, version
0.11.3) écrit la description dans `workflow[id]['inputs'][clé]` **sans regarder** ce qui s'y
trouve. Si la ligne « Prompt* » reste `text` / `27`, le lien `["34", 0]` est remplacé par la
description : la concaténation n'est plus reliée à rien, ComfyUI ne l'exécute pas, la charte
disparaît, et aucun message ne le signale (vérifié : demande acceptée, nœud 34 jamais exécuté).

`python publier.py --verifier` détecte ce cas : une ligne de correspondance qui vise un lien est
refusée.

## Revenir en arrière

Téléverser `workflows/affiches-v1.json` et remettre la ligne « Prompt* » à `text` / `27`
(ou `python publier.py --revenir`). Les autres lignes ne changent pas.
