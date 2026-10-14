# v0.2.15 — personnages du monde plus lisibles

Les corps du joueur, des PNJ et des créatures du monde passent de 16×16 à
24×24 pixels, soit 50 % de plus en largeur et hauteur. Les trois maîtres de
classe étaient déjà en 24×24 et restent inchangés. Le déplacement et les
collisions gardent leur grille native de 16 pixels.

## Sources et conversion

- PNG canoniques : `references/characters/peon_world_character_sheets_split/`.
- Péon et shaman : indices natifs archivés dans
  `gfx/native_actor_restore_v0213/peon/overworld.bin`.
- Guerrier et démoniste : `gfx/approved_player_v0212/`.
- Péon endormi : ancien sprite natif `gfx/sprites/peon_sleeping.2bpp`.
- Diablotins, orcs, trolls, créatures et Yarrog : silhouettes des PNG fournis,
  avec les substitutions de vues sources endommagées déjà documentées.
- Crawler et les deux Kolkar : aucun PNG canonique correspondant n'est présent ;
  leurs corps natifs historiques sont agrandis sans nouveau dessin. Les Kolkar
  utilisent la palette cuir/contour sombre correspondant à leur source.

L'import `tools/import_peon_world_actors_v0215.py` écrit uniquement des sorties
séparées dans `gfx/world_actors_v0215/` et
`references/generated/world_actors_v0215/`. Les 495 PNG sources sont conservés
et leurs hashes enregistrés. Le redimensionnement utilise le voisin le plus
proche, sans lissage ni détail inventé. Les couleurs des PNJ viennent du PNG
source et sont converties par tuile 8×8 vers trois couleurs opaques GBC. La
transparence reste l'indice zéro. Les héros conservent leurs indices natifs.

Chaque corps possède 12 poses de 9 tuiles. Les poses sans animation originale
réutilisent leurs images sources ; aucune marche manquante n'est dessinée.
Les masques omettent les tuiles entièrement transparentes. Les attributs
séparés donnent la palette de chaque tuile. Le manifeste décrit les sources,
l'ordre front/dos/gauche/droite et les substitutions exactes.

## Moteur et limites mesurées

Le moteur charge seulement la pose courante de chaque objet, dans une zone
réservée de 117 tuiles en banque VRAM 1 (`$8000..$874F`). Les petites images
natives et les maîtres utilisent la banque 0 sous les tuiles du HUD. Les tuiles
des décors étendus et les polices restent hors de cette zone. Le cache est
transitoire, hors sauvegarde, et invalidé au retour des menus et combats. La
file DMA native de Crystal charge atomiquement les neuf tuiles avant le travail
audio de VBlank ; aucune nouvelle routine d’interruption n’est ajoutée. Les
masques, couleurs et positions relatives sont réutilisés tant que la pose ne
change pas. Le HUD réutilise les comptes de chaque ligne déjà calculés.

La Game Boy Color dispose de 40 objets graphiques, dont 10 au maximum sur une
même ligne. Un corps 24×24 peut utiliser neuf objets. Le moteur vérifie ces
deux limites avant d'ajouter un corps entier. Le joueur, l'interlocuteur puis
les PNJ proches sont prioritaires. Les acteurs éloignés peuvent être masqués
dans une scène chargée. Les marqueurs de quête et les émotes sont remontés
au-dessus des nouvelles têtes. La barre de ressources du monde peut être
omise quand les corps complets ne lui laissent plus six objets ; elle conserve
son fonctionnement dans les scènes qui lui laissent de la place et en combat.

Ce changement conserve les cartes, décors, bâtiments, piliers, warps, combats,
équipements et formats de sauvegarde de la v0.2.14. Les palettes de monde
récupèrent la famille verte/cuir et la famille rouge/or des diablotins ; les
palettes de combat et les substitutions de la salle des maîtres sont conservées.

## Compilation et preuves

Build sûr : `python3 tools/build_peon_v0215.py`. Les anciens générateurs de
remplacement et les paquets graphiques importés restent gelés.

La ROM, les captures de l'émulateur et les rapports de validation sont publiés
sous `releases/v0.2.15/` et `references/generated/world_actors_v0215/`.
Les comparaisons PNG de l'import sont des décodages statiques ; seuls les
répertoires runtime et les captures de la release prouvent l'affichage du jeu.
Un test sur une console ModRetro physique n'a pas été effectué.

### Vérification de la ROM publiée

ROM SHA256 : `e6be1f0a31ce390f07d8d3a181248ac7945f2085692a3930bee3d4f54d6b8e5a`.
Une compilation depuis un dossier neuf, sans anciens objets, produit exactement
les mêmes fichiers ROM, symboles et map. La ROM fait 2 MiB, est déclarée CGB
uniquement et conserve le contrôleur MBC3, l'horloge et les 32 KiB de sauvegarde.

Les suites `runtime_e6be1f0a`, `lodge_continue_e6be1f0a`,
`battle_regression_e6be1f0a` et `performance_e6be1f0a`, sous
`references/generated/world_actors_v0215/`, vérifient cette même ROM. Les essais
utilisent les boutons normaux de l'émulateur, sans modifier sa RAM, charger un
état ou ouvrir une sauvegarde utilisateur.

- Monde : quatre directions des trois classes, poses de marche, palettes,
  données VRAM, corps complets, marqueurs de quête et scènes chargées. L'intro
  du péon simple ne montre réellement que la pose gauche imposée par le script ;
  ses autres poses sont vérifiées dans les paquets compilés.
- Auberge : les trois maîtres restent entiers, soit 27 cellules graphiques et
  939 pixels opaques contrôlés sur l'écran natif. Les trois classes reprennent
  correctement une sauvegarde réelle ; le compagnon du démoniste revient dehors.
- Combats : mana, rage, textes des types, PP, noms et proportions du dos du
  shaman sont conservés. Le changement forcé de compagnon après un KO suit les
  commandes ordinaires du ROSTER.
- Performance : au repos dans The Den, 60 mises à jour sur 240 images LCD,
  comme en v0.2.14. Quatre déplacements mesurés prennent 204 images contre 175
  dans la référence v0.2.14, soit environ 17 % de plus. La salle des maîtres
  reste à la même cadence au repos, avec 36 objets et six au maximum par ligne.

Le rapport agrégé et la compilation indépendante sont dans
`references/generated/v0215/`. Le ZIP distingue les captures réelles du jeu
des PNG transparents réutilisables et contient leurs hashes de contrôle.
