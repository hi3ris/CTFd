# En-tetes de proxy communs aux deux configurations.
#
# CTFd tourne avec REVERSE_PROXY=true : il fait confiance aux en-tetes
# X-Forwarded-*. Il faut donc les positionner TOUS explicitement, y compris
# ceux qu'on ne veut pas. Un en-tete non defini ici est transmis tel que le
# client l'a envoye : un joueur qui poste
#   X-Forwarded-Host: attaquant.example
# sur /reset_password ferait fabriquer par CTFd un lien de reinitialisation
# pointant chez lui, et l'enverrait a l'administrateur. C'est une prise de
# controle du compte admin en une requete.
proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host  $host;
proxy_set_header X-Forwarded-Port  $server_port;
proxy_set_header X-Forwarded-Prefix "";

# Les challenges IA repondent en streaming : pas de bufferisation, et un
# timeout large pour laisser le modele generer.
proxy_buffering    off;
proxy_read_timeout 300s;
