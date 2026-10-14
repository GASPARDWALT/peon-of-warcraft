# Peon of Warcraft — v0.2.13

ROM : `peon_of_warcraft_v0_2_13.gbc` (2 Mio, Game Boy Color).

- Mana réelle en haut de l'écran et en combat ; rage rouge pour le guerrier.
- Type d'attaque en couleur : Nature, Ombre, Feu et types physiques.
- Anciens modèles complets du péon/shaman, du sanglier et du diablotin restaurés.
- Décors extérieurs issus des PNG fournis ; bâtiments approuvés conservés.
- Lightning Bolt horizontal, vérifié dans les deux sens.
- ROSTER : un combattant actif, attaques et PP natifs des compagnons.
- Petit cailloux vibrant → Veine Tellurique au niveau 8 → Roche Elementaire au niveau 12.
- Pierre de contrôle réutilisable : lancer, rebonds, suspense et capture native.
- Trois maîtres agrandis dans le bâtiment ouest de The Den, dont Bismillah LesTenèbres.
- Péon endormi déplacé en zone 2 ; récompense unique conservée.
- Piliers aux passages et deux voies fonctionnelles ; grotte issue du pack fourni.
- Correction des noms de victoire, du retour du suivi de quête et des sprites après Continue.

## Vérification

Compilation avec RGBDS 1.0.4, sans relancer les anciens générateurs d'art.
Les tests sur la ROM finale couvrent les trois classes, les jauges, les couleurs,
les noms et les sauvegardes relancées à froid. D'autres parcours complets ont été
vérifiés sur les candidats antérieurs ; leurs hashes et leur portée sont précisés
sans les présenter comme des tests du fichier final.

Les captures `captures/` proviennent de l'émulateur, à la résolution native 160×144.
Leur suffixe indique leur provenance. Aucun test physique ModRetro n'a été effectué.

Sources, limites et imports : `docs/V0213_NATIVE_ART_AND_ROSTER.md` dans le dépôt.
Rapport : `references/generated/v0213/validation.json`.
