# Géographie : audit et préparation v0.2.9

Les fichiers de ce dossier séparent l'état de la ROM et la proposition. Les
images `*_rom_decoded.png` sont reconstruites à partir des tiles, palettes,
metatiles et cartes effectivement extraites de la ROM. Ce sont des vues
statiques de données natives, pas des captures de jeu. Les images de
`proposed/` montrent des changements **non appliqués et non compilés**.

## Ce qui correspond déjà au plan

Les neuf liaisons voulues ont les bonnes destinations et retours :

| Liaison | Sortie actuelle | Arrivée actuelle |
| --- | --- | --- |
| 1 → 2, droite | TheDen `(20,10)` | ValleyOfTrials `(4,12)` |
| 2 → 3, haut | ValleyOfTrials `(16,0)` | Crossroads `(5,9)` |
| 3 → 4, gauche | Crossroads `(0,4)` | HanazuaCamp `(9,4)` |
| 4 → 5, bas | HanazuaCamp `(5,9)` | SarkothBasin `(5,0)` |
| 5 → 1, droite | SarkothBasin `(9,7)` | TheDen `(0,14)` |
| 3 → 6, haut | Crossroads `(5,0)` | CaveApproach `(5,9)` |
| 2 → 7, droite | ValleyOfTrials `(28,12)` | ValleyExit `(0,4)` |
| 7 → route, droite | ValleyExit `(9,4)` | DurotarRoad `(4,14)` |
| 6 → grotte, haut | CaveApproach `(5,2)` | Cavern `(10,16)` |

Le chemin vers Sen'jin descend ensuite de DurotarRoad `(12,24)` vers
SenjinVillage `(10,4)`. Hanazua reste en zone 4, Sarkoth en zone 5, et les deux
diablotins de niveau 3 protègent l'accès à la grotte de la zone 6.

## Écarts visibles

- Les zones 1 et 2 sont encore de grandes cartes héritées : 384×320 et
  512×384 pixels. Les zones 3 à 7 font 160×160. Les carrés du plan de référence
  représentent la vue souhaitée, alors que ces deux premières cartes font
  défiler la caméra. Même 160×160 dépasse la hauteur réelle de l'écran,
  144 pixels. Les caméras fixes et le redécoupage des événements restent hors
  de cette préparation.
- Les limites des petites cartes sont essentiellement rectangulaires.
  L'annotation rouge décrit des montagnes bloquantes irrégulières ; elle ne
  demande pas des falaises rouge fluo en jeu.
- La zone 7 place actuellement des murs fortifiés ivoire sur presque tout
  son pourtour. La proposition garde les fortifications sur le côté est,
  près de la véritable sortie, et remet des montagnes sur les autres côtés.
- Il reste aujourd'hui un parcours vers Sen'jin sans combat : 18 pas en
  terrain libre, ou 24 pas sur le chemin peint. Le pack de deux scorpides est
  à côté du trajet principal. Le sous-audit détaille ce problème et les
  options de combat successif sans guérison automatique.

La carte annotée rouge/vert de la conversation n'existe pas sous forme de
fichier dans `references/`. Les positions des sept rectangles proviennent des
mesures déjà documentées dans `build_peon_valley_zones_v025.py`. Les données du
jeu et les chemins ont été vérifiés ; une superposition précise de chaque
pixel de l'annotation d'origine ne serait pas justifiée avec ces seules
mesures.

## Préparation concrète

`tools/build_peon_geography_v029.py` reste en prévisualisation par défaut.
Il prépare des reliefs véritablement solides dans des marges inutilisées,
avec une précision de 16×16 pixels. Quatorze metatiles partiels appendent les
IDs 53–66. Ils combinent les quadrants déjà existants de falaise 1 et de sol
38 : **aucun nouveau motif graphique, aucune palette et aucun champ SRAM**.
Les 53 significations précédentes sont conservées et l'allocation reste à
192 motifs 8×8.

Cette proposition transforme 68 anciennes cases de sol en `WALL` :

| Carte | Cases devenant réellement bloquantes |
| --- | ---: |
| TheDen | 15 |
| ValleyOfTrials | 44 |
| Crossroads | 1 |
| HanazuaCamp | 1 |
| SarkothBasin | 3 |
| CaveApproach | 1 |
| ValleyExit | 3 |

Chaque nouvelle case de mur reste reliée au relief extérieur, et les chemins
peints restent inchangés. Les entrées, événements de cactus, approches de PNJ,
trajectoires d'agression et positions prévues des nouvelles recrues sont
protégés. Une recherche de chemin vérifie les portails et les interactions,
y compris en considérant les corps de tous les PNJ et futurs ennemis comme
des obstacles.

**La reprise des anciennes sauvegardes doit être intégrée avant publication.**
Si une ancienne sauvegarde se trouve sur l'une des 68 nouvelles cases de mur,
un garde de reprise doit déplacer le personnage vers un sol réellement
accessible. `changed_collision_cells.json` liste toutes les cases avec
`safeLandingSuggested`, hors PNJ, portail et déclencheur de combat. Les quatre
intérieurs conservent leur ancienne passabilité.

Le patch binaire `/tmp/peon_v029_geography_hooks.patch` a été testé dans une
copie temporaire avec `git apply --check` et comparaison des octets produits.
Il n'a pas été appliqué au dépôt de travail. La préparation peut être
intégrée après le checkpoint v0.2.8 en lançant le générateur avec `--apply`.
Les essais natifs devront ensuite couvrir le jeu normal, les retours de
portail, les cactus et une véritable ancienne sauvegarde sur une case
devenue bloquante.

## Positions des rencontres proposées

`safe_spawn_sites.json` donne des cases de sol et leurs approches vérifiées :

- Esprit de terre niveau 2 : Crossroads `(3,5)`, placeholder objet 1.
- Grunt orc niveau 2 : HanazuaCamp `(3,6)`, placeholder objet 1.
- Second esprit futur : CaveApproach `(7,7)`.
- Archer Kolkar niveau 7 : ValleyExit `(3,5)`, nouvel objet 2.
- Pillard Kolkar niveau 8 : ValleyExit `(7,5)`, nouvel objet 3.

Les scripts de recrutement, drapeaux persistants, alias d'espèces et groupes
de combats appartiennent aux modules de gameplay correspondants. Ces JSON
ne créent aucun ennemi dans la ROM actuelle.
