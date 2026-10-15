# v0.2.16 — détails des personnages et attaques de terre

Les modèles du monde restent en 24×24. Les quatre héros sont réimportés depuis
leurs vues **world** dédiées, directement à cette résolution. Cette conversion
évite la perte de détail cumulée par une réduction à 16×16 puis un agrandissement.
Les PNG originaux restent intacts ; les nouvelles sorties sont séparées dans
`gfx/world_actors_v0216/` et documentées dans
`references/generated/world_detail_v0216/`.

Les PNJ restent fondés sur leurs PNG world fournis. Les sources tronquées
gardent leurs substitutions documentées ; les conversions corrigent les tons
de peau et de cuir auparavant trop souvent réduits au noir. Les palettes
matérielles, les neuf tuiles de chaque pose, la grille de collisions 16px et le
moteur de corps complets de la v0.2.15 restent en place.

## Personnages principaux en combat

Les corps occupent davantage leurs cadres natifs : 48×48 de dos et 56×56 de
face. Le shaman conserve ses proportions tête/corps et ses trois poses
originales, avec une silhouette de dos de 47×42 contre 42×38. Le guerrier
atteint 48×41 et le démoniste 45×48. Les vues du guerrier et du démoniste sont
réimportées depuis les images approuvées, avec leurs propres couleurs de
peau, de cuir, de métal et de robe. Les mains du démoniste retrouvent leur vert.
Ces modifications ne changent pas les sprites des adversaires.

Sources, boîtes visibles, palettes, transparence et comparaisons statiques :
`gfx/combat_heroes_v0216/manifest.json` et
`references/generated/combat_heroes_v0216/`. Une comparaison d'assets ne
constitue pas une capture du jeu : les preuves d'affichage viennent des tests
de la ROM compilée.

## Petit caillou

Le caillou commence avec **STRIKE**, **MUD-SLAP** et **ROCK THROW**. STRIKE est
un contact physique sans arme. MUD-SLAP projette de la terre ; ROCK THROW lance
un rocher en arc, suivi de poussière et d'un impact. Les animations utilisent
les vraies tuiles natives de rochers et de sable. Lightning Bolt est conservée.

Les attaques de départ utilisent les PP normaux des compagnons. MACE STRIKE
du héros et STRIKE du caillou coûtent zéro mana. Les évolutions restent au
niveau 8 vers Veine Tellurique, puis au niveau 12 vers Roche Élémentaire.

La reprise d'une sauvegarde reconnaît uniquement l'ancien duo de départ
POUND/THUNDERSHOCK des espèces de cette famille. Elle le remplace par
STRIKE/MUD-SLAP, conserve les PP de Strike, plafonne ceux de Mud-Slap sans
les restaurer et ajoute Rock Throw seulement dans un emplacement libre.
Les autres attaques, surnoms, niveaux, statistiques et membres sont conservés.

## Vérification et limites

Compilation sûre : `python3 tools/build_peon_v0216.py`. Les anciens générateurs
de dessins restent désactivés. Les paquets de toutes les versions importées
sont des entrées gelées du build.

Les limites de la Game Boy Color restent 40 objets graphiques et dix sur une
même ligne. Le joueur et les interlocuteurs proches ont priorité ; certains
acteurs éloignés et le HUD facultatif peuvent être omis dans les scènes chargées.
Les quatre directions sont contrôlées en émulateur, avec les palettes, les
pixels de la ROM, les dialogues, les combats et les sauvegardes. Un test sur
console ModRetro physique n'a pas été effectué.

### Résultats de la ROM finale

SHA256 : `3c25adf84a9278c826f3f873560991ee6483d6bc02641782afb1e9f9810aa2dc`.
Une compilation depuis un dossier neuf, sans objets réutilisés, produit les
mêmes ROM, symboles et map. La ROM garde le format CGB, 2 MiB, MBC3 avec
horloge et 32 KiB de sauvegarde.

- **Monde : PASS** sur les trois classes et quatre directions ; les 30 paquets
  exportés correspondent exactement aux données de la ROM. Masques, couleurs,
  pixels LCD, marqueurs `!/?` et admission des corps entiers vérifiés. Maximum
  observé : 40 objets et neuf sur une ligne. Les quatre modèles source sont
  des vues fixes ; base/shaman utilisent un léger bob d'un pixel. Il ne s'agit
  pas de trois nouvelles poses de marche dessinées.
- **Combat : PASS** sur les trois héros et le diablotin actif. Chaque dos est
  vérifié sur ses 576 octets, attributs, palettes et 2 304 pixels LCD réels.
  Mace Strike a laissé la mana à 72/72 ; Lightning Bolt a consommé 15 et
  Shadow Bolt 25. Types en couleur, textes et PP conservés.
- **Maîtres et sauvegardes : PASS** pour les trois classes, les 27 cellules des
  trois maîtres et leurs 939 pixels opaques ; quête du dormeur et récompense
  unique préservées. Sauvegardes natives et cold Continue vérifiés.
- **Caillou : PASS** sur la vraie quête puis la capture, les trois attaques
  choisies et lancées, leurs PP et les effets de terre. Le lancer de rocher a
  été observé dans les deux sens. Pics observés : 23 objets et huit par ligne.
  La reprise d'une sauvegarde privée v0.2.15 ne modifie que les cinq octets
  attendus de l'ancien kit du caillou ; le reste des données contrôlées reste
  identique. Les attaques de niveaux supérieurs et les évolutions 8/12 sont
  vérifiées dans la ROM liée, sans prétendre à une partie jouée au niveau 15.

Rapport agrégé et build indépendant : `references/generated/v0216/`.
Les captures réelles du monde sont dans
`references/generated/world_detail_v0216/runtime_3c25adf8/` ; les preuves de
quête et animations sont dans
`references/generated/rock_earth_moves_v0216/runtime_3c25adf8/`.
