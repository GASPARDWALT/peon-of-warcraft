# Import des sprites et décors utilisateur — v0.2.11

Cette version importe les PNG déposés dans le dépôt dans les chemins de rendu natifs de la ROM : déplacement, fiche du personnage, combat, alliés et cartes. Les planches de référence et les aperçus d'un convertisseur ne constituent pas des captures du jeu. Les vérifications en émulateur doivent porter sur le SHA-256 exact de la ROM distribuée.

## Sources conservées

Les trois archives et chaque fichier extrait restent identiques aux fichiers fournis. Les corrections et conversions sont enregistrées séparément.

| Archive dans `references/characters/` | SHA-256 |
| --- | --- |
| `peon_world_character_sheets_split.zip` | `0aac67d4de4e49e0f13882be203dc4acda51fafe542570f97d1b1ba5d794e27a` |
| `durotar_asset_pack_v1.zip` | `2d9bbe4609ffc83c99955ec1065efbf5885bf902e417e5d99c6b31ad77edc7bc` |
| `razor_hill_inn_gbc.zip` | `27276d86f2d71c77aca899ba73947d6ec12b6ae3042a3d6c747d35779bbbffcb` |

La première archive contient 26 rôles et 156 PNG natifs, soit quatre directions dans le monde, une vue de face et une vue de dos en combat par rôle. Certains fichiers comportent des découpes endommagées, du texte ou une vue mal étiquetée. Le diagnostic initial est conservé dans `references/generated/user_sprite_import/source_audit.json`.

L'autorisation de compléter les éléments manquants, donnée le 13 octobre 2026, s'applique aux fichiers dérivés. Elle ne remplace pas les PNG originaux valides. Les manifestes enregistrent les parents, leurs empreintes, les coordonnées de composants réutilisés et les interventions effectuées.

## Personnages et poses

| Usage | Dimensions du PNG source |
| --- | --- |
| Monde : face, dos, gauche, droite | 16 × 16 px |
| Combat : face | 56 × 56 px |
| Combat : dos | 48 × 48 px |

`references/generated/user_player_v0211/` contient les quatre variantes du péon, créées à partir de l'anatomie de l'orc fourni : péon de base, chaman, guerrier et démoniste. La crête noire reste commune. Le chaman reçoit masse, bouclier et totem ; le guerrier une épaulière en mailles et une hache ; le démoniste une robe mauve déchirée, un bâton et des yeux modifiés. Les fichiers comprennent les quatre directions, des pas distincts, des poses de combat et une pose de sommeil pour l'introduction. Les vues de dos représentent réellement le dos. Les lignes de pixels modifiables sont aussi conservées en `.rows.json`.

`references/generated/user_npc_completion_v0211/` contient les réparations nécessaires des découpes fournies et le véritable dos du diablotin. Les autres poses valides continuent à provenir directement de l'archive originale. L'orc `shaman_master` fourni n'est pas substitué à Kento Brandenhoof, qui est un Tauren dans le jeu.

La table de monde comporte 19 liaisons de sprites. L'identifiant du péon ouvrier est ajouté à la fin de la table ; les identifiants existants ne sont pas réordonnés. Les directions gauche et droite des PNJ importés sont indépendantes. Lorsque seuls les quatre PNG statiques ont été fournis, la marche des PNJ utilise ces poses : elle n'est pas présentée comme trois nouveaux dessins animés. Les quatre variantes du joueur disposent de vrais pas distincts.

Le convertisseur de combat produit les paquets des joueurs, les portraits, les ennemis et les alliés. Les ennemis utilisent leur pose canonique fournie ; les références de frames natives pointent sur cette pose et conservent les effets de sorts et d'impact. Cette version ne prétend pas ajouter trois dessins de mouvement à chaque ennemi. Les espèces dont aucun nouveau dessin correspondant n'a été fourni conservent leurs graphismes existants.

Les manifestes qui font foi sont :

- `references/generated/user_player_v0211/manifest.json` : PNG complétés du joueur et provenance.
- `references/generated/user_npc_completion_v0211/manifest.json` : découpes réparées et provenance.
- `gfx/user_world_v0211/manifest.json` : sources exactes, palettes et liaisons du monde.
- `references/generated/user_battle_v0211/manifest.json` : paquets de combat, vues et palettes.

## Conversion Game Boy Color

