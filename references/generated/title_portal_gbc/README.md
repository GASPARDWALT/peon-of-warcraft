# Portail intégré — Peon of Warcraft v0.1.1

Cette capture provient de la ROM en émulateur, avec un agrandissement sans lissage.

![Écran titre réel dans la ROM](title_portal_in_rom_6x.png)

[Télécharger la version jouable ZIP](https://github.com/GASPARDWALT/peon-of-warcraft/raw/refs/heads/main/releases/v0.1.1/peon_of_warcraft_v0_1_1.zip)

Fichiers visuels :

- `title_portal_in_rom_160x144.png` : capture native réelle.
- `title_portal_in_rom_6x.png` : capture réelle agrandie ×6.
- `title_portal_native_160x144.png` : reconstruction du convertisseur.
- `title_portal_native_preview_6x.png` : reconstruction agrandie ×6.

Le portail reprend [le dessin approuvé](../title_portal_redrawn_v2.png).
Le convertisseur `tools/compile_peon_title.py` produit 360 tuiles, réparties
sur les deux banques VRAM, et huit palettes GBC de quatre couleurs chacune.
Les textes sont redessinés à la résolution native pour rester lisibles.
La capture est comparée à la reconstruction pixel par pixel en RGB555 dans
`tools/validate_peon_intro.py`. Les différences d'expansion RGB888 entre
Pillow et PyBoy sont tolérées uniquement dans les trois bits de poids faible.

La musique reste celle du prototype Crystal. Aucun test sur console physique
n'est effectué ici. Le parcours et le format de sauvegarde restent ceux de v0.1.

Pour régénérer les données : `python tools/compile_peon_title.py`
(Pillow et NumPy requis). Les données binaires sont versionnées pour permettre
la compilation normale avec RGBDS sans ces dépendances Python.
