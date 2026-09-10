# Passerelle vers le demon Docker de l'arena.
#
# CTFd doit piloter le Docker de l'arena pour creer les instances par equipe.
# Le faire depuis le conteneur CTFd lui-meme ne marche pas : l'image CTFd n'a
# pas de client ssh, tourne en uid 1001, et son HOME n'est pas /root - la cle
# montee n'y serait donc ni lisible ni trouvee.
#
# Ce conteneur ouvre un tunnel ssh vers l'arena et republie le socket Docker
# distant en TCP sur le reseau interne du compose. CTFd s'y connecte avec
# DOCKER_HOST=tcp://dockerproxy:2375, sans avoir besoin de ssh.
#
# Ce port n'est jamais publie vers l'exterieur : il n'existe que sur le reseau
# interne, dont l'acces vaut deja root sur l'arena.
FROM alpine:3.20

RUN apk add --no-cache openssh-client socat

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 2375 7400
ENTRYPOINT ["/entrypoint.sh"]
