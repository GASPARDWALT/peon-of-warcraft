# Peon of Warcraft v0.2.17

Ouvrir peon_of_warcraft_v0_2_17.gbc dans un émulateur Game Boy Color ou sur ModRetro.

Les personnages du monde sont redessinés directement en pixels natifs 24×24 : visages, proportions et équipements disposent de nouveaux pixels. Les 35 rôles nouvellement dessinés possèdent leurs quatre directions ; les héros et le diablotin disposent de trois emplacements de pose par direction. Ces dessins sont de nouvelles interprétations natives des références fournies, pas une extraction exacte ou un agrandissement des anciens PNG 16×16. Les cinq JSON de cellules sources sont dans assets/world/native_sources/, avec leur provenance et leurs SHA256 dans le manifest.

La grille de déplacement et de collision reste de 16 px. Les limites GBC restent 40 objets et 10 par ligne ; les corps proches sont prioritaires, et le HUD optionnel peut disparaître lorsque les corps complets occupent les objets disponibles.

Les imports de combat restent ceux de v0.2.16 : cadres natifs 48×48 de dos et 56×56 de face. Les conversions avec perte depuis les grandes références approuvées ne sont pas présentées comme des pixels natifs récupérés. Le caillou conserve STRIKE et ses attaques de terre ; MACE STRIKE conserve son coût nul de mana.

runtime/ contient uniquement les captures natives 160×144 explicitement validées de cette ROM et leurs agrandissements 4× sans lissage. assets/world/static_native_exports/ et assets/combat/static_imports/ contiennent les PNG transparents des paquets natifs ; assets/combat/source_native/ contient les sources échantillonnées avant quantification. Ces galeries statiques sont distinctes des captures du jeu. Aucun lissage n'est appliqué.

Les GIF de runtime/animations/, lorsqu'ils sont fournis, montrent cette même ROM en 160×144 ; leurs images composées sont opaques et leurs SHA256 sont vérifiés.

validation/ contient les preuves déclarées PASS. Les 495 PNG de personnages originaux et les quatre rasters approuvés, soit 499 sources conservées, ont été revérifiés par SHA256. Le matériel physique ModRetro n'a pas été testé.

ZIP déterministe : noms triés, date fixe 2026-10-15 et compression fixe. Chaque membre est relu avec son CRC et son SHA256 après écriture. SHA256SUMS.txt vérifie les fichiers du ZIP ; le SHA256 du ZIP lui-même est fourni dans le manifest externe et le fichier .zip.sha256, sans hash autoréférentiel.
