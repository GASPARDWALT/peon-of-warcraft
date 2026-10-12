# Peon of Warcraft v0.2.8 — Lecteur navigateur

Décompresse le ZIP, ouvre `peon_of_warcraft_v0_2_8_player.html` dans Chrome ou Edge, puis clique sur **Jouer**. La ROM, le moteur et le son sont intégrés dans ce seul fichier. Aucun téléchargement supplémentaire du lecteur n'est nécessaire.

Commandes : flèches pour marcher ; Z = A ; X = B ; Entrée = Start ; Majuscule = Select ; Espace = pause. Les boutons tactiles sont testés ; les manettes standard sont prises en charge, mais aucune manette physique n'a été testée.

Sauvegarde dans le jeu avec **Start → SAVE**. **Exporter .sav** fournit les 32 Kio de sauvegarde batterie. **Exporter la session** conserve l'instant exact, y compris l'horloge émulée. La session courante reste aussi dans les données locales du navigateur. Exporte-la pour changer d'appareil ou avant d'effacer ces données.

L'horloge avance pendant l'émulation et s'arrête lorsque le lecteur est fermé. Un .sav brut ne contient pas le RTC ; une session complète le conserve. Une sauvegarde de session de ce lecteur n'est pas un fichier à programmer sur une cartouche.

Le parcours chaman, le premier combat, SAVE, la reprise de session, l'import d'un .sav dans un nouveau navigateur, le son et les commandes tactiles ont été testés sous Chromium en HTTP. Le cloud bloque les URL file:// : l'ouverture locale par double-clic n'y a pas pu être vérifiée. Si ton navigateur refuse le fichier local, sers ce dossier en HTTP (`python -m http.server 8765` si Python est installé), puis ouvre `http://localhost:8765/peon_of_warcraft_v0_2_8_player.html` sur **ce même ordinateur**. Safari/iPhone et le navigateur intégré de Codex n'ont pas été testés.

Le dépôt contient aussi une branche `gh-pages` prête à héberger ce lecteur. Son activation est décrite dans `docs/BROWSER_PLAYER_V028.md` sur GitHub. Une URL GitHub raw télécharge le HTML ; elle ne l'exécute pas comme une page de jeu.

Moteur GBC binjgb sous licence MIT, ROM v0.2.8 inchangée. Ce lecteur indépendant ne simule pas le matériel FPGA Chromatic ni une cartouche DevDay et n'utilise pas le plugin ModRetro. Aucun matériel n'a été programmé.
