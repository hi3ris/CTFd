# strings-goldmine — writeup

**Category:** mobile · **Difficulty:** beginner
**Flag:** `NCTF{h4rdc0d3d_k3y_in_str1ngs_xml}`

## Summary

An Android APK ships an encrypted "premium unlock token" as a base64 resource,
and the XOR key used to decrypt it is a hardcoded `API_SECRET` in `BuildConfig`.
Reading both out of the bundle recovers the flag.

## The technique

An APK is just a ZIP. Unzip it:

- `res/values/strings.xml` → `<string name="enc_blob">…base64…</string>`
- `sources/com/vault/app/BuildConfig.java` → `API_SECRET = "sk_live_tg_…"`

`MainActivity` decodes the blob and XORs it with `API_SECRET` (key repeats):

```
token = base64_decode(enc_blob) XOR API_SECRET
```

The plaintext flag is never stored (`grep h4rdc0d3d app-release.apk` → nothing).

## Solve

```
$ python3 solve.py app-release.apk
API_SECRET: sk_live_tg_0f4c9a1b7d2e5
flag: NCTF{h4rdc0d3d_k3y_in_str1ngs_xml}
```

## Rebuilding

```
python3 src/gen.py    # writes app-release.apk with the flag embedded via XOR
```
