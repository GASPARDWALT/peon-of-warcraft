# Peon of Warcraft — v0.2.14

- Shaman : tête plus petite par rapport au corps, taille proche des autres héros.
- Vues 56×56 de face et 48×48 de dos, trois poses chacune, sans lissage.
- Sols moins chargés : grands espaces calmes et quelques plaques de texture.
- Décors, bâtiments, grotte, piliers, chemins, collisions et événements conservés.
- Mana, rage et types d'attaque en couleur toujours actifs.

ROM : `peon_of_warcraft_v0_2_14.gbc` (2 Mio).
Le dossier `transparent_shaman/` contient les six PNG dérivés réutilisables.
`captures/` contient uniquement les images de l'émulateur à 160×144.
Les originaux fournis sont conservés dans le dépôt.

Build sûr : `python3 tools/build_peon_v0214.py`.
La compilation propre donne exactement la ROM testée. Les parcours utilisent
les boutons ordinaires, sans modification de RAM ou sauvegardes de l'utilisateur.
Les rapports précisent les scènes observées. Aucun test physique ModRetro
n'a été effectué.

Détails : `docs/V0214_SHAMAN_AND_QUIETER_GROUND.md` dans le dépôt.
