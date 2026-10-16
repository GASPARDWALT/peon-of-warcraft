# v0.2.20 — personnages natifs et fluidité

Les humanoïdes utilisent maintenant une grille native **32 × 32** : visage,
oreilles, cheveux, vêtements et équipement viennent de nouvelles vues WORLD
guidées par les sprites fournis. La réduction part directement des grandes
illustrations, avec conversion aux palettes GBC. Chaque direction possède
un repos et deux clés de pas éditées à cette résolution. Les JSON décrivent
les retouches et les variantes partagées ; aucune récupération exacte d'une
grille native dans les illustrations générées n'est revendiquée.

Il y a **19 familles 32 × 32** dans les sources, dont 15 liées au moteur, et
**20 familles 24 × 24** préservées. Les 30 familles réellement liées utilisent 90
paquets. Le sanglier approuvé et les deux Kolkar gardent exactement leurs
pixels, masques et palettes v19. Les cinq héros restent à 13 cellules OAM ou
moins dans toutes leurs poses : les trois maîtres peuvent rester complets
avec le joueur. La vue droite du Démoniste utilise le dessin entier réduit
à 26 × 31 dans le canevas 32 × 32, sans coupe d'arme ou de silhouette.

Les PNJ proches et leurs symboles de quête passent avant le familier facultatif.
Chaque corps est admis entier dans les limites de 40 objets et 10 par ligne ; un
familier ou un personnage éloigné peut être entièrement masqué en scène dense.
Le déplacement, les collisions et les sauvegardes gardent leur grille de 16 px.

Le sol ocre choisi est appliqué uniformément aux champs et chemins de 13
cartes, y compris sous les pixels transparents des décors. Les 110 174 pixels
opaques des accessoires et les 4 452 octets de collisions sont préservés.
Les palettes BG3 supplémentaires sont limitées à TheDen, RazorHill et
OrgrimmarGate ; les braises intérieures gardent leurs phases originales.

## Cadence et corrections moteur

Le CPU CGB démarre en double vitesse. Le travail de rendu et de défilement
se place dans le budget natif de deux VBlanks, avec une table directe pour
les descripteurs et des caches transitoires pour les cellules OAM.

Sur les trois scènes mesurées, la cadence passe de **15 à 30 mises à jour/s**.
Les quatre déplacements contrôlés prennent **97 images LCD contre 204** en
v19 ; chaque case utilise toujours huit déplacements caméra de 2 pixels.
Quelques intervalles de 1 puis 3 images subsistent : ce n'est pas une promesse
de 30 images distinctes parfaitement régulières. Le son reste calculé une fois
par image LCD et chaque service complet du GameTimer avance d'une image.

Deux erreurs ont été corrigées avant livraison :

- Le feu exécuté pendant VBlank utilise un garde local, préservant les
  registres et la banque WRAM. Il ne réutilise plus les temporaires d'un
  `farcall` interrompu, qui pouvaient corrompre les retours et bloquer la marche.
- Les transferts HDMA demandent le nombre exact de blocs et attendent leur
  fin. Réécrire un statut inactif `$ff` après l'avoir masqué relançait 128 blocs
  de copie et écrasait les sols, les espaces et les bordures en combat.

Les graphismes et petites métadonnées utilisent des sections indépendantes
pour tenir dans la ROM 2 MiB/MBC3 existante, sans retirer de détails.

## Vérification de la livraison

ROM SHA256 :
`163fae77fd496829f1367d6a8baf55b70fd4e71cc9f0368c9626ffb3a7416b1c`.

[Rapport final et liste explicite des captures LCD](../references/generated/v0220/validation.json).
Six rapports PASS portent sur cette même ROM :

- Trois classes, quatre vues, palettes, VRAM, OAM, pixels LCD, dialogues,
  entraînement et sauvegarde/Continuer à froid. La marche observe les trois
  adresses de pose ; la comparaison stricte des pixels LCD couvre les vues stables.
- 126 cases en quatre directions sans redémarrage, puis combat complet :
  MACE STRIKE gratuit, Lightning Bolt horizontal coûtant 15 mana, retour au monde.
  Fond blanc, six bordures, dos Shaman 48 × 48 et 30 glyphes de victoire vérifiés.
- Accueils et portraits approuvés, annulation, remplacement refusé et
  Continue chaud/froid des trois classes.
- Cadence, déplacements, son et horloge mesurés en images LCD émulées.
- Reconstruction depuis un export propre des sources indexées : ROM, symboles
  et carte de liaison identiques à l’octet près aux fichiers testés.
- 499 PNG originaux, 7 755 fichiers historiques et paquets de combat/UI
  conservés ; 13 exceptions moteur nommées et leurs diffs sont documentés.

Build : `python3 tools/build_peon_v0220.py`. Les sources et paquets natifs
sont versionnés ; les anciens générateurs d'art restent bloqués. Les captures
du ZIP viennent uniquement de cette ROM. Les aperçus d'import statiques sont
rangés séparément. Le matériel physique n'a pas été testé.
