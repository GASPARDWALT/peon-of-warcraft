# Petit Cailloux : attaques de terre et de roche

Le compagnon capturé dans la quête du shaman reste un vrai membre du ROSTER.
Il utilise les tours, quatre emplacements d'attaques, PP, renommage et évolutions
du moteur natif. Il ne porte aucune masse et n'utilise plus les leçons de classe
Lightning Bolt / Earth Shock.

| Attaque de départ | ID natif | Type | Puissance | PP |
| --- | --- | --- | --- | --- |
| STRIKE | TACKLE, 33 | Normal | 35 | 35 |
| MUD-SLAP | 189 | Sol | 20 | 10 |
| ROCK THROW | 88 | Roche | 50 | 15 |

Les trois attaques sont disponibles dès le niveau 1, donc aussi sur le caillou
capturé au niveau 3. STRIKE réutilise le contact natif de TACKLE, sans arme. Ce
nom générique s'applique également aux autres créatures qui possèdent TACKLE ;
le nom et l'attaque MACE STRIKE / POUND du héros ne changent pas. MACE STRIKE et
STRIKE coûtent zéro mana/rage ; le compagnon dépense ses PP natifs.

Progression : HARDEN au niveau 4, MAGNITUDE au niveau 6, évolution en Veine
Tellurique au niveau 8, DIG au niveau 10, évolution en Roche Elementaire et
ROCK SLIDE au niveau 12, EARTHQUAKE au niveau 15. Les niveaux d'évolution
existants et les choix natifs de remplacement parmi quatre attaques restent
inchangés.

Les effets utilisent les dessins détaillés ROCKS et SAND de pokecrystal : un
rocher suit un arc de l'attaquant vers sa cible, puis un impact et deux nuages
de terre marquent son arrivée. Mud-Slap lance plusieurs petites projections
ocres ; Magnitude, Rock Slide et Earthquake associent les secousses à de vrais
débris de roche et de poussière. Trois objets sont ajoutés à la fin de la table
native, sans décaler les anciens IDs. Le moteur inverse les coordonnées pour
un attaquant ennemi. Les données et l'animation approuvée de Lightning Bolt
restent intactes.

À la reprise d'une sauvegarde, une correction reconnaît uniquement les espèces
ONIX / GRAVELER / GOLEM qui portent encore exactement l'ancienne paire de
départ POUND, THUNDERSHOCK dans leurs deux premiers emplacements. Elle remplace
ces deux IDs par STRIKE et MUD-SLAP. Les PP de STRIKE restent identiques ; ceux
de Mud-Slap sont plafonnés à sa capacité, en conservant les PP Ups. Aucun PP
existant n'est restauré. ROCK THROW est ajouté uniquement s'il manque et qu'un
des deux derniers emplacements est libre. Les attaques apprises ou modifiées,
les autres membres, noms, niveaux, statistiques, événements, argent et objets
restent inchangés. La nouvelle paire ne correspond plus à la garde, donc la
correction est idempotente. Aucun octet ni version de format de sauvegarde
n'est ajouté.

Le validateur `tools/validate_peon_rock_earth_moves_v0216.py` joue une vraie
capture et des attaques, observe le framebuffer, les PP et les limites OAM,
puis prépare une vraie sauvegarde privée v0.2.15 et vérifie sa reprise dans la
nouvelle ROM. Il n'écrit pas dans la RAM de l'émulateur, ne restaure pas d'état
et n'ouvre aucune sauvegarde personnelle. La progression ultérieure est
contrôlée dans les tables de la ROM liée ; ces contrôles ne prétendent pas
montrer une progression ordinaire jusqu'au niveau 15. Le matériel Chromatic
physique n'est pas testé.

Validation de la ROM `3c25adf84a9278c826f3f873560991ee6483d6bc02641782afb1e9f9810aa2dc`
: PASS dans `references/generated/rock_earth_moves_v0216/runtime_3c25adf8/validation.json`.
Le vrai caillou TERRA capturé au niveau 3 lance STRIKE, MUD-SLAP puis ROCK THROW.
Ses PP passent de `[35, 10, 15]` à `[34, 9, 14]`, un seul PP débité par tour,
sans coût de mana du héros. Le maximum observé est de 23 objets OAM au total
et 8 sur une même ligne. STRIKE et ROCK THROW sont aussi observés côté ennemi ;
l'inversion de Mud-Slap ennemi est vérifiée dans les objets natifs, mais ce
choix n'a pas été tiré par le RNG de cette route. Les captures montrent la vraie
image LCD 160×144, et les versions 4× utilisent uniquement le plus proche voisin.

Une vraie partie privée v0.2.15 capture et renomme TERRA avant le SAVE natif.
Sa reprise à froid dans la nouvelle ROM donne `[33, 189, 88, 0]` et conserve
exactement tous les autres champs contrôlés : membres et statistiques, noms,
niveaux, PP non concernés, événements, objets et argent. Un second changement
de carte ne modifie plus les attaques ni les PP. Le premier combat de quête
est gagné normalement ; la capture demande cinq essais sur cette route,
avec une défaite et une reprise normale à l'auberge. Aucun ajustement de
statistiques, objet injecté ou nerf de difficulté n'a été nécessaire.
