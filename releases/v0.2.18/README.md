# Peon of Warcraft v0.2.18

Ouvrir peon_of_warcraft_v0_2_18.gbc dans un émulateur Game Boy Color ou sur ModRetro.

Cette version ajoute un accueil illustré dans Durotar, quatre images de classe et les portraits des trois maîtres. Les personnages du monde et de combat restent ceux de v0.2.17.

runtime/ contient uniquement les captures 160×144 de cette ROM déclarées par les tests, avec leurs copies 4× sans lissage. assets/native_selection/ contient sept PNG natifs statiques (quatre scènes et trois portraits), les trois aperçus opaques hardware_bg.png, les tuiles 2bpp, cartes, attributs, palettes et manifests. Ces images statiques ne sont pas des captures du jeu. Les libellés utilisent 24 tuiles de texte compact.

Les trois grandes illustrations et les trois portraits originaux 64×68 restent intacts dans le dépôt et sont revérifiés par SHA256. Leurs chemins et leur provenance figurent dans assets/source_provenance.json ; les grands PNG ne sont pas dupliqués dans le ZIP. Les scènes sont des conversions natives avec perte de couleurs et réduction sans lissage ; les portraits conservent leur géométrie avec quatre lignes transparentes de marge inférieure. Aucune récupération de grille native des grandes illustrations n'est revendiquée.

validation/ contient les rapports PASS portant sur le SHA256 exact de la ROM. Le matériel physique ModRetro n'a pas été testé.

ZIP déterministe : noms triés, date fixe 2026-10-15, compression fixe ; tous les membres sont relus avec CRC et SHA256, et la ROM embarquée est identique au fichier fourni. SHA256SUMS.txt couvre les contenus hors manifest ; le manifest externe et le fichier .zip.sha256 fournissent le SHA256 du ZIP sans hash autoréférentiel.
