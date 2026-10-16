# Peon of Warcraft v0.2.20

Ouvrir peon_of_warcraft_v0_2_20.gbc dans un émulateur Game Boy Color.

Personnages du monde redessinés sur une grille native 32×32 : nouvelles silhouettes, visages, équipements et deux clés de marche par direction. Les nouvelles illustrations sont réduites directement à 32 px puis converties avec perte aux palettes GBC ; les pas sont édités séparément. Ce ne sont pas des sprites16px agrandis. Les créatures approuvées, dont le sanglier et le Kolkar, conservent leurs paquets natifs24px.

Sol ocre uniforme sur 13 cartes, chemins compris, avec les pixels opaques des décors et les collisions préservés. Le moteur utilise le mode double vitesse du CPU CGB et place son travail dans le budget natif de deux images. Les mesures exactes de cadence, son et déplacements sont dans validation/.

assets/active_world/ contient les graphismes du monde liés à cette version. assets/native_world/ conserve les références historiques v19 et la provenance Garrosh ; ces strips statiques ne sont pas des captures ROM. Les illustrations et menus approuvés restent inchangés. runtime/ ne contient que des captures LCD160×144 du SHA exact livré et leurs agrandissements4× sans lissage. Le matériel physique n’a pas été testé.

La grille de déplacement reste16px. Les corps sont admis entiers dans les limites 40objets OAM/10par ligne ; des acteurs éloignés peuvent être masqués dans les scènes chargées. Les sauvegardes, combats et règles de jeu restent compatibles.
