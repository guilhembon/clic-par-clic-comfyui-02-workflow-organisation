"""Publier une version du workflow de l'organisation dans Open WebUI, par son API.

Fait ce que le module 2 de la série « Générer des images dans Open WebUI avec ComfyUI » fait à
l'écran, dans Panneau d'administration › Réglages › Images :
  1. téléverse le workflow au format API (workflows/affiches-v2.json : charte graphique ajoutée
     par un nœud de concaténation) ;
  2. met à jour la correspondance : la description va dans le second champ (string_b) de la
     concaténation, derrière la charte (string_a), et non plus dans le texte de l'encodeur (le
     piège du lien écrasé) ;
  3. garde l'adresse du serveur d'images, le modèle, la taille et les étapes du module 1.

Avant d'enregistrer, le script vérifie que chaque ligne de la correspondance vise une valeur du
workflow, et jamais un lien : Open WebUI écrirait la valeur par-dessus le lien, sans message.

Usage :
  python publier.py                 # sauvegarde la configuration en place (images-avant.json), publie la version 2
  python publier.py --revenir       # republie la version 1 (workflow d'origine, prompt dans le texte du nœud 27)
  python publier.py --verifier      # contrôle les deux versions et leur correspondance, sans rien changer
  python publier.py --essai         # génère une image d'essai par Open WebUI (adresse du fichier)
  python publier.py --retablir      # remet la configuration sauvegardée dans images-avant.json
  python publier.py --comfyui       # dépose la version 2 (format de l'interface) dans ComfyUI

La sauvegarde images-avant.json contient la configuration complète de la page Images, clés
comprises : elle est ignorée par git, ne la partagez pas.

Réglages : fichier .env (voir .env.example) ; les variables d'environnement l'emportent.
Aucune dépendance : Python 3.10 ou plus récent, bibliothèque standard seulement.
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

ICI = pathlib.Path(__file__).resolve().parent
SAUVEGARDE = ICI / "images-avant.json"
VARIABLES = ("OWUI_URL", "OWUI_JETON", "COMFYUI_URL", "COMFYUI_INTERFACE", "MODELE", "TAILLE", "ETAPES")

# Correspondance commune aux deux versions : modèle 28, image vide 13, échantillonneur 3.
COMMUNE = [
    ("model", "unet_name", "28"),
    ("width", "width", "13"),
    ("height", "height", "13"),
    ("steps", "steps", "3"),
    ("seed", "seed", "3"),
]
# Ce qui change d'une version à l'autre : où Open WebUI écrit la description.
VERSIONS = {
    1: {"fichier": "affiches-v1.json", "prompt": ("prompt", "text", "27")},
    2: {"fichier": "affiches-v2.json", "prompt": ("prompt", "string_b", "34")},
}


def reglages() -> dict:
    """Lit .env (clé=valeur), puis l'environnement, qui l'emporte."""
    r = {}
    env = ICI / ".env"
    if env.exists():
        for ligne in env.read_text(encoding="utf-8").splitlines():
            ligne = ligne.strip()
            if ligne and not ligne.startswith("#") and "=" in ligne:
                cle, valeur = ligne.split("=", 1)
                r[cle.strip()] = valeur.strip()
    for cle in VARIABLES:
        if os.environ.get(cle):
            r[cle] = os.environ[cle]
    return r


R = reglages()


def requete(methode: str, url: str, corps=None, entetes=None, brut: bytes | None = None):
    donnees = brut if brut is not None else (None if corps is None else json.dumps(corps).encode())
    req = urllib.request.Request(url, data=donnees, method=methode,
                                 headers={"Content-Type": "application/json", **(entetes or {})})
    try:
        with urllib.request.urlopen(req, timeout=300) as rep:
            texte = rep.read().decode()
    except urllib.error.HTTPError as e:
        sys.exit(f"{methode} {url} : {e.code} {e.read().decode()[:300]}")
    return json.loads(texte) if texte.strip().startswith(("{", "[")) else texte


def api(methode: str, chemin: str, corps=None):
    """Appel de l'API d'Open WebUI avec le jeton d'un administrateur."""
    if not R.get("OWUI_JETON"):
        sys.exit("OWUI_JETON manquant (.env) : jeton d'un compte administrateur d'Open WebUI.")
    return requete(methode, R["OWUI_URL"].rstrip("/") + chemin, corps,
                   {"Authorization": f"Bearer {R['OWUI_JETON']}"})


def correspondance(version: int) -> list[tuple[str, str, str]]:
    return [VERSIONS[version]["prompt"], *COMMUNE]