Les PNG sources conservent leur géométrie et leur transparence binaire. Les convertisseurs ne redimensionnent pas les personnages. La réduction des couleurs RGB555 est explicite et séparée : l'image affichée sur console n'est pas annoncée comme identique aux couleurs RGBA du PNG.

Un objet GBC utilise trois couleurs visibles et une transparence par palette. Les sprites de monde sont regroupés par matériaux et familles de personnages, en conservant les palettes réservées à l'interface et aux marqueurs de quête. Les grandes images de combat utilisent des familles de palettes par tuile de 8 × 8 ; les emplacements des PV, de l'expérience, du texte, du dragon de rang et du diablotin ou totem restent protégés. Le portrait de la fiche utilise quatre familles de couleurs. Le menu natif de statistiques dispose également d'une conversion dédiée.

Les aperçus nommés `hardware_rgba` ou `4x` dans `references/generated/user_battle_v0211/` montrent la sortie du convertisseur. Ils doivent être distingués des captures PPU de la ROM dans `references/generated/user_art_runtime_v0211/`.

Le choix des attaques conserve le dos complet du joueur. Le panneau de ressource qui recouvrait son corps est remplacé par deux lignes de six cellules au-dessus du sprite, colonnes 2 à 7 et lignes 4 et 5. Une observation navigateur du build final confirme `MP: 72` puis `C:15MP` lorsque Lightning Bolt est sélectionné par le bouton Bas. Le coût et les valeurs de ressource ne sont pas modifiés par cette mise en page. Les octets réellement lus et les captures sont conservés dans `references/generated/browser_player_v0211/compact_resource/`.

## Décors et bâtiments

Le pack `durotar_asset_pack_v1` fournit le sol, les cactus, rochers, palmiers, feux, bannières et palissades utilisés par l'importeur. Le manifeste indique aussi les éléments conservés mais non liés à une carte : leur présence dans l'archive ne signifie pas qu'ils sont tous affichés dans le jeu.

Les neuf extérieurs des bâtiments accessibles de The Den, Sen'jin Village et Razor Hill utilisent le modèle complet `razor_hill_inn_exterior_96x80.png`, ainsi que les deux postes fermés de la porte d'Orgrimmar. Les anciens postes de Razor Hill sont remplacés sous les nouvelles façades. Le modèle n'est pas réduit à l'ancien bloc de bâtiment de 32 × 32. L'entrée des bâtiments accessibles est centrée sur les coordonnées de porte existantes ; les postes fermés restent sans entrée. Les quatre salles partagées (`PeonOrcHut`, `PeonOrcInn`, `PeonTrollHut`, `PeonTrollInn`) et la salle de cinématique `GrommashHold` réutilisent les éléments du même intérieur de Razor Hill. Le manifeste distingue ces onze façades et cinq salles des autres éléments du décor.

L'intérieur original de 192 × 160 contient environ 455 motifs distincts après conversion. Le moteur existant dispose de 192 motifs de décor par carte. L'intérieur natif est donc une composition modulaire à l'échelle 1, avec murs, lits, table, foyer et porte recopiés depuis leurs coordonnées sources, puis réutilisés. Le PNG complet original reste conservé ; la salle du jeu n'est pas présentée comme l'import littéral de ses 30 blocs. Les coordonnées des modules apparaissent dans `references/generated/user_environment_v0211/manifest.json`.

Chaque carte charge son propre paquet de motifs et de métatuiles. Les 18 cartes concernées gardent leurs identifiants et leurs scripts. La limite de 192 motifs, la limite de 128 métatuiles et la banque des attributs sont contrôlées. Le feu fourni utilise trois frames complètes de 16 × 16, soit quatre motifs par frame. Les palmiers de 32 × 48 conservent leur hauteur.

Les nouvelles façades ajoutent 17 cellules de mur sur leur partie basse : une à The Den, sept à Sen'jin et neuf à Razor Hill. Les portes, les cases de retour et les approches des PNJ restent accessibles. L'importeur vérifie les chemins vers les portes et les PNJ sur les 18 cartes. Les autres collisions restent inchangées. Un masque de priorité de 32 octets par carte permet au joueur de passer derrière les débords supérieurs des toits ; il est appliqué au chargement et au défilement, sans donner cette priorité aux tuiles du texte ou du feu.

