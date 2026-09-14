# ssti-jinja -- solution

**Summary:** The `name` is concatenated into the Jinja template source before
rendering, so a `{{ vault.reveal() }}` payload executes and returns the flag.

## Vulnerability

`render_card` builds `env.from_string("Dear " + name + ", welcome to Lome!")`.
User input becomes part of the template source, i.e. server-side template
injection. The render environment exposes a `vault` global whose `reveal()`
method unseals the flag (XOR of a sealed blob with
`sha256("greeting-vault-2026")`). The flag is not present in the clear -- it is
produced only when the template evaluates the payload.

## Steps

1. Recognise the name is placed in the template source, not passed as data.
2. Send `name = "{{ vault.reveal() }}"`.
3. The rendered card becomes `Dear <flag>, welcome to Lome!`; strip the
   surrounding text.

Run:

```
python3 solution/solve.py
```

## Flag

```
NCTF{jinja2_ssti_config_leak_via_render_string}
```
