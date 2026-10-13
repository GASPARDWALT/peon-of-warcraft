# Audit géographique — préparation v0.2.9

Audit **sans modification du jeu**, basé sur la ROM v0.2.8 candidate02
`acf059de6658c41c1c97714ec28826a69fcc11c89b0839007e5c8f7571706942`.
Les cartes PNG sont reconstruites depuis les graphiques compressés, palettes
RGB555, metatiles, collisions et événements réellement présents dans cette
ROM. Elles ne sont pas des captures d'émulateur. Chaque `.blk` et chaque
coordonnée de portail ont été comparés aux octets de la ROM.

Le rouge du dessin utilisateur signifie **montagne bloquante** : il ne demande
pas de colorer les falaises en rouge fluorescent dans le jeu. Le fichier du
dessin annoté de la conversation n'est pas stocké dans `references/` ; les
rectangles du comparatif proviennent des mesures approximatives conservées
dans `build_peon_valley_zones_v025.py::REFERENCE_RECTS`. Le comparatif expose
les positions relatives et les liens ; il ne prétend pas avoir numérisé le
contour rouge exact.

## Ce qui correspond déjà au plan

Les sept secteurs sont reliés dans le bon ordre et tous les indices de retour
sont réciproques. Les neuf liens ci-dessous sont vérifiés dans la ROM.

| Départ | Arrivée | Direction | Sortie native | Arrivée native |
|---|---|---|---|---|
| 1 — The Den | 2 — Valley of Trials | Droite | `(20,10)` | `(4,12)` |
| 2 | 3 — Crossroads | Haut | `(16,0)` | `(5,9)` |
| 3 | 4 — Hanazua Camp | Gauche | `(0,4)` | `(9,4)` |
| 4 | 5 — Sarkoth Basin | Bas | `(5,9)` | `(5,0)` |
| 5 | 1 | Droite | `(9,7)` | `(0,14)` |
| 3 | 6 — Cave Approach | Haut | `(5,0)` | `(5,9)` |
| 2 | 7 — Valley Exit | Droite | `(28,12)` | `(0,4)` |
| 7 | Durotar Road | Droite | `(9,4)` | `(4,14)` |
| 6 | Burning Blade Cavern | Entrée de grotte au nord | `(5,2)` | `(10,16)` |

Hanazua se trouve dans le secteur 4 et donne la quête de Sarkoth, placé dans
le secteur 5. Les deux familiers devant la grotte du secteur 6 sont des
rencontres natives de niveau 3. L'ancienne entrée de grotte dans la grande
carte Valley of Trials a été retirée ; la vraie entrée se trouve au nord du
secteur 6. Les routes peintes de chacune des neuf cartes sont connexes.

La sortie de Durotar Road vers Sen'jin est `(12,24)` ; le retour de Sen'jin
est `(10,4)`. Le chemin pointe bien vers le sud, tandis que Razor Hill est au
nord de Durotar Road.

## Écarts visibles à corriger

1. **Les secteurs 1 et 2 restent de grandes cartes.** The Den mesure
   384×320 pixels, Valley of Trials 512×384. Les secteurs 3–7 mesurent chacun
   160×160. Ils ne correspondent donc pas encore tous à « un carré = ce qui
   tient sur l'écran », qui affiche 160×144 pixels avant les éléments du HUD.
   Les portails 1→2 et 2→7 sont aussi à l'intérieur des grandes cartes,
   contrairement aux portails des cinq petits secteurs situés sur leurs bords.
2. **Les contours sont encore simplifiés en rectangles.** Les routes et
   blocages sont fonctionnels, mais les cinq petits secteurs n'épousent pas
   encore les falaises irrégulières, replis et ouvertures étroites du plan WoW.
   Le comparatif est utile pour constater cet écart ; il ne doit pas être
   présenté comme une reproduction fidèle du contour rouge.
3. **La sortie 7 ressemble à une enceinte complète.** Les fortifications
   claires entourent presque tout le rectangle. Le dessin utilisateur montre
   surtout les deux murs de la sortie à l'est. On peut replacer les autres
   fortifications par des falaises sans toucher aucune collision.
4. **La route vers Sen'jin n'oblige actuellement à aucun combat.** Un trajet
   libre de 18 pas, ou le chemin peint de 24 pas, évite toutes les zones
   d'aggro. Le pack de deux scorpides niveau 4 se trouve sur une branche
   latérale, actif seulement à partir du niveau 4. Voir le sous-audit détaillé
   `senjin_route_audit.md` et les chemins exacts dans son JSON.

## Corrections proposées, dans l'ordre

