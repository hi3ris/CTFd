# ModelHub -- model registry validation API (handout)

ModelHub validates an uploaded model by deserializing it and returning a short
summary of the loaded object. Models are plain Python **pickles** (the format
`joblib.dump`, `sklearn`, and `torch.save` all use).

## Endpoint

```
POST /validate
```

Send the pickle as the raw request body, or as multipart form field `model`.

```sh
# raw body
curl -s --data-binary @model.pkl http://HOST:PORT/validate

# multipart
curl -s -F model=@model.pkl http://HOST:PORT/validate
```

### Responses (JSON)

Success -- the object loaded, here is its repr:

```json
{"status":"ok","loaded_type":"dict",
 "model_summary":"{'name': 'demo-linear', 'weights': [0.1, -0.4, 2.0]}",
 "truncated":false}
```

Rejected -- the restricted loader refused a class, and tells you why:

```json
{"status":"rejected",
 "reason":"class not allowed: os.system (module 'os' is blocked)"}
```

Error -- the pickle failed to load for some other reason:

```json
{"status":"error","reason":"UnpicklingError: ..."}
```

## The included example

`example_model.pkl` is a harmless model: a `dict` describing a toy linear model.
Load it locally to see the structure, and POST it to `/validate` to see the
`status:"ok"` round-trip. It uses no custom classes and no `__reduce__`.

```python
import pickle
print(pickle.load(open("example_model.pkl", "rb")))
# {'name': 'demo-linear', 'framework': 'modelhub', 'version': 1,
#  'weights': [0.1, -0.4, 2.0, 0.7], 'bias': 0.05}
```

## Notes from the service `GET /`

- Any pickle protocol is accepted.
- The loader runs in a restricted sandbox that refuses to import dangerous
  modules (`os`, `subprocess`, `sys`, `builtins`, `importlib`, and friends).
  Rejected classes are reported so you can see which import tripped the guard.
- The host holds one file with this team's flag. It is **not** part of any
  response, and the registry will not read it for you.
- There is a stale `/flag.decoy` placeholder. It is not a flag.

Flag format: `CTF{...}`
