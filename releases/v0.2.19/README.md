# Peon of Warcraft v0.2.19

Ouvrir peon_of_warcraft_v0_2_19.gbc dans un émulateur Game Boy Color ou sur ModRetro.

Les trois maîtres ont des bustes illustrés de 80 × 88 pixels : Kento Tauren Shaman aux cornes corrigées, MoCMoc Zogzog inspiré de Garrosh (brun, chauve, armure et hache), Bismillah mort-vivant Démoniste. Ce sont des illustrations générées approuvées, converties avec perte par réduction au plus proche et palettes natives ; aucun lissage ni récupération d'une grille source n'est revendiqué. Les trois atlas de 2078 × 757 pixels restent intacts dans le dépôt ; chaque buste seul est importé entier.

L'accueil illustré, ses quatre états de classe et ses libellés compacts restent les assets approuvés de v0.2.18. assets/native_selection/ contient sept PNG natifs statiques (quatre scènes et trois portraits), trois aperçus opaques et tous leurs paquets 2bpp, cartes, attributs et palettes. Ces images sont des revues d'import, pas des captures du jeu. Les grands PNG sources sont revérifiés par SHA256 mais ne sont pas dupliqués dans le ZIP ; assets/source_provenance.json les documente.

Les personnages du monde restaurent les silhouettes natives historiques et les vues sources disponibles. Le passage de 16 à 24 pixels au plus proche rend ces dessins plus grands sans inventer du détail. Le maître Guerrier du monde suit l'aspect Garrosh brun/chauve ; le Guerrier du joueur reste distinct. Les conversions, retouches locales déclarées et cas sans source dédiée sont documentés dans les manifestes et JSON de provenance. assets/native_world/ contient les 39 familles et leurs 117 paquets, dont 30 familles et 90 paquets liés au moteur, plus leurs strips statiques de 96 × 72 pixels. Les palettes et facings du maître Garrosh sont fournis séparément. Les graphismes de combat et le gameplay existant sont préservés.

runtime/ contient uniquement les captures de 160 × 144 pixels de cette ROM figurant dans l'allowlist des tests, et leurs copies 4× sans lissage. validation/ conserve les rapports PASS liés au SHA256 exact de la ROM, du SYM et du MAP. Le matériel physique ModRetro n'a pas été testé.

ZIP déterministe : noms triés, date 2026-10-15 et compression fixes. Tous les membres sont relus avec CRC/SHA256 ; la ROM embarquée est identique au fichier fourni. SHA256SUMS.txt couvre les contenus hors manifest. Le manifest externe et .zip.sha256 fournissent le hash du ZIP sans hash autoréférentiel.
