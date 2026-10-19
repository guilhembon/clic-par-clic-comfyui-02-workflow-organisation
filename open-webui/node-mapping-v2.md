# Node mapping — version 2 (style guide enforced)

Admin Panel › Settings › Images › "ComfyUI Workflow Nodes", after uploading
`workflows/posters-v2.json` ("ComfyUI Workflow" › "Upload").

| Row | Key | Node Ids | Target node | Change from version 1 |
|---|---|---|---|---|
| Prompt* | `string_b` | `34` | `StringConcatenate` ("Concatenate Text"), second field (the first one holds the style guide) | **yes**: before, `text` of node `27` |
| Model | `unet_name` | `28` | `UNETLoader` ("Load Diffusion Model") | no |
| Width | `width` | `13` | `EmptySD3LatentImage` (empty image) | no |
| Height | `height` | `13` | same | no |
| Steps | `steps` | `3` | `KSampler` (sampler) | no |
| Seed | `seed` | `3` | same | no |

Unchanged fields: ComfyUI engine, "Base URL" `http://comfyui.comfyui.svc.cluster.local:8188`,
model `z_image_turbo_int8_convrot.safetensors`, size `1024x1024`, 8 steps. Save.

## The trap of the overwritten link

In version 2, the encoder's text (node `27`) is no longer a sentence but a link:

```json
"27": { "inputs": { "text": ["34", 0], "clip": ["30", 0] }, "class_type": "CLIPTextEncode" }
```

Open WebUI (`open_webui/utils/images/comfyui.py`, function `_apply_workflow_nodes`, version
0.11.3) writes the description into `workflow[id]['inputs'][key]` **without looking** at what is
there. If the "Prompt*" row stays `text` / `27`, the link `["34", 0]` is replaced by the
description: the concatenation is no longer connected to anything, ComfyUI does not run it, the
style guide disappears, and no message says so (checked: request accepted, node 34 never run).

`python publish.py --check` detects this case: a node mapping row that targets a link is refused.

## Rolling back

Upload `workflows/posters-v1.json` and set the "Prompt*" row back to `text` / `27`
(or `python publish.py --rollback`). The other rows do not change.