def verifier(workflow: dict, lignes: list[tuple[str, str, str]]) -> list[str]:
    """
    Problèmes de la correspondance : nœud absent, clé absente, ou clé qui porte un lien
    (["34", 0] : la sortie d'un autre nœud). Open WebUI remplace la valeur sans regarder ce
    qu'elle était : un lien écrasé débranche le nœud qu'il reliait, et ComfyUI ne dit rien.
    """
    problemes = []
    for type_, cle, noeud in lignes:
        if noeud not in workflow:
            problemes.append(f"{type_} : le nœud {noeud} n'existe pas dans le workflow")
            continue
        entrees = workflow[noeud].get("inputs", {})
        if cle not in entrees:
            problemes.append(f"{type_} : le nœud {noeud} ({workflow[noeud].get('class_type')}) n'a pas de clé {cle}")
        elif isinstance(entrees[cle], list):
            source = entrees[cle][0]
            problemes.append(f"{type_} : {noeud}.{cle} est un lien vers le nœud {source} "
                             f"({workflow.get(source, {}).get('class_type')}) : la description l'écraserait")
    return problemes


def lire_workflow(version: int) -> tuple[str, dict]:
    texte = (ICI / "workflows" / VERSIONS[version]["fichier"]).read_text(encoding="utf-8")
    return texte, json.loads(texte)


def publier(version: int) -> None:
    texte, workflow = lire_workflow(version)
    lignes = correspondance(version)
    problemes = verifier(workflow, lignes)
    if problemes:
        sys.exit("Correspondance refusée :\n  " + "\n  ".join(problemes))
    config = api("GET", "/api/v1/images/config")
    if not SAUVEGARDE.exists():
        SAUVEGARDE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Configuration en place sauvegardée dans {SAUVEGARDE.name} (python publier.py --retablir)")
    config.update({
        "ENABLE_IMAGE_GENERATION": True,
        "IMAGE_GENERATION_ENGINE": "comfyui",
        # Exactement l'origine qui sert les images, sans barre finale (contrôle anti-SSRF d'Open WebUI).
        "COMFYUI_BASE_URL": R.get("COMFYUI_URL", "").rstrip("/"),
        "COMFYUI_API_KEY": "",
        "COMFYUI_WORKFLOW": texte,
        "COMFYUI_WORKFLOW_NODES": [{"type": t, "key": k, "node_ids": [n]} for t, k, n in lignes],
        "IMAGE_GENERATION_MODEL": R.get("MODELE", "z_image_turbo_int8_convrot.safetensors"),
        "IMAGE_SIZE": R.get("TAILLE", "1024x1024"),
        "IMAGE_STEPS": int(R.get("ETAPES", "8")),
    })
    api("POST", "/api/v1/images/config/update", config)
    t, k, n = VERSIONS[version]["prompt"]
    print(f"Version {version} publiée ({VERSIONS[version]['fichier']}) : la description va dans {n}.{k}.")


def controler() -> None:
    for version in VERSIONS:
        _, workflow = lire_workflow(version)
        problemes = verifier(workflow, correspondance(version))
        print(f"Version {version} : " + ("correspondance juste" if not problemes else "; ".join(problemes)))
    # Le piège, montré : la correspondance de la version 1 appliquée à la version 2.
    _, v2 = lire_workflow(2)
    print("Version 2 avec la correspondance de la version 1 : " + "; ".join(verifier(v2, correspondance(1))))


def essai() -> None:
    images = api("POST", "/api/v1/images/generations",
                 {"prompt": "a team having a coffee break on the office terrace"})
    for image in images or []:
        print(f"Image : {R['OWUI_URL'].rstrip('/')}{image['url']}")


def retablir() -> None:
    if not SAUVEGARDE.exists():
        sys.exit(f"{SAUVEGARDE.name} introuvable : rien à rétablir.")
    api("POST", "/api/v1/images/config/update", json.loads(SAUVEGARDE.read_text(encoding="utf-8")))
    SAUVEGARDE.unlink()
    print("Configuration Images rétablie.")


def comfyui() -> None:
    """Dépose la version 2 (format de l'interface) parmi les workflows de l'utilisateur de ComfyUI."""
    base = R.get("COMFYUI_INTERFACE", "").rstrip("/")
    if not base:
        sys.exit("COMFYUI_INTERFACE manquant (.env) : adresse de l'interface de ComfyUI dans le navigateur.")
    nom = urllib.parse.quote("workflows/Serveur d'images — affiches v2.json", safe="")
    corps = (ICI / "workflows" / "affiches-v2.interface.json").read_bytes()
    # ComfyUI refuse une requête dont l'en-tête Origin ne correspond pas à son adresse.
    requete("POST", f"{base}/api/userdata/{nom}?overwrite=true", brut=corps, entetes={"Origin": base})
    print("Workflow « Serveur d'images — affiches v2 » déposé dans ComfyUI (panneau Flux de travail).")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # console Windows : accents lisibles
    if "--retablir" in sys.argv:
        retablir()
    elif "--verifier" in sys.argv:
        controler()
    elif "--essai" in sys.argv:
        essai()
    elif "--comfyui" in sys.argv:
        comfyui()
    elif "--revenir" in sys.argv:
        publier(1)
    else:
        publier(2)
