"""Publish a version of the organization's workflow in Open WebUI, through its API.

Does what module 2 of the "Image generation in Open WebUI with ComfyUI" series does on screen,
in Admin Panel > Settings > Images:
  1. uploads the workflow in API format (workflows/posters-v2.json: style guide added by a
     concatenation node);
  2. updates the node mapping: the description goes into the second field (string_b) of the
     concatenation, behind the style guide (string_a), and no longer into the encoder's text
     (the trap of the overwritten link);
  3. keeps the image server address, the model, the size and the steps of module 1.

Before saving, the script checks that each row of the node mapping targets a value of the
workflow, and never a link: Open WebUI would write the value over the link, without a message.

Usage:
  python publish.py                 # back up the current configuration (images-config.backup.json), publish version 2
  python publish.py --rollback      # publish version 1 again (original workflow, prompt into the text of node 27)
  python publish.py --check         # check both versions and their node mapping, without changing anything
  python publish.py --test          # generate a test image through Open WebUI (address of the file)
  python publish.py --restore       # put back the configuration saved in images-config.backup.json
  python publish.py --comfyui       # drop version 2 (interface format) into ComfyUI

The backup images-config.backup.json holds the whole configuration of the Images page, keys
included: it is ignored by git, do not share it.

Settings: .env file (see .env.example); environment variables take precedence.
No dependency: Python 3.10 or newer, standard library only.
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
BACKUP = HERE / "images-config.backup.json"
VARIABLES = ("OWUI_URL", "OWUI_TOKEN", "COMFYUI_URL", "COMFYUI_INTERFACE", "MODEL", "SIZE", "STEPS")


def settings() -> dict:
    """Read .env (key=value), then the environment, which wins."""
    s = {}
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                s[key.strip()] = value.strip()
    for key in VARIABLES:
        if os.environ.get(key):
            s[key] = os.environ[key]
    return s


S = settings()

# Node mapping shared by both versions: model 28, empty image 13, sampler 3.
SHARED = [
    ("model", "unet_name", "28"),
    ("width", "width", "13"),
    ("height", "height", "13"),
    ("steps", "steps", "3"),
    ("seed", "seed", "3"),
]
# What changes from one version to the other: where Open WebUI writes the description.
VERSIONS = {
    1: {"file": "posters-v1.json", "prompt": ("prompt", "text", "27")},
    2: {"file": "posters-v2.json", "prompt": ("prompt", "string_b", "34")},
}


def request(method: str, url: str, body=None, headers=None, raw: bytes | None = None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            text = resp.read().decode()
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url}: {e.code} {e.read().decode()[:300]}")
    return json.loads(text) if text.strip().startswith(("{", "[")) else text


def api(method: str, path: str, body=None):
    """Call Open WebUI's API with an administrator token."""
    if not S.get("OWUI_TOKEN"):
        sys.exit("OWUI_TOKEN missing (.env): token of an Open WebUI administrator account.")
    return request(method, S["OWUI_URL"].rstrip("/") + path, body,
                   {"Authorization": f"Bearer {S['OWUI_TOKEN']}"})


def node_mapping(version: int) -> list[tuple[str, str, str]]:
    return [VERSIONS[version]["prompt"], *SHARED]


def check(workflow: dict, rows: list[tuple[str, str, str]]) -> list[str]:
    """
    Problems of the node mapping: missing node, missing key, or a key that holds a link
    (["34", 0]: the output of another node). Open WebUI replaces the value without looking at
    what it was: an overwritten link disconnects the node it linked, and ComfyUI says nothing.
    """
    problems = []
    for type_, key, node in rows:
        if node not in workflow:
            problems.append(f"{type_}: node {node} does not exist in the workflow")
            continue
        inputs = workflow[node].get("inputs", {})
        if key not in inputs:
            problems.append(f"{type_}: node {node} ({workflow[node].get('class_type')}) has no key {key}")
        elif isinstance(inputs[key], list):
            source = inputs[key][0]
            problems.append(f"{type_}: {node}.{key} is a link to node {source} "
                            f"({workflow.get(source, {}).get('class_type')}): the description would overwrite it")
    return problems