### A. Sortie 7 : amélioration visuelle sans changement de collision

Dans `maps/PeonValleyExit.blk`, garder les blocs de fortification 33 aux quatre
positions `(4,0)`, `(4,1)`, `(4,3)`, `(4,4)` : ils forment les murs de part et
d'autre de l'ouverture orientale. Remplacer les dix autres blocs 33 de la
bordure par le bloc de montagne 1. Les deux blocs ont quatre collisions WALL,
donc anciennes positions sauvegardées, PNJ, portails `(0,4)/(9,4)` et chemin
restent inchangés. Aucun motif supplémentaire n'est nécessaire.

Cette proposition est détaillée dans `zone7_gate_collision_stable_proposal.json`
et dessinée en jaune dans son overlay. **Elle n'est pas appliquée.**

### B. Chemins et montagnes : préserver les cellules avant de déplacer les murs

Conserver les neuf points de portail et leur approche. Dessiner des faces de
falaise qui changent d'orientation aux angles, ainsi que des replis au lieu de
la même face répétée partout. Toute variation de metatile doit conserver ses
quatre collisions. Une falaise solide ne doit pas dessiner du sol libre dans
une cellule où le joueur ne peut pas marcher.

Le moteur actuel charge un atlas partagé de 192 motifs pour toute la nature,
les bâtiments et les pièces. Cette limite est celle de cette allocation de
Crystal, pas la limite absolue de la Chromatic. Des atlas par région seraient
une prochaine étape raisonnable : les mêmes IDs de collision resteraient
stables, tandis que les motifs chargés donneraient plus de détail propre à
chaque secteur. Cela nécessite des tests des retours de combat, menus et
chargements avant d'être intégré.

### C. Route Sen'jin : deux ou trois ennemis réellement successifs

Une première amélioration peut déplacer l'approche du pack vers le chemin
peint sud et garder les drapeaux existants FIRST/DEAD. Les déclencheurs
`(12,22)/(13,22)` interceptent ce chemin, mais un détour ouest reste possible
avec une seule harpie : ne pas annoncer un minimum de deux combats partout.

Pour une vraie triple séquence, réserver explicitement les bits de progression
supplémentaires avant implémentation, figer la taille du pack avant le premier
combat, conserver chaque victoire après fuite/défaite et donner priorité aux
anciens drapeaux DEAD. Aucun soin automatique ne doit arriver entre les trois
combats. Vérifier ensuite potion, mana/rage, deuxième/troisième défaite, vraie
sauvegarde et Continue, disparition définitive et retour à Sen'jin.

La proposition de placement visible `(14,21)` doit aussi être vérifiée contre
les anciennes cellules de sauvegarde et les déplacements du garde. Le rapport
Sen'jin propose une alternative sans nouveau bit : la paire existante suivie
de la harpie existante, avec son propre drapeau de mort conservé.

### D. Un secteur par écran : décision de compatibilité à traiter séparément

Réduire silencieusement The Den ou Valley of Trials casserait les coordonnées
des sauvegardes, des PNJ, des quêtes, des portes et de l'atlas. Garder la
géographie actuelle pour le checkpoint v0.2.8. Pour obtenir sept vrais écrans,
préparer soit un découpage vers de nouvelles cartes avec migration explicite
des anciennes positions, soit une caméra par écrans conservant les cartes et
coordonnées natives. Ces deux options demandent une revue des transitions ;
elles ne doivent pas être confondues avec le simple remplacement de sprites.

## Fichiers de revue

- `seven_zones_target_vs_native_contact_sheet.png` : comparaison des positions
  approximatives du plan et des sept secteurs complets de la ROM ; les deux
  cartes de route et village sont fournies séparément.
- `*_rom_decoded.png` : fonds natifs reconstruits depuis la ROM.
- `*_collision_warp_overlay_2x.png` : rouge montagnes, ivoire fortifications,
  vert route peinte, cyan vrais portails, rose cellules de déclenchement.
- `native_geography_audit.json` : dimensions, vrais octets et indices de retour.
- `senjin_route_audit.md/.json` : chemins, rencontres et reprise des séquences.
- `zone7_gate_collision_stable_proposal.json` : dix remplacements proposés,
  sans changement de collision et sans application au jeu.

Le contrôle complet v0.2.8 candidate02 a également réussi : neuf portes,
quatre sauvegardes froides dans les pièces, 22 retours de menus, neuf liens
avec leurs retours, grotte et cactus. Les quatre pièces ont montré 256 frames
de vasques natives, trois phases de feu et 190 autres motifs inchangés.
