# v0.2.14 — proportions du shaman et sols plus calmes

Le shaman reprend le dessin natif archivé, avec une tête plus petite par
rapport au corps. Les vues de face et de dos ainsi que leurs trois poses
sont encodées séparément. La masse et le bouclier restent reconnaissables.

Les canvases restent à **56×56 de face** et **48×48 de dos** ; les sprites
du monde restent à 16×16. Le sprite de dos au repos occupe désormais
42×38 pixels, proche du guerrier à 46×40, avec les pieds à la même hauteur.
La face au repos occupe 54×44 pixels, contre 54×45 pour le guerrier.
Le rapport tête/corps est corrigé, plutôt que de réduire uniquement le
personnage entier.

## Sources et dérivations

- Shaman : `gfx/native_actor_restore_v0213/peon/`, issu des paquets
  historiques `gfx/peon_classes/shaman/`. Masques de tête mesurés,
  redimensionnement au plus proche voisin, repositionnement sans lissage.
  La petite séparation du col de la pose levée reprend uniquement sa
  ligne de col originale. La pose de lancement conserve son angle et son
  aura entière, ajustés ensemble. Les palettes restent inchangées.
- Sorties séparées : `gfx/shaman_proportions_v0214/` ; PNG transparents,
  comparaisons et hashes dans `references/generated/shaman_proportions_v0214/`.
- Grain du sol :
  `references/characters/peon_of_warcraft_environment_pack_v2_art_quality/durotar_valley/ground_durotar_dirt_01_32x32.png`.
  Les deux groupes de grains de base sont extraits de ce PNG, aux mêmes
  coordonnées. Le fond est la couleur de terre native existante. Les
  grandes zones ont quatre pixels de grain par bloc 32×32 ; des plaques
  ponctuelles en conservent 22. Ce sont des dérivations autorisées du sol,
  distinctes des sources originales intactes.
- Sorties environnementales séparées : `gfx/quieter_ground_v0214/`.
  Les treize cartes conservent 109 110 pixels opaques de décor et 4 452
  cellules de collision. Palettes, priorité, bâtiments, grotte, piliers et
  événements restent identiques. Huit fichiers `.blk` utilisent des alias
  de sol pour les plaques, avec les mêmes collisions.

Le budget maximal est de 209 motifs sur 216 à Razor Hill. Le chemin VRAM
192/216 introduit en v0.2.13 demeure inchangé. Aucun nouveau champ de
sauvegarde ni changement de mécanique de combat n'est ajouté.

## Build et vérification

Build sûr : `python3 tools/build_peon_v0214.py`. Il préserve 207 sorties
historiques et 301 paquets natifs, sans relancer les anciens générateurs.
La compilation propre depuis les fichiers Git produit exactement la ROM
testée : `4c6daec032ce7b9692fe37c7e385f517a6cff6091dcb37b33ac8f337059649a9`.

ROM : `releases/v0.2.14/peon_of_warcraft_v0_2_14.gbc`.
Rapports : `references/generated/v0214/validation.json` et
`references/generated/v0214/fresh_build_validation.json`.

Les tests utilisent les boutons ordinaires et des lectures de VRAM/OAM
dans PyBoy, sans écrire de RAM, charger d'état ou ouvrir une sauvegarde de
l'utilisateur. Les captures sont prises dans la ROM compilée ; les images
de comparaison des sources sont identifiées séparément. Les passages de
The Den vers la zone 2 gardent leurs deux voies dans les deux sens. Le
passage au nord du PNJ cactus et l'intérieur des maîtres sont vérifiés.
Mana, rage et couleurs des types restent fonctionnelles pour les trois
classes et le diablotin actif.

En-tête GBC, MBC3 avec RTC, 32 Kio de RAM et sommes de contrôle validés.
Aucun test sur un appareil physique ModRetro n'est revendiqué.
