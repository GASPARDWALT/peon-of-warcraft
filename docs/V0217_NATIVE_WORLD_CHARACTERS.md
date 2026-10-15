# Personnages du monde natifs — v0.2.17

La demande porte sur tous les personnages du monde : leur donner de vrais
pixels pour les visages, les tenues et les accessoires. Agrandir les anciens
16×16 conservait leurs silhouettes étroites et leurs détails déjà perdus.

Cette version utilise des dessins créés directement sur des grilles 24×24.
Les sources sont les cinq JSON de `assets/world_redraw_v0217/`, avec quatre
vues par rôle. Les quatre héros et le diablotin possèdent aussi deux pas
distincts par direction. Les autres familles conservent quatre poses fixes.
Les références fournies guident l'identité des personnages ; ces nouveaux
dessins ne sont pas présentés comme des extractions exactes de leurs pixels.
Les 495 PNG de personnages et les quatre anciennes grandes références restent
intacts, avec leurs hashes dans le rapport d'import.

Les 35 rôles dessinés couvrent les 30 familles réellement liées au moteur,
ainsi que cinq variantes de référence. Les quatre anciens paquets non liés
(maître shaman de référence et trois stades du caillou) sont conservés
explicitement. Les trois grands maîtres du pavillon utilisent toujours leurs
sprites natifs approuvés séparés. Les petits portraits de menu gardent leur
format 16×16 ; les sprites de combat restent ceux de la v0.2.16.

## Pipeline

`python3 tools/import_peon_world_redraw_v0217.py` valide les lignes 24×24,
encode sans redimensionnement les indices transparents/1/2/3 en tuiles 2bpp,
et écrit 12 images de neuf tuiles par rôle. Il génère les masques de tuiles
opaques et neuf attributs de palette par image. Les comparaisons et exports
statiques sont dans `references/generated/world_redraw_v0217/` ; ils sont
distincts des captures d'émulateur.

`python3 tools/build_peon_v0217.py` compile les paquets versionnés en gelant
les anciens générateurs. Le moteur conserve la grille de déplacement et les
collisions de 16 pixels, les 117 tuiles de streaming en banque VRAM1, les
40 objets OAM et la limite de dix objets par ligne. Les corps entiers du
joueur et des interlocuteurs proches sont prioritaires dans les scènes denses.

Les visages orcs emploient OBJ6 (ivoire, vert, contour). Les trolls, métaux et
la jauge de mana réutilisent l'ancien bleu d'OBJ6 sur OBJ5. Les marqueurs de
quête réappliquent ces couleurs après leurs rafraîchissements. Les palettes
de combat sont indépendantes. Le pavillon des trois maîtres conserve ses
propres palettes ; son HUD optionnel est omis pour éviter un conflit de
couleurs avec les maîtres. Les poussières natives peuvent prendre la nouvelle
teinte pâle d'OBJ5 ; leur comportement ne change pas.

## Vérifications et limites

Le build initial v0.2.16 est reproductible :
`3c25adf84a9278c826f3f873560991ee6483d6bc02641782afb1e9f9810aa2dc`.
Les rapports de la ROM finale, captures LCD 160×144, vérifications des paquets,
achats, sauvegardes et palettes sont dans `references/generated/v0217/` et
les sous-dossiers de tests explicitement nommés dans `validation.json`.
Une galerie d'art seule ne prouve pas le fonctionnement dans la ROM.

La limite reste trois couleurs opaques par tuile OBJ de 8×8. Une scène très
chargée peut masquer un personnage lointain et le HUD entier pour garder les
corps proches complets. Aucun test sur un appareil Chromatic physique n'a
été effectué. Les sauvegardes, maps, bâtiments, combats, Lightning Bolt et
attaques de terre ne font pas l'objet d'une refonte dans cette version.
