# Peon of Warcraft v0.2.16

Ouvrir peon_of_warcraft_v0_2_16.gbc dans un émulateur Game Boy Color ou sur ModRetro.

Les personnages du monde conservent leurs corps 24×24 sur la grille de déplacement de 16 px. Les détails proviennent de leurs sources de personnage dans le monde, pas d'une réduction des illustrations de combat. Les silhouettes et équipements fournis restent les références. Les limites GBC restent 40 objets et 10 par ligne ; les personnages proches sont prioritaires.

Les trois héros de classe occupent mieux leurs cadres natifs de combat 48×48 de dos et 56×56 de face ; le Peon de base est également fourni. Les PNG natifs et leurs provenances sont dans assets/combat/. Les imports Warrior/Warlock depuis les grandes références approuvées restent des conversions avec perte ; ils ne sont pas présentés comme des pixels natifs récupérés.

Le Peon de base et le Shaman conservent trois poses dessinées. Warrior/Warlock conservent l'unique pose fournie, répétée dans les trois emplacements natifs.

Le petit caillou utilise STRIKE et des attaques de terre adaptées, avec leurs animations. Il ne possède pas de masse. MACE STRIKE est une attaque physique sans coût de mana.

runtime/ contient uniquement les captures natives 160×144 explicitement validées de cette ROM et leurs agrandissements 4× sans lissage. assets/world/static_imports/ et assets/combat/static_imports/ contiennent des PNG transparents décodés depuis les imports natifs. assets/combat/source_native/ contient les sources échantillonnées avant quantification. Ces galeries statiques sont distinctes des captures du jeu. Aucun lissage n'est appliqué.

Les GIF de runtime/animations/, lorsqu'ils sont fournis, montrent les animations de cette même ROM en 160×144 ; leurs images composées sont opaques et leurs SHA256 sont vérifiés.

validation/ contient les preuves déclarées PASS. Les 495 PNG de personnages originaux et les quatre rasters approuvés, soit 499 sources, ont été revérifiés par SHA256. Le matériel physique ModRetro n'a pas été testé.

ZIP déterministe : noms triés, date fixe 2026-10-15 et compression fixe. Chaque membre est relu avec son CRC et son SHA256 après écriture. SHA256SUMS.txt vérifie les fichiers du ZIP ; le SHA256 du ZIP lui-même est fourni dans le manifest externe et le fichier .zip.sha256, car un fichier ne peut pas contenir son propre hash sans circularité.
