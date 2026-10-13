# Environment Pack v2 — première carte de test Durotar

Le premier test Durotar est compilé et vérifié dans la ROM native : trois cartes, hutte et grotte accessibles, collisions, coffre, feu animé et bande terre → transition → sable rouge. Le parcours final est **PASS** sur le même SHA-256 que le binaire distribué. La compression utilise le profil natif du dépôt. Les pixels canoniques restent conservés ; la bande raccorde les terrains, avec des différences visibles entre leurs bords sources.

Cette étape porte sur `durotar_valley/`, avec trois assets globaux du même pack pour le coffre et les deux frames du feu. Les autres biomes sont inventoriés pour conserver une vue complète du pack ; ils ne sont pas importés pendant cette étape. Le mur et le sol du pipeline CAVE existant servent de bordure et de salle d'inspection. Les combats, classes, quêtes et cartes de production existantes restent hors du périmètre de ce test de décor.

## Source canonique et conservation

Le commit [`64bfb4cbf75ca83b05f34401c520a099a5e25f54`](https://github.com/GASPARDWALT/peon-of-warcraft/commit/64bfb4cbf75ca83b05f34401c520a099a5e25f54), nommé `Add_Map_environment_pack_v2_art_quality`, ajoute uniquement l'archive `references/characters/peon_of_warcraft_environment_pack_v2_art_quality.zip`.

- SHA-256 de l'archive : `5a9b27fe4a8c20934654388058f635726e2e3f477c131b27efff687fc2c1bdc0`.
- Dossier canonique : `references/characters/peon_of_warcraft_environment_pack_v2_art_quality/`.
- Instructions suivies : [`docs/CODEX_IMPORT_AND_IMPLEMENT_MAPS.md`](../references/characters/peon_of_warcraft_environment_pack_v2_art_quality/docs/CODEX_IMPORT_AND_IMPLEMENT_MAPS.md), dans ce dossier.
- Inventaire mesuré : [`source_inventory.json`](../references/generated/map_tests/source_inventory.json).

Les 182 fichiers extraits correspondent octet pour octet aux membres du ZIP : 166 PNG d'assets natifs, 11 PNG d'aperçu ou d'atlas, et cinq documents ou manifestes. Les noms, dimensions, transparences, empreintes et fins de ligne des sources sont conservés. Les conversions et fichiers de carte sont des sorties séparées.

| Dossier natif | Assets | `ground` source | `prop` source | `derived` source |
| --- | ---: | ---: | ---: | ---: |
| Durotar / vallée | 37 | 8 | 12 | 17 |
| Razor Hill | 34 | 6 | 14 | 14 |
| Sen'jin Village | 35 | 8 | 12 | 15 |
| Echo Isles | 44 | 12 | 8 | 24 |
| Objets partagés | 16 | 0 | 16 | 0 |
| **Total** | **166** | **34** | **62** | **70** |

Ces trois types sont les valeurs du manifeste fourni, pas une décision de rendu dans le moteur. Les 28 catégories mesurées sont : sols 25, chemins et passerelles 25, transitions 24, rives 16, végétation 11, palissades 10, eau 8, feux 7, bâtiments 4, totems 4, rochers 3, mobilier de camp 3, caisses/barils/sacs 3, bannières 2, décors de plage 2, bateaux/filets 2, coffres 2, plantes récoltables 2, minerais 2, objets de quête/ressource 2, râteliers 2 ; puis un enclos, un tas d'ossements, un pont, une entrée de grotte, une ruine, un poste de garde et un plancher de bois. Chaque fichier conserve sa catégorie et son biome dans l'inventaire.

## Contraintes mesurées avant import

Les 166 assets ont des dimensions multiples de huit et une transparence binaire. Les terrains sont composés de cellules natives de 8 × 8 dans des canevas de 32 × 32 ; les props et bâtiments utilisent des canevas multiples de huit. Les PNG d'atlas et d'aperçu ne sont pas traités comme des tuiles prêtes à charger.

Deux points demandent une liaison explicite dans le premier test :

- Les fichiers Durotar nommés `path_durotar_straight_horizontal_32x32.png` et `path_durotar_straight_vertical_32x32.png` montrent les axes opposés à leurs noms. Les sources ne sont pas renommées ou redessinées ; le manifeste d'import doit expliquer leur orientation réelle dans la carte. Le même problème est inventorié pour les chemins de Razor Hill, différés ici.
- La bannière Durotar de 16 × 48 est visible dans son tiers inférieur (`bbox [0,32,15,48]`). Le cactus haut de 16 × 32 est visible dans sa moitié basse (`bbox [4,16,14,32]`). Le placement doit tenir compte de ces marges natives sans inventer des pixels ni tronquer silencieusement le canevas.

Les quatre frames d'eau numéro 02 de Sen'jin et Echo Isles demandent également une réduction de palette ; elles sont signalées dans l'inventaire et restent hors du premier import. Aucun des 37 PNG Durotar n'a les mêmes pixels RGBA complets qu'un autre. Des variantes de terrain éventuellement reportées pour budget doivent donc être décrites comme des variantes alternatives, pas comme des doublons exacts.

## Chaîne native et audit moteur

Le build initial de référence a compilé avant l'import, avec le SHA-256 `ae084fd2c5fb9d38b949c4dae0f26e25b4c819406d05874f1054bd9bd4c75b10`. Il identifie la ROM de base ; il ne constitue pas le résultat de la carte de test.

Le moteur utilise une tuile matérielle de 8 × 8 et un bloc de carte de 32 × 32, soit seize tuiles. La collision est définie séparément pour les quatre cellules de déplacement de 16 × 16 de chaque bloc. Les grandes silhouettes de 64 × 64 sont composées dans plusieurs blocs de fond et ne sont pas forcées dans des objets mobiles.

La chaîne de conversion et de chargement est la suivante :

1. Lire le PNG canonique et vérifier son empreinte. Un asset transparent est composé sur le fond voulu en conservant son échelle et son ancrage ; la transparence du PNG source reste conservée.
2. Découper en cellules de 8 × 8, attribuer les couleurs RGB555 et les familles de palettes GBC, puis dédupliquer les motifs compatibles. Une conversion de palette est enregistrée séparément ; elle ne remplace pas le dessin source.
3. Produire les données 2bpp indexées et leur compression native, avec le même ordre de tuiles que le chargeur. Le pipeline normal du dépôt utilise `rgbgfx`, `tools/lzcompress` et les règles du `Makefile`. L'importeur dédié `tools/import_peon_environment_v2.py` écrit directement les motifs indexés et les PNG d'inspection correspondants, puis utilise `tools/lzcompress --matching --align4`, conformément au profil de `gfx/lz.mk`. Ce profil permet de reproduire les mêmes octets compressés dans une copie neuve. Il importe des fonctions pures de conversion existantes sans exécuter un ancien générateur de cartes ou de dessins.
4. Produire les métatuiles 4 × 4, les attributs de palettes/banques et la table de collisions à quatre entrées par bloc. Contrôler le budget du chargeur : au plus 192 motifs de décor et moins de 128 métatuiles par carte, avec les tuiles de texte et d'animation protégées.
5. Écrire les `.blk`, puis déclarer les cartes dans `constants/map_constants.asm`, `data/maps/maps.asm`, `data/maps/attributes.asm`, `data/maps/blocks.asm` et `data/maps/scripts.asm`. Les dimensions et les liens de porte doivent correspondre aux coordonnées des événements de chaque `maps/*.asm`.
6. Charger les paquets dédiés par les en-têtes de tileset et `home/map.asm:LoadMapTileset`, avec les palettes de fond de `engine/tilesets/map_palettes.asm`. La table standard et ses pointeurs sont définis dans `data/tilesets.asm` ; les données graphiques/collisions standard sont incluses par `gfx/tilesets.asm`.
7. Compiler le target dédié `pokecrystal_environment_test.gbc` avec RGBDS 1.0.4 et `PEON_ENVIRONMENT_TEST`. Son arrivée directe sur la carte de test est limitée à cette compilation. La ROM de production n'est pas remplacée par un démarrage de test.
8. Lancer cette ROM exacte, marcher dans la carte, vérifier les collisions, traverser les portes dans les deux sens et conserver les captures natives de 160 × 144 ainsi que les preuves sur son SHA-256.

Les cartes ajoutées appartiennent au groupe 26, après les identifiants existants. Chacune mesure 12 × 10 blocs, soit 384 × 320 pixels et 24 × 20 cellules de déplacement.

| Carte | Numéro | Motifs utilisés / budget | Métatuiles |
| --- | ---: | ---: | ---: |
| `PeonEnvironmentTest` | 30 | 181 / 192 | 16 |
| `PeonEnvironmentTestAnnex` | 31 | 186 / 192 | 29 |
| `PeonEnvironmentTestCave` | 32 | 187 / 192 | 21 |

Les paquets chargés ont tous 192 motifs, avec un remplissage des cases inutilisées. Ils utilisent sept familles RGB555 calculées depuis les couleurs des sources ; la huitième famille de l'interface reste inchangée. Les références graphiques de la seconde banque portent explicitement le bit de banque. Les motifs physiques `$60–$7f` restent réservés au texte ; les quatre motifs `$00–$03` sont réservés au feu animé. Les métatuiles restent sous la limite de 128.

Le manifeste [`import_manifest.json`](../references/generated/map_tests/import_manifest.json) donne les couleurs, empreintes, sources, placements, ouvertures visibles des chemins et paquets exacts. Le contrat [`test_contract.json`](../references/generated/map_tests/test_contract.json) donne l'arrivée `(12,17)`, les obstacles, points d'interaction et six liens de porte. La hutte et l'entrée de grotte de 64 × 64 conservent leur canevas complet sur quatre blocs. Elles ouvrent la même salle d'inspection, avec deux points d'arrivée et de retour distincts. Cette salle n'est pas un nouvel intérieur de jeu avec quêtes ou combats.

Les 31 assets Durotar utilisés conservent leur échelle 1 et leur canevas complet. Les six variantes différées pour budget sont `ground_durotar_dirt_02/03/04_32x32.png` et `ground_valley_redsand_02/03/04_32x32.png`. Leurs noms complets et empreintes sont dans le manifeste ; aucune variante n'est remplacée par un nouveau dessin. Les trois ajouts globaux sont `chest_shared_closed_16x16.png` et `campfire_shared_frame_01/02_16x16.png`. Le cycle de feu est `01 → 02 → 01`, soit trois frames temporelles à partir de deux PNG distincts, sur quatre motifs par frame.

Les bordures et la salle reprennent les blocs 1 et 2 de `data/tilesets/cave_metatiles.bin` depuis `gfx/tilesets/cave.png`, avec conversion de couleurs documentée. Cette reprise suit l'option de pipeline cave existant donnée par le document canonique. Elle n'est pas présentée comme un dessin d'intérieur fourni dans le pack v2.

La disposition finale ajoute dans cette salle une bande continue de trois blocs : terre aux coordonnées de bloc `(3,2)`, transition terre/sable à `(4,2)`, puis sable rouge à `(5,2)`. Les huit échantillons de transition restent visibles ailleurs. Ce raccord est praticable et conserve les pixels sources, sans repeindre leurs bords. Les textures canoniques séparées ont des couleurs de bord différentes : la continuité de la bande ne doit pas être décrite comme un raccord de pixels parfaitement invisible.

Pour reproduire l'inventaire et la compilation dédiée :

```sh
python3 tools/inventory_peon_environment_v2.py
python3 tools/build_peon_environment_v2.py
```

Le second outil compile les helpers C nécessaires et gèle les 207 sorties des anciens générateurs avant de construire ses propres objets `_environment_test.o`. Il refuse une sortie canonique manquante ou un ancien générateur dans le plan make. `PEON_RGBDS` permet de choisir le dossier de RGBDS 1.0.4 et `PEON_JOBS` le parallélisme. Il ne publie rien. Les options `--no-import` et `--normal` servent respectivement à recompiler les paquets déjà figés et à vérifier l'entrée normale du jeu ; elles ne remplacent pas le parcours de la carte de test.

## Vérification et livrables

ROM finale : [`peon_environment_v2_durotar_test.gbc`](../releases/environment-v2-durotar-test/peon_environment_v2_durotar_test.gbc), SHA-256 `7cd599fc9c19ac6f8e3f579051aa60b8036dc60069f07b357d7be419cf107425`. Les symboles et la carte de liens accompagnent le même binaire. Le rapport de compilation est [`build.json`](../references/generated/map_tests/build.json). La reconstruction sans objets précompilés est **PASS**, avec les mêmes octets et le même SHA, dans [`fresh_rebuild.json`](../references/generated/map_tests/fresh_rebuild.json).

Le [`ZIP de test`](../releases/environment-v2-durotar-test/peon_environment_v2_durotar_test.zip) contient la ROM, ses symboles, la carte de liens, le README et le manifeste.

La vérification finale [`runtime/validation.json`](../references/generated/map_tests/runtime/validation.json) est **PASS** sur ce SHA : un nouveau jeu, 25 actions et 15 180 frames, sans chargement d'état d'émulateur, injection RAM ni ouverture de sauvegarde utilisateur. Elle confirme :

- Déplacement et défilement dans les trois cartes, avec 188 motifs statiques, les métatuiles, sept palettes de décor, attributs et pixels LCD correspondant aux paquets compilés. Les pixels recouverts par le joueur ou l'interface sont exclus explicitement de la comparaison du fond.
- Cinq sondes bloquantes : cactus, mur de hutte, mur de palissade, feu et rocher ; les coordonnées restent inchangées.
- Six passages ordinaires : aller-retour entre test et annexe, entrée et sortie par la hutte, puis entrée et sortie par la grotte. Le pas automatique hors des portes est observé séparément de la case d'arrivée de l'événement natif.
- Dialogue d'inspection et coffre utilisables. Le premier examen ajoute un objet ; le deuxième laisse la quantité inchangée. Ce coffre de test ne constitue pas un nouveau système de quête.
- Sur 240 frames de feu, deux états distincts sont réellement observés dans la VRAM et à l'écran ; la séquence des sources est `01 → 02 → 01`. Le transfert des quatre tuiles conserve le paquet de feu fourni.
- Traversée de la bande terre/transition/sable par cinq pressions Droite : `(6,5) → (7,5) → (8,5) → (9,5) → (10,5) → (11,5)`. Les deux frontières de blocs sont franchies avec les boutons ordinaires ; les cellules et pixels natifs correspondent au trio source.

Captures réelles de la même ROM, en 160 × 144 avec versions `4x` agrandies par pixels entiers :

| Vue | Capture |
| --- | --- |
| Chemins et sol | [`native_ground_paths_north.png`](../references/generated/map_tests/runtime/native_ground_paths_north.png) |
| Carrefour | [`native_crossroad.png`](../references/generated/map_tests/runtime/native_crossroad.png) |
| Hutte complète | [`native_hut_whole_facade.png`](../references/generated/map_tests/runtime/native_hut_whole_facade.png) |
| Entrée de grotte complète | [`native_cave_whole_facade.png`](../references/generated/map_tests/runtime/native_cave_whole_facade.png) |
| Salle d'inspection | [`native_ground_transitions.png`](../references/generated/map_tests/runtime/native_ground_transitions.png) |
| Bande terre → transition → sable | [`native_joined_soil_whole_strip.png`](../references/generated/map_tests/runtime/native_joined_soil_whole_strip.png) |
| Feu, état 1 | [`fire_LCD_source_state_0.png`](../references/generated/map_tests/runtime/fire_LCD_source_state_0.png) |
| Feu, état 2 | [`fire_LCD_source_state_1.png`](../references/generated/map_tests/runtime/fire_LCD_source_state_1.png) |

Le contrôle d'entrée normale est également **PASS**, décrit dans [`normal_entry.json`](../references/generated/map_tests/normal_entry.json) et [`normal_build.json`](../references/generated/map_tests/normal_build.json), sur le SHA `67e1645c196e27a1671be05fd7c5fafa38850327f3e8ba2681f9f9f932b79670` : titre, Start, nouveau jeu puis scène initiale `PeonOpening`, avec son en-tête et ses 188 motifs statiques existants. Cette vérification couvre l'arrivée normale, pas un nouveau parcours complet des classes ou des combats. Aucun `.blk` de carte existante n'a été remplacé et les 182 sources du pack restent identiques au ZIP.

La liste exhaustive des chemins créés ou modifiés est [`changed_files.txt`](../references/generated/map_tests/changed_files.txt).

## Fichiers de cette étape

Le commit d'import `cad63b3` contient 59 fichiers créés ou modifiés, énumérables par `git show --format= --name-only cad63b3`. Le raccord de terrain est ajouté par `8bcfa57`, qui actualise uniquement la Cave et les manifestes/outils correspondants. `c7028d0` aligne les trois paquets LZ et l'importeur sur la compression native, sans modifier pixels, cartes ou palettes. Chaque complément est énumérable avec la même commande `git show --format= --name-only`.

Le premier commit comprend les modifications suivantes : `Makefile`, `constants/map_constants.asm`, les cinq tables `data/maps/{attributes,blocks,maps,scripts,spawn_points}.asm`, `engine/gfx/color.asm`, `engine/menus/intro_menu.asm`, `engine/tilesets/{map_palettes,tileset_anims}.asm`, `home.asm`, `home/map.asm` et `main.asm`. Les cinq tables nommées déclarent les trois nouvelles cartes et leur arrivée de test ; elles ne réécrivent pas les blocs des anciennes cartes.

Les nouveaux fichiers sont :

- `tools/import_peon_environment_v2.py`, `tools/build_peon_environment_v2.py`, `tools/validate_peon_environment_v2.py` et `tools/inventory_peon_environment_v2.py`.
- `home/peon_environment_v2.asm`, `engine/tilesets/peon_environment_v2.asm`, `data/tilesets/peon_environment_v2_headers.asm` et `gfx/peon_environment_v2.asm`.
- Les `.asm` et `.blk` de `maps/PeonEnvironmentTest`, `maps/PeonEnvironmentTestAnnex` et `maps/PeonEnvironmentTestCave`.
- `gfx/tilesets/peon_environment_v2/` : trois paquets PNG/2bpp/LZ, leurs métatuiles, collisions, attributs/priorités, palette de fond et frames du feu. Les 23 sorties graphiques sont énumérées avec leurs empreintes dans le manifeste.
- Ce rapport et `references/generated/map_tests/` : inventaire, manifestes, contrats, aperçus de conversion, résultats de compilation et preuves runtime.
- Le binaire et les fichiers de distribution dédiés dans `releases/environment-v2-durotar-test/`.

Les rapports de build, d'entrée normale et de reconstruction depuis les sources suivies, l'outil de validation runtime, ses captures/logs, la distribution et ce rapport complètent les commits d'import. Le champ d'état de l'inventaire renvoie aux preuves distinctes de conversion et de runtime. Les essais préliminaires de l'observateur restent séparés des preuves finales et ne sont pas cités comme validation du binaire livré. Les fichiers de diagnostic historiques déjà non suivis dans le workspace ne font pas partie de cette modification. Les sources du pack restent inchangées ; les sorties de l'ancien importeur et les versions publiées ne sont pas régénérées.

## Étape suivante recommandée

Après validation du test Durotar, reconstruire **The Den** avec ce pack : arrivée du joueur, feu central, Kento Brandenhoof dans son identité de Tauren, premier donneur de quête et marqueurs pilotés par l'état de la quête, gardes/péons et sortie lisible vers la vallée. Prévoir de la place pour les objets de camp existants, sans ajouter dès maintenant les biomes suivants. Cette étape doit conserver les scripts, les états de quête et la compatibilité des sauvegardes, puis faire l'objet de son propre build et de ses propres captures.

Avant d'appliquer ces terrains à The Den, harmoniser leurs palettes de conversion et leur placement pour réduire les jointures visibles, tout en gardant les sources canoniques intactes. La bande actuelle vérifie le chargement, l'adjacence et la traversée ; elle montre aussi la limite visuelle réelle des bords fournis.

La ROM de test déclare GBC, MBC3 avec RTC/RAM/batterie, 2 Mio de ROM et 32 Kio de RAM ; ses checksums sont vérifiés. Cette étape démontre le rendu et les interactions dans l'émulation native. Elle ne teste ni une console ModRetro physique, ni une cartouche DevDay, ni l'horloge RTC ou la persistance batterie de ce nouveau binaire.