La table `data/maps/peon_user_environment_relocations_v0211.asm` fournit 17 positions de reprise sûres pour une ancienne sauvegarde située sur un nouveau mur. Le hook de géographie l'applique après la migration précédente, sans ajouter de champ ni changer le format de sauvegarde. Les fichiers `_priority.bin` et cette table sont produits par l'importeur de décor. La comparaison statique et la recherche de chemins ne remplacent pas l'observation des façades, des passages et des neuf portes en émulateur.

## Reproduire le build sans écraser les dessins

Prérequis : Python 3 avec Pillow et NumPy, GNU make, compilateur C pour les outils du dépôt et RGBDS 1.0.4. Le script réutilise les PNG complétés validés ; il ne lance pas les auteurs de dessins.

```sh
tools/rebuild_peon_v0211.sh --check
tools/rebuild_peon_v0211.sh
```

`PEON_RGBDS` permet de choisir le dossier RGBDS ; `PEON_PYTHON` et `PEON_JOBS` permettent de choisir Python et le parallélisme. Dans cet environnement, RGBDS se trouve dans `/workspace/toolchains/rgbds-1.0.4/`.

Le script vérifie les empreintes des trois ZIP, de tous les fichiers extraits, des PNG dérivés et du baseline de décor conservé. Il exécute uniquement les importeurs dédiés, dans cet ordre :

1. `tools/build_peon_user_world_v0211.py` : familles de palettes, PNJ et péon endormi.
2. `tools/build_peon_user_battle_v0211.py` : classes, monde du joueur, portraits, ennemis et alliés.
3. `tools/import_peon_user_environment_v0211.py --apply` : paquets de carte, blocs et collisions dérivés depuis le baseline, masques de priorité des toits et table de reprise sûre des sauvegardes.
4. Compilation native `make pokecrystal.gbc`, avec les sorties des anciens générateurs gelées et un refus de tout générateur Python ou Node inattendu dans le plan make.

Ne pas lancer `tools/rebuild_peon_v028.sh` et ne pas utiliser `make clean` comme étape de cette chaîne : ils peuvent supprimer ou recréer les anciens graphismes. Un baseline ou une sortie ancienne manquants produisent une erreur explicite. Le script ne publie rien et ne programme aucune cartouche.

Les sorties binaires canoniques des anciens générateurs sont incluses dans le dépôt pour que cette protection fonctionne aussi depuis une copie neuve : polices, palettes, sprites, effets, icônes et tables graphiques. Elles restent inchangées ; aucune sauvegarde RAM ni donnée personnelle n'est ajoutée comme dépendance de compilation. La reconstruction dédiée réutilise ces entrées gelées plutôt que de lancer les anciens auteurs de dessins.

Les outils `author_peon_user_player_v0211.cjs` et `author_peon_user_npcs_v0211.cjs` restent disponibles pour reproduire les **compléments dérivés**, avec Node.js et `pngjs`. Ils ne sont pas une étape automatique du rebuild et ne doivent pas écraser de nouvelles corrections manuelles approuvées.

## Vérification avant distribution

`tools/validate_peon_user_art_v0211.py` reçoit une ROM figée, son fichier `.sym` et son SHA-256 attendu. Les parcours utilisent les boutons normaux et des observations en lecture seule. Les fichiers de preuve doivent indiquer la classe, le SHA-256 et les captures exactes.

Les contrôles pertinents portent sur les trois classes, les directions et phases du joueur, les poses des PNJ, les palettes et la fiche du personnage, le premier combat et les alliés, les entrées et sorties de bâtiments, les limites OAM, la sauvegarde native, la reprise à froid et `EXIT → écran titre → START → CONTINUE`. Un build ou une validation de PNG ne remplace pas ces observations. Les résultats provisoires ne doivent pas être inclus comme preuve finale d'une ROM modifiée après leur exécution.

Pour le lecteur navigateur, `tools/validate_peon_browser_player.py` choisit la table de collisions locale de The Den lorsque le fichier `.sym` contient `PeonSelectUserEnvironmentV0211`. Les métatuiles des grandes façades dépassent les 67 entrées de l'ancienne table partagée. Les validations des ROM précédentes conservent cette ancienne table. Ce choix de table sert uniquement au parcours automatique en lecture seule ; il ne modifie ni la ROM ni la RAM du jeu.

Le build conserve le format ROM GBC de 2 Mio, MBC3 avec RTC, RAM et batterie, et 32 Kio de RAM de sauvegarde. L'émulation ne vérifie pas le profil matériel d'une cartouche DevDay ni son firmware ; aucun test sur console ou cartouche physique ne doit être annoncé sans observation réelle.
