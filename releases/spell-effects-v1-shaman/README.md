# Shaman spell-effects v1

- `peon_spell_effects_v1_shaman.gbc`: jeu normal, quatre effets Shaman importés.
- `peon_spell_effects_v1_shaman_test.gbc`: carte de test et huit scénarios natifs.

Dans la ROM de test : Start, nouveau personnage, puis un pas à gauche depuis le
point de départ et A pour parler au guide. Les quatre premiers scénarios sont
les effets joueur ; les quatre suivants vérifient les directions ennemi.
Lightning/Rockbiter/Earth Shock passent par Fight ; Earth Totem passe par Bags.
Le scénario ennemi Totem est un aperçu visuel, sans mécanique de sac ennemi.

Les PNG sources restent identiques. Le rendu conserve leurs dimensions et leur
transparence ; leurs couleurs sont adaptées aux palettes natives GBC.
Aucune modification des personnages, sauvegardes ou cartes finales.

Les fichiers SYM/MAP sont inclus pour les tests et le débogage. Le rapport
complet est `docs/SPELL_EFFECTS_V1_SHAMAN.md` et les captures de combats sont
dans `references/generated/spell_tests/runtime/`. Le manifest contient les
empreintes des deux ROM. Les tests n'ont pas programmé de cartouche physique.

Résultat : compilation OK, huit scénarios natifs réussis et sprites des trois
classes vérifiés dans la ROM normale. Reconstruction depuis le dépôt identique.
