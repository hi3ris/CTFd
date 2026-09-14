#!/bin/sh
# ---------------------------------------------------------------------------
# ACME vault. usage:  sh lock.sh <password>
# (this file was minified/obfuscated by the build; nothing here is plaintext)
# ---------------------------------------------------------------------------
_k=5942194646755d1b504b584e
_b=PStnKhcsHwIWDS0XFgRVMwhsFEMDEQY7Aw0AAAk7Cg==
_p=$(printf '%s' "$_k" | perl -ne 'chomp;print chr(hex($1)^0x2a)while/(..)/g')
[ "$1" = "$_p" ] || { echo "access denied"; exit 1; }
printf '%s' "$_b" | base64 -d | perl -e '$k=shift;local $/;$d=<STDIN>;print join("",map{chr(ord(substr($d,$_,1))^ord(substr($k,$_%length($k),1)))}0..length($d)-1),"\n"' "$_p"
