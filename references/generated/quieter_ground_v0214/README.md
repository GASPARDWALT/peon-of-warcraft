# Sols plus calmes — v0.2.14

La demande du 14 octobre 2026 autorise cette dérivation du sol : réduire le
grain répété et garder les détails à quelques endroits. Les PNG fournis sont
conservés. Les personnages, bâtiments, végétaux, rochers, pylônes, grotte,
palettes régionales, priorités, collisions, événements et warps gardent leur
contenu précédent.

La terre utilise son ton natif existant. Deux groupes complets de petits grains
sont prélevés, à leurs coordonnées originales, dans
`references/characters/peon_of_warcraft_environment_pack_v2_art_quality/durotar_valley/ground_durotar_dirt_01_32x32.png`.
Le sol calme contient quatre pixels de grains par bloc de 32×32. Les petites
plaques ajoutent trois groupes irréguliers du même PNG, soit 22 pixels par bloc.
Les contours de ces groupes ne sont pas redessinés. Les chemins pâles restent
lisibles. Le grain dense autour des décors protégés reste intact.

L'import limité à `tools/import_peon_quieter_ground_v0214.py` produit les 13
paquets extérieurs séparés dans `gfx/quieter_ground_v0214/`. Il conserve les
quatre premières tuiles animées, la réserve de fonte et l'allocation native de
216 tuiles. La carte la plus chargée utilise 209 tuiles. Les alias de quelques
plaques changent huit fichiers `.blk`; aucune collision de déplacement ne
change. La preuve d'import porte sur 109 110 pixels opaques du décor, 4 452
cellules de collision et toutes les palettes/priorités par cellule.

`*_comparison_native.png` et `*_160x144.png` sont des compositions des paquets
natifs, pas des captures de gameplay. Les vraies captures d'émulateur sont dans
`runtime_4c6daec0/shaman/`, avec le rapport `runtime_4c6daec0/validation.json`.

Ce playtest a utilisé le candidat exact
`4c6daec032ce7b9692fe37c7e385f517a6cff6091dcb37b33ac8f337059649a9` :

- nouvelle partie Shaman, sans édition de RAM ni état d'émulateur ;
- The Den, zone 2 et passage au-dessus du donneur de quête des cactus ;
- les deux voies de chaque passage entre ces zones, dans les deux sens ;
- un pas de sortie sûr après chaque arrivée ;
- intérieur conservé avec les trois maîtres, leurs 27 tuiles et leurs pixels LCD ;
- neuf vérifications des tuiles et attributs affichés par le PPU, des 192 tuiles
  de base et des 24 tuiles supplémentaires à l'extérieur ;
- aucune collision entre OAM et la réserve de graphismes du fond.

Reproduction : `python3 tools/import_peon_quieter_ground_v0214.py --apply`.
Le mode `--apply-staged` lie les résultats déjà vérifiés. Le mode
`--verify-rom ROM --symbols SYM` contrôle les liaisons de la ROM sans régénérer
les graphismes. Le build central reste à la charge du constructeur sûr v0.2.14.
