# Premier peon jouable

Le joueur à pied utilise un peon orc apprenti chaman, à la place de Chris ou Kris dans l'overworld. Les portraits, les icônes des menus, le vélo, le surf et la pêche gardent encore leurs graphismes Crystal. Les maps et la logique de déplacement restent inchangées. L'écran titre et la musique Warcraft ne sont pas intégrés dans ce jalon.

## Assets et rendu

`gfx/sprites/peon.png` est un vrai asset indexé de **16 × 192 pixels**, soit douze images de **16 × 16**. Il contient quatre repos, quatre pas A et quatre pas B, dans l'ordre face, dos, gauche, droite. Il utilise trois indices visibles et l'indice 0 transparent lors du rendu OBJ. Le PNG source est opaque en niveaux de gris pour respecter le convertisseur DMG de RGBDS ; les couleurs sont fournies par la palette verte déjà présente dans le jeu. La tenue et les accessoires utilisent donc la couleur chaude existante, pas les nuances brunes supplémentaires des maquettes.

Les pixels sont définis explicitement dans `tools/build_peon_sprite.py`, pas extraits des images de présentation générées. La masse, le bouclier et le petit signe de totem sur la ceinture sont très simplifiés pour rester dans les 16 × 16 pixels. La lisibilité artistique de ce premier asset peut encore être améliorée.

`PEON_SPRITE = 0` permet de garder le joueur en tête du tri, exigence de `GetSpriteVTile`. Ce type fournit 16 tuiles de repos et 32 tuiles de marche ; l'allocation réserve 32 emplacements dans chaque moitié concernée de la VRAM. Cela augmente le budget du joueur par rapport aux 12 emplacements initiaux. Les cartes vérifiées passent, mais toutes les cartes très chargées en sprites ne sont pas couvertes par ce test.

Les tables `data/sprites/peon_facings.asm` définissent le cycle repos/A/repos/B sans miroir OAM. Le renderer les utilise pour Chris/Kris à pied seulement ; les autres sprites et les facings spéciaux gardent les tables originales. Les deux chemins de sélection du joueur pointent vers le même peon ; le genre et le format de sauvegarde ne sont pas modifiés.

## Reproduction

Installer Pillow pour régénérer les images. Installer PyBoy 2.7.0 pour le contrôle en émulateur. La compilation normale n'a besoin ni de Pillow ni de PyBoy : le PNG est versionné.

```bash
cd /workspace/peon-of-warcraft
python tools/build_peon_sprite.py
make -j4 RGBDS=/workspace/toolchains/rgbds-1.0.4/
PYTHONPATH=/workspace/toolchains/pyboy-preview python tools/validate_peon_sprite.py
```

Le validateur utilise une copie temporaire de la ROM et ses propres fichiers RAM/RTC. Il ne lit ni ne modifie les sauvegardes personnelles. Des snapshots préparent les scénarios de déplacement ; le test final de reprise redémarre une nouvelle instance avec la sauvegarde normale du jeu, sans snapshot.

Le SHA-1 de Crystal d'origine ne doit plus être utilisé comme critère de réussite après cette modification intentionnelle. Le validateur enregistre le SHA-256 de la ROM testée.

## Validation

- Compilation RGBDS 1.0.4 réussie.
- Nouvelle partie, arrivée dans la chambre, palette verte et chargement exact des 48 tuiles vérifiés.
- Seize états de facing testés dans le renderer par instrumentation ; aucun miroir horizontal sur le joueur.
- Déplacement réel au D-pad dans les quatre directions, avec pas alternés et changement de coordonnées.
- Passage par les escaliers vers l'autre étage sur les maps originales.
- Comparaison des graphismes des PNJ présents après cette transition avec les données ROM attendues.
- Sauvegarde par le menu, arrêt, nouvelle instance, Continue et restauration de l'identité, de l'argent et de la position.

Preuves et captures : [galerie du peon dans le jeu](../references/generated/peon_in_game/README.md), [résultats détaillés](../references/generated/peon_in_game/validation_results.json).

La Chromatic physique, le son et les états de mobilité spéciaux ne sont pas testés dans ce contrôle. Le parcours New Game/Continue automatisé utilise le choix joueur par défaut ; le second choix pointe également vers l'asset peon mais n'a pas été parcouru manuellement dans cette validation.
