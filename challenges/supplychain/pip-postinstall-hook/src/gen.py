#!/usr/bin/env python3
"""Generate the pip-postinstall-hook artifact bundle.

A Python source distribution (`sdist`) ships a `setup.py` with a custom
install command. The malicious body is stored obfuscated: it is XOR'd with a
single-byte key and hex-encoded. Deobfuscating reveals code that writes the
flag to disk.
"""

import io
import os
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

FLAG = "NCTF{p1p_postinstall_deobfuscated_5b90}"
KEY = 0x5B


def obfuscate(text):
    return bytes(b ^ KEY for b in text.encode()).hex()


def build():
    hidden_code = (
        "import os\n"
        "open(os.path.expanduser('~/.acme_licence'),'w')"
        f".write('{FLAG}')\n"
    )
    blob = obfuscate(hidden_code)

    setup_py = (
        "from setuptools import setup\n"
        "from setuptools.command.install import install\n"
        "\n"
        f"_K = {KEY}\n"
        f'_B = "{blob}"\n'
        "\n"
        "\n"
        "def _run():\n"
        "    data = bytes.fromhex(_B)\n"
        "    src = bytes(c ^ _K for c in data).decode()\n"
        "    exec(compile(src, '<hook>', 'exec'), {})\n"
        "\n"
        "\n"
        "class PostInstall(install):\n"
        "    def run(self):\n"
        "        _run()\n"
        "        install.run(self)\n"
        "\n"
        "\n"
        "setup(\n"
        "    name='acme-license-check',\n"
        "    version='1.0.0',\n"
        "    py_modules=['acme_license_check'],\n"
        "    cmdclass={'install': PostInstall},\n"
        ")\n"
    )

    pkg_info = (
        "Metadata-Version: 2.1\n"
        "Name: acme-license-check\n"
        "Version: 1.0.0\n"
        "Summary: License validation helper for ACME tooling.\n"
    )
    module = "def check():\n    return True\n"

    files = {
        "acme-license-check-1.0.0/setup.py": setup_py.encode(),
        "acme-license-check-1.0.0/PKG-INFO": pkg_info.encode(),
        "acme-license-check-1.0.0/acme_license_check.py": module.encode(),
    }

    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))

    import gzip

    with open(os.path.join(OUT, "acme-license-check-1.0.0.tar.gz"), "wb") as fh:
        fh.write(gzip.compress(raw.getvalue(), mtime=0))

    print("built pip-postinstall-hook artifacts")


if __name__ == "__main__":
    build()