def read_workflow(version: int) -> tuple[str, dict]:
    text = (HERE / "workflows" / VERSIONS[version]["file"]).read_text(encoding="utf-8")
    return text, json.loads(text)


def publish(version: int) -> None:
    text, workflow = read_workflow(version)
    rows = node_mapping(version)
    problems = check(workflow, rows)
    if problems:
        sys.exit("Node mapping refused:\n  " + "\n  ".join(problems))
    config = api("GET", "/api/v1/images/config")
    if not BACKUP.exists():
        BACKUP.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Current configuration saved to {BACKUP.name} (python publish.py --restore)")
    config.update({
        "ENABLE_IMAGE_GENERATION": True,
        "IMAGE_GENERATION_ENGINE": "comfyui",
        # Exactly the origin that serves the images, without a trailing slash (Open WebUI's anti-SSRF check).
        "COMFYUI_BASE_URL": S.get("COMFYUI_URL", "").rstrip("/"),
        "COMFYUI_API_KEY": "",
        "COMFYUI_WORKFLOW": text,
        "COMFYUI_WORKFLOW_NODES": [{"type": t, "key": k, "node_ids": [n]} for t, k, n in rows],
        "IMAGE_GENERATION_MODEL": S.get("MODEL", "z_image_turbo_int8_convrot.safetensors"),
        "IMAGE_SIZE": S.get("SIZE", "1024x1024"),
        "IMAGE_STEPS": int(S.get("STEPS", "8")),
    })
    api("POST", "/api/v1/images/config/update", config)
    t, k, n = VERSIONS[version]["prompt"]
    print(f"Version {version} published ({VERSIONS[version]['file']}): the description goes into {n}.{k}.")


def check_versions() -> None:
    for version in VERSIONS:
        _, workflow = read_workflow(version)
        problems = check(workflow, node_mapping(version))
        print(f"Version {version}: " + ("node mapping correct" if not problems else "; ".join(problems)))
    # The trap, shown: the node mapping of version 1 applied to version 2.
    _, v2 = read_workflow(2)
    print("Version 2 with the node mapping of version 1: " + "; ".join(check(v2, node_mapping(1))))


def test() -> None:
    images = api("POST", "/api/v1/images/generations",
                 {"prompt": "a team having a coffee break on the office terrace"})
    for image in images or []:
        print(f"Image: {S['OWUI_URL'].rstrip('/')}{image['url']}")


def restore() -> None:
    if not BACKUP.exists():
        sys.exit(f"{BACKUP.name} not found: nothing to restore.")
    api("POST", "/api/v1/images/config/update", json.loads(BACKUP.read_text(encoding="utf-8")))
    BACKUP.unlink()
    print("Images configuration restored.")


def comfyui() -> None:
    """Drop version 2 (interface format) among the workflows of ComfyUI's user."""
    base = S.get("COMFYUI_INTERFACE", "").rstrip("/")
    if not base:
        sys.exit("COMFYUI_INTERFACE missing (.env): address of ComfyUI's interface in the browser.")
    name = urllib.parse.quote("workflows/Image server — posters v2.json", safe="")
    body = (HERE / "workflows" / "posters-v2.interface.json").read_bytes()
    # ComfyUI refuses a request whose Origin header does not match its address.
    request("POST", f"{base}/api/userdata/{name}?overwrite=true", raw=body, headers={"Origin": base})
    print('Workflow "Image server — posters v2" dropped into ComfyUI (Workflows panel).')


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows console: dashes and quotes readable
    if "--restore" in sys.argv:
        restore()
    elif "--check" in sys.argv:
        check_versions()
    elif "--test" in sys.argv:
        test()
    elif "--comfyui" in sys.argv:
        comfyui()
    elif "--rollback" in sys.argv:
        publish(1)
    else:
        publish(2)
