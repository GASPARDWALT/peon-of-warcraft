# v0.2.19 — silhouettes restaurées et maîtres illustrés

Les héros et plusieurs PNJ retrouvent les dessins compacts historiques du
péon et de ses classes. Leurs corps entiers sont présentés en **24 × 24**,
avec les directions et pas disponibles. Agrandir au plus proche un dessin
de 16 pixels ne crée pas de détail supplémentaire.

Les créatures utilisent leurs vues **WORLD** complètes. Les Kolkar archer et
raider viennent de la planche de centaures explicitement approuvée : torse
humain, cheval entier, équipement et quatre directions. Cette illustration
générée est convertie avec perte ; ce n'est pas un ancien sprite natif retrouvé.

Les maîtres disposent de bustes plus riches dans un cadre de **80 × 88** :

- **Kento Brandenhoof** : Tauren Shaman ; les deux cornes partent du crâne,
  séparées du bâton, avec fourrure, museau, étoffes bleues et pendentifs.
- **MoCMoc Zogzog** : maître Guerrier inspiré de **Garrosh**, brun et chauve,
  avec cicatrice, défenses, fer et hache. Son nom est conservé ; le Guerrier
  du joueur reste distinct.
- **Bismillah LesTenèbres** : Démoniste mort-vivant, visage osseux, robe
  violette, yeux lumineux et bâton à crâne ; illustration approuvée conservée.

Chaque buste entier vient du seul composant alpha approuvé de son atlas,
sans couper cornes ou armes ni importer les voisins. Les quatre scènes
d'accueil approuvées de v0.2.18 et leur paysage orange et rouge sont conservés.

## Sources et limites

Les originaux restent intacts ; crops, conversions et SHA256 sont documentés :

- [Sources et provenance world](../assets/world_readability_v0219/)
- [Manifest world](../gfx/world_readability_v0219/manifest.json)
- [Atlas approuvés des maîtres](../assets/class_portraits_v0219/README.md)
- [Manifest des portraits](../gfx/class_portraits_v0219/manifest.json)
- [Comparaisons statiques](../references/generated/class_selection_v0219/)

La Game Boy Color limite chaque tuile de 8 × 8 à quatre couleurs. Le monde
réserve une couleur à la transparence ; les portraits emploient cinq palettes
avec une encre commune. Réduction et palettes sont **avec perte**, sans lissage
ni prétention de récupérer une grille native dans une grande illustration.

Certaines poses sont répétées. Les Trolls partagent des familles historiques :
villageois/marchand, garde/chef et les deux Shamans. La panthère est une
variante sombre déclarée du tigre WORLD, pas son dessin original retrouvé.
Les corps restent entiers dans les limites OAM ; des acteurs éloignés peuvent
être masqués dans une scène dense.

Combats, sorts, équipe, quêtes, format des sauvegardes, décors et passages
restent ceux de la version précédente.

## Compilation et vérifications

Build : `python3 tools/build_peon_v0219.py`, avec les paquets natifs conservés.

**Validation finale : PASS** sur la ROM SHA256
`b91b687630810108452f3ff69a1e6cb9e9a2439ea745386adbebe29da80a0527`.

La compilation depuis un export Git propre donne les mêmes ROM, SYM et MAP.
Les sept rapports et 29 captures natives sélectionnées sont réunis dans le
[rapport final](../references/generated/v0219/validation.json).

- Trois classes : portraits, annulations, kit, SAVE/EXIT et Continue chaud/froid.
- Héros du monde : directions, pas disponibles, PNJ proches et scènes chargées.
- Maîtres du lodge : corps complets et palettes après dialogues et entraînement.
  Leurs bases de tuiles sont réassociées après réallocation. La fermeture du
  menu revient au mode de carte natif avant les déplacements ; le transfert
  plein écran ne réécrit plus le sol avec des attributs périmés.
- Le fond réellement visible dans la VRAM et les pixels du LCD sont vérifiés
  avant/après entraînement, déplacement et Continue, indépendamment du buffer
  d'attributs partiellement conservé par le défilement natif.
- Sanglier et deux Kolkar : corps, paquets ROM/VRAM, palettes et tous leurs
  pixels opaques vérifiés à l'écran. Parcours ordinaire The Den → Valley of
  Trials → Valley Exit, avec une fuite native à l'ouest. La sortie orientale vers
  Durotar Road ne fait pas partie de ce test d'illustrations.
- Quête du péon endormi en zone deux, récompense unique et équipe conservées.
- Les 499 PNG originaux et les paquets historiques de combat, maîtres et
  Lightning Bolt sont inchangés ; seuls les raccordements déclarés et les
  corrections de retour au monde diffèrent.

Le ZIP contient la ROM et les captures de cette ROM ; les comparaisons
statiques sont identifiées séparément. Le matériel physique ModRetro n'a pas
été testé.

Destinations de publication :
[ROM v0.2.19](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/codex/peon-v0.2.19/releases/v0.2.19/peon_of_warcraft_v0_2_19.gbc)
· [ZIP v0.2.19](https://raw.githubusercontent.com/GASPARDWALT/peon-of-warcraft/refs/heads/codex/peon-v0.2.19/releases/v0.2.19/peon_of_warcraft_v0_2_19.zip).
Les liens sont vérifiés par téléchargement après publication ; le rapport de téléchargement figure dans `references/generated/v0219/public_download_validation.json`.
