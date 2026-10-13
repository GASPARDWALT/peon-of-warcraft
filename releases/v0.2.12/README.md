# Réparation graphique et quête de la pierre tellurique — v0.2.12

Cette version répare les imports des héros, les PNJ du monde et cinq intérieurs, puis ajoute la quête du shaman mystérieux. Les façades et les chemins extérieurs sont conservés.

## Quête jouable

1. Parler au shaman mystérieux en zone 2 (`ValleyOfTrials`, 12,11).
2. Aller en zone 3 (`PeonValleyCrossroads`, 3,5) et vaincre le premier élémentaire.
3. Rapporter la pierre tellurique au shaman pour obtenir la pierre de contrôle.
4. Retourner en zone 3 : un second élémentaire apparaît à 2,6.
5. Utiliser la pierre en combat pour le recruter. La probabilité native dépend de ses PV et de son état ; une tentative peut échouer. La pierre est réutilisable.
6. Choisir son surnom. Il apparaît dans l'équipe et dans le HUD du compagnon actif, puis reste enregistré après sauvegarde et reprise.

Le premier élémentaire ne peut pas être recruté à la place du second. Fuir ou perdre ne valide pas sa victoire. Un échec de capture ou une défaite laisse le second disponible. La limite d'équipe existante est conservée : deux membres au début. Les autres classes ne reçoivent pas cette quête. Les anciens compagnons et leurs noms sont préservés.

## Sources et imports

| Usage | Source réelle | Import natif |
| --- | --- | --- |
| Quatre héros | `references/generated/peon_sprite_redesign_v030/originals/peon_{base,shaman_totemic,warrior,warlock}_design_reference.png` | `gfx/approved_player_v0212/` |
| PNJ et créatures dans le monde | `references/characters/peon_world_character_sheets_split/` et ZIP original | `gfx/user_world_v0211/` |
| Intérieurs | `references/characters/razor_hill_inn_gbc/razor_hill_inn_interior_192x160.png` | `gfx/readable_interiors_v0212/` |
| Élémentaire manquant | Nouveau master conservé dans `references/generated/earth_elemental_v0212/originals/` | `gfx/earth_elemental_v0212/` |

Les héros utilisent les grandes planches validées disponibles dans le dépôt. L'atlas natif des quatre héros visible dans la conversation n'a pas été retrouvé dans les fichiers ou les branches GitHub inspectés. Cette importation est donc une **conversion avec perte**, par recadrage documenté, seuil alpha et réduction au plus proche voisin ; elle n'est pas une extraction exacte de cet atlas. Les PNG originaux sont intacts. Aucun contour, équipement ou membre n'est redessiné par le convertisseur.

Les sorties sont des PNG transparents de 16×16 pour le monde, 56×56 de face et 48×48 de dos. Les trois emplacements de pose natifs répètent volontairement le même dessin : les anciens corps inventés ne reviennent pas pendant les attaques. Les effets de sorts et leurs animations natives restent actifs. Les palettes GBC réduisent les couleurs ; les captures matérielles simulées distinguent ce rendu des PNG avant conversion.

Pour les PNJ, les 65 vues originales intactes sont prioritaires. Les 39 vues contenant des libellés, des morceaux de corps ou des équipements isolés utilisent un PNG canonique entier d'un rôle proche, avec le choix et le hash consignés. Ce sont des substitutions explicites, pas des reconstructions exactes des vues endommagées. Les maîtres et les aubergistes sont reliés à ces imports, en plus des PNJ déjà reliés. Aucun PNG procédural de réparation n'est utilisé dans cet import du monde.

L'élémentaire n'existait pas dans le pack de personnages. Son nouveau dessin a été créé avec Image Generation à partir du style des références fournies, conservé séparément, puis converti au format natif. Il est identifié comme nouvel asset généré, pas comme PNG fourni par l'utilisateur.

## Intérieurs

`GrommashHold`, `PeonOrcHut`, `PeonOrcInn`, `PeonTrollHut` et `PeonTrollInn` utilisent des meubles entiers prélevés dans la source : lit, comptoir, table, foyer et porte. Une zone centrale reste libre. Il s'agit d'un aménagement partiel cohérent, pas de la copie intégrale de l'image de pièce.

Chaque pièce utilise 175 des 192 motifs disponibles. L'image complète exige plus de 450 motifs dans ce pipeline et ne tient pas avec les réservations actuelles de police et de sprites. Les sorties des petites pièces sont alignées avec leur porte à 5,9 ; les points de retour de la pierre de foyer et les anciennes positions de sauvegarde restent accessibles. Une migration limitée à 61 anciennes cases devenues bloquées évite de reprendre une sauvegarde dans un meuble. Le foyer est statique afin que l'ancienne animation ne remplace plus des tuiles de mobilier.

## Build et vérification

Build courant :

```sh
python3 tools/build_peon_art_repair_v0212.py
```

Ce builder refuse de relancer les 207 cibles historiques de génération d'art. Les imports sont explicites et séparés :

```sh
python3 tools/import_peon_approved_players_v0212.py
python3 tools/build_peon_user_world_v0211.py --npc-only
python3 tools/import_peon_readable_interiors_v0212.py --apply
python3 tools/import_peon_earth_elemental_v0212.py
```

ROM : `releases/v0.2.12/peon_of_warcraft_v0_2_12.gbc`.
SHA-256 : `d4adeb85438fb3362b80c7300397d47b67b5aa40350339f199fa5100d074c35e`.
En-tête et sommes de contrôle vérifiés : 2 Mio, CGB, MBC3 avec RTC, batterie et 32 Kio de RAM. Aucun test sur une cartouche physique ModRetro n'a été effectué.

Les tests PyBoy utilisent les commandes ordinaires du jeu et des lectures de VRAM/OAM ; aucun état d'émulateur, écriture de RAM ou appel forcé de fonction n'est utilisé. Les rapports finaux et leurs captures portent le hash exact de la ROM. Ils couvrent les trois classes, quatre directions, portraits, dos en combat, sorts et attaques, annulation de FIGHT/BAG, menus d'équipe, les cinq intérieurs, les portes, sauvegarde et reprise. La quête vérifie aussi les refus des autres classes, la fuite, des échecs de capture, une défaite, le recrutement, le surnom visible et sa persistance. Le cas de sac rempli est revu dans le code, sans remplir artificiellement l'inventaire en émulation.

- `references/generated/art_repair_v0212/runtime/validation.json`
- `references/generated/art_repair_v0212/source_fidelity_validation.json`
- `references/generated/art_repair_v0212/fresh_build_validation.json` : compilation depuis les fichiers indexés dans Git, ROM identique octet pour octet.
- `references/generated/earth_stone_quest_v0212/final_d4adeb85/runtime/validation.json`
- `references/generated/art_repair_v0212/changed_files.txt`

Ces vérifications prouvent les parcours observés et les imports décrits. Elles ne certifient pas l'absence de tout bug dans le jeu entier.
