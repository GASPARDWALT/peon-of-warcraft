# Péon — nouvelle direction artistique

Art source indépendant : aucune modification de la ROM.

## Ouvrir les dessins

Ouvrir `index.html` dans un navigateur. Le damier est uniquement un fond de prévisualisation. Aucun fichier externe ni serveur n’est requis.

## PNG natifs

24/24 fichiers présents. Chaque personnage utilise six fichiers dans `sprites/<personnage>/` :

- `world_front.png`, `world_back.png`, `world_left.png`, `world_right.png` : 16 × 16 px.
- `combat_front.png` : 56 × 56 px.
- `combat_back.png` : 48 × 48 px.

Les sprites natifs ont une transparence binaire, alpha 0 ou 255. Les fichiers `previews/` sont des agrandissements entiers avec répétition exacte des pixels et ne remplacent pas les PNG natifs. Les références de conception dans `originals/` restent intactes. Les couleurs sources ne sont pas automatiquement réduites. Les dimensions natives sont exactes. Les couleurs RGBA sources sont préservées ; leur affectation aux palettes GBC est une étape distincte. L’art n’est pas encore intégré ni validé dans une ROM.

## Sélection des maîtres

Le dossier `selection/` contient trois propositions d’écran 160 × 144 px, des portraits transparents et une page interactive. Ces images sont des maquettes natives, pas des captures de la ROM.

## Réutiliser les outils

Node.js et le paquet `pngjs` sont nécessaires uniquement pour reconstruire la galerie ou écrire des pixels. Le ZIP et la galerie sont utilisables sans Node.js.

`node tools/build_pack.cjs` reconstruit la galerie pour les dessins disponibles.

`node tools/build_pack.cjs --require-complete --zip` exige toutes les poses, contrôle dimensions et transparence et crée l’archive.

`native_png.cjs` expose `writeIndexed(spec, output)`, `sampleRecoverableGrid(input, geometry, output)`, `writeNearestPreview(input, output, scale)` et `inspectPng(input)`. Les sorties sont limitées à ce nouveau dossier. `sampleRecoverableGrid` exige les coordonnées explicites des cellules et ne réalise pas de redimensionnement global ni de quantification.
