# Début orc niveau 1–6 : références et prochaines améliorations

Revue du 8 octobre 2026. Elle compare WoW Classic au prototype actuel, y
compris les deux diablotins devant la grotte, les marchands du Den et le HUD.
La ROM de référence testée avant cette revue est
`2006a6f6e0988b54ac1eea385d31a1ee8e9cfa24296a580bc530d938d5b65a2a`.
Ce document ne modifie ni la ROM ni les versions publiées.

## Ce qui a réellement été consulté

Les objectifs, niveaux et relations entre quêtes ont été vérifiés dans des
données publiques accessibles :

- [Questie v8.8.2, quêtes Classic](https://github.com/Questie/Questie/blob/v8.8.2/Database/Classic/classicQuestDB.lua).
- [CMaNGOS, Classic DB 1.12.1 z2815](https://github.com/cmangos/classic-db/blob/master/Full_DB/ClassicDB_1_12_1_z2815.sql.gz) : archive SQL retenue pour les objectifs, objets et sorts.
- [Interface 1.12.1, QuestFrame.lua](https://github.com/tekkub/wow-ui-source/blob/1.12.1/FrameXML/QuestFrame.lua) et [QuestLogFrame.lua](https://github.com/tekkub/wow-ui-source/blob/1.12.1/FrameXML/QuestLogFrame.lua) : noms des sons appelés par l'interface.
- [wowdev, liste historique des noms de fichiers](https://github.com/wowdev/wow-listfile/blob/master/listfile.txt) et [description de sa provenance](https://github.com/wowdev/wow-listfile/blob/master/README.md) : métadonnées de fichiers audio, sans leurs enregistrements.

Les pages Wowhead sont bloquées par le proxy de cet environnement. Aucun
navigateur de recherche n'est disponible ici : je n'ai donc pas visionné de
vidéo de gameplay Classic ni écouté les sons Blizzard pendant cette revue.
Les données permettent de vérifier la progression ; elles ne prouvent pas le
cadrage, le rythme ou le timbre exact d'une vidéo. Les captures et essais
natifs déjà réalisés concernent notre ROM, pas un client WoW Classic.

## Quêtes : Classic et état du prototype

« Minimum / niveau » distingue le niveau requis du niveau attribué à la
quête. Les nombres de créatures et récompenses du prototype sont des
adaptations pour une courte aventure GBC.

| Quête Classic | Minimum / niveau | Objectif Classic vérifié | État actuel de Peon of Warcraft |
| --- | --- | --- | --- |
| Cutting Teeth — 788 | 1 / 2 | Tuer dix Mottled Boars pour Gornek. | Fonctionnel, réduit à un sanglier au Den. Le sanglier neutre attend une interaction et une confirmation. |
| Sting of the Scorpid — 789 | 1 / 3 | Après Cutting Teeth, rapporter dix Scorpid Worker Tails. | Fonctionnel, réduit à un scorpid hostile et une queue. La carte est gagnée après cette deuxième quête : choix du projet. |
| Galgar's Cactus Apple Surprise — 4402 | 1 / 3 | Après Cutting Teeth, ramasser dix Cactus Apples pour Galgar. | Fonctionnel avec trois cactus persistants. Sac et cuivre remplacent la récompense Classic de dix Cactus Apple Surprise. |
| Lazy Peons — 5441 | 3 / 4 | Réveiller cinq péons avec le Foreman's Blackjack fourni par Thazz'ril. | Fonctionnel avec un péon endormi, interaction de réveil et retour au contremaître. Pas de Blackjack distinct ni de compteur de cinq péons. |
| Thazz'ril's Pick — 6394 | 3 / 4 | Après Lazy Peons, retrouver la pioche dans Burning Blade Coven. | Absent. Une courte collecte dans la grotte réutiliserait un lieu déjà jouable. |
| Sarkoth — 790 puis 804 | 1 / 5 | Rapport à Hana'zua avec la griffe, puis rapport de sa situation à Gornek. | Boss, preuve et retour à Hana'zua fonctionnels. Le deuxième rapport à Gornek est absent. Le boss actuel est niveau 4. |
| Vile Familiars — 792 | 2 / 4 | Tuer douze Vile Familiars pour Zureetha avant Burning Blade Medallion, pour notre parcours Shaman. | Ennemis présents, étape de quête absente. Deux diablotins extérieurs et deux familiars dans la grotte offrent quatre rencontres finies. |
| Burning Blade Medallion — 794 | 1 / 5 | Après Vile Familiars, rapporter le médaillon de Yarrog à Zureetha. | Fonctionnel et proposé directement. Yarrog, preuve, récompense et reprise après sac plein sont implémentés. |
| Report to Sen'jin Village — 805 | 1 / 5 | Après le médaillon, parler à Master Gadrin. | Sen'jin et Gadrin existent ; le transfert de quête n'existe pas encore. |
| Call of Earth — 1516 → 1517 → 1518 | 4 / 4 | Deux Felstalker Hooves pour Canaga, Earth Sapta à Spirit Rock, puis Rough Quartz à rapporter. Récompense : Earth Totem et Stoneskin Totem. | La chaîne et le rituel sont absents. Le kit contient déjà un Earth Totem ; le sort Strength of Earth enseigné au niveau 10 est une autre capacité. |
| Report to Orgnil — 823 | 4 / 7 | Parler à Orgnil Soulscar à Razor Hill. | Razor Hill et Orgnil existent, sans objectif de quête. Bonne transition vers le chapitre suivant ; niveau de quête 7. |

La variante Warlock de Vile Familiars utilise une autre entrée, 1499. Elle ne
doit pas remplacer l'entrée 792 utilisée pour la voie Shaman.

Le réveil après le BONK, Thrall, Kento, les trois maîtres personnalisés et le
nom « Peon + nom choisi » restent la direction du projet. Ce prologue n'est
pas présenté comme le démarrage canonique de Classic.

## Ce que le jeu possède déjà

La base permet de marcher entre les zones, entrer dans la grotte et les
bâtiments, acheter aux marchands, combattre, gagner de l'XP et sauvegarder.
Les auberges restaurent la vie et les charges ; le Hearthstone retrouve
l'auberge liée. Une défaite y ramène avec un point de vie, sans soin gratuit.
Les ennemis vaincus et cactus récoltés restent absents après chargement et
redémarrage d'une sauvegarde batterie.

Les portraits, les indicateurs jaune `!` / gris `?` / jaune `?`, la carte
découverte progressivement, les objectifs de carte, le personnage de combat,
les attaques de Shaman et les premiers équipements existent. Les sons
actuels de sanglier et d'éclair sont des compositions natives GBC originales.
Les offres de Duokna pour cinq eaux ou cinq pains à 25 copper ont été vérifiées
dans la base Classic ; les autres prix et effets ne sont pas tous canoniques.

Le combat reste au tour par tour, avec quatre attaques stockées et des charges
issues des PP. Il n'a pas encore la mana ni le combat temps réel de Classic.
L'Earth Totem utilisable dans le sac est indépendant des quatre attaques.

## Donner une fonction aux sept zones dessinées

Le [contrat de carte](VALLEY_SCREEN_LAYOUT.md) conserve les indications de
l'image reçue dans le chat. La Valley actuelle est encore une carte défilante,
pas sept écrans fixes.

| Zone indiquée | Rôle à préserver | Ambiance et lisibilité proposées |
| --- | --- | --- |
| 1 — Den | Camp de vendeurs aux points bleus ; camp d'entraînement au point violet. | Péon au travail, foyer, marchand identifiable, courte route battue entre repos, achats et entraînement. Garder les portes et les vendeurs accessibles. |
| 2 et 3 | Connexions exactes encore à préciser par le dessin des chemins. | Prévoir des respirations entre combats et collecte, sans inventer leur topologie ou déplacer les objectifs avant le dessin. |
| 4 | Hana'zua blessé et quête Sarkoth. | Pose blessée, peu de décor concurrent ; préparer visuellement la montée vers le boss. |
| 5 | Rencontre Sarkoth. | Cuvette rocheuse, silhouette rouge visible, accès assez large pour comprendre l'aggro et se retirer. |
| 6 | Entrée de grotte, diablotins rouges niveau 3, intérieur chargé séparément. | Transition sable → roche sombre → lumière de torche ; prévenir le danger avant le seuil. |
| 7 | Sortie fortifiée, murs clairs. | Gardes, palissade et direction de Sen'jin. Le rapport de Zureetha donne une raison de quitter la Valley. |

Les falaises rouges ferment les passages ; un sentier contrasté indique les
trajets praticables. Ne pas multiplier les rochers sur les cellules
d'interaction, de sortie ou de retrait d'un combat. Les contours jaunes des
créatures neutres et rouges des hostiles doivent rester lisibles devant ces
fonds.

Une migration vers sept cartes demande des IDs ajoutés après les cartes
actuelles, une traduction des anciennes positions et la reconstruction du
cache de terrain sauvegardé. Le dernier test d'ancienne sauvegarde a justement
détecté ce problème au nouvel emplacement des marchands du Den. Les drapeaux
de quête, vie, charges, objets et liaison d'auberge doivent être conservés.

## Prochaines additions, par priorité

1. **Terminer les chemins avant de disperser les PNJ.** Appliquer le dessin
   attendu, puis vérifier chaque trajet Den → Hana'zua → Sarkoth → grotte →
   sortie, avec une capture native. Ajouter quelques animations de travail,
   flammes et silhouettes de rochers plutôt qu'un grand nombre d'acteurs.
2. **Relier les objectifs déjà présents.** Ajouter Vile Familiars avant le
   médaillon, puis Sarkoth → rapport à Gornek. Afficher un petit journal avec
   objectif et compteur. Quatre familiars finis seraient une adaptation
   cohérente ; douze exigeraient de nouveaux acteurs ou un respawn explicite.
   Les ennemis tués avant acceptation doivent compter et les quêtes déjà
   terminées dans une ancienne sauvegarde ne doivent pas être bloquées.
3. **Ajouter Thazz'ril's Pick à la grotte.** Une pioche visible et une
   interaction permettent une mission sans bataille supplémentaire. Faire
   varier le dialogue du péon après le réveil : sommeil, BONK, travail, merci.
4. **Faire de Call of Earth le moment Shaman du niveau 4.** Canaga peut devenir
   un contact de Classic ou le rituel peut être présenté par Kento, en
   conservant le maître choisi. Ajouter Earth Sapta, apparition de l'esprit
   et attunement à Spirit Rock, puis Stoneskin. Ne pas donner un second Totem
   aux joueurs qui possèdent déjà `ITEM_94`, ni retirer celui des anciennes
   sauvegardes. Il n'y a actuellement qu'un Felstalker : deux sabots demandent
   un deuxième ennemi ou un objectif réduit clairement annoncé.
5. **Conclure la Valley avec Report to Sen'jin Village.** Gadrin reçoit le
   rapport après le médaillon, avec accueil troll et nouvelle destination.
   Report to Orgnil peut ensuite ouvrir le chapitre niveau 6–7. Une courte
   transition travaillée apporte davantage qu'un Orgrimmar complet précipité.
6. **Renforcer les signaux sonores et le rythme.** Une phrase de vent et de
   percussion, un feu discret, un BONK et un bref son de quête suffisent à
   identifier les camps. Jouer le son de récompense une seule fois à la
   transition d'état, pas à chaque conversation. Garder les pauses de lecture
   et les effets courts pour ne pas ralentir les combats.

Pour la première version de cette progression, conserver les soins et charges
actuels. Une vraie mana persistante doit être conçue avec le format de
sauvegarde avant d'ajouter une barre bleue qui laisserait croire qu'elle
existe déjà. Healing Wave au niveau 6 et Flame Shock au niveau 4 restent des
adaptations documentées ; Classic commence avec Healing Wave rank 1 et utilise
ses propres rangs et timings.

## Sons de référence identifiés

Ces liens ouvrent des **noms de fichiers vérifiés**, pas des téléchargements
audio. Le [catalogue Classic de Wowhead](https://www.wowhead.com/classic/sounds)
peut servir à chercher les noms dans un navigateur qui y a accès. Aucun ID
numérique de son ni lien direct vers un fichier audio n'a été vérifié ici.

| Usage | Référence historique vérifiée | Application proposée dans la ROM |
| --- | --- | --- |
| Quête terminée | [`sound/interface/iquestcomplete.wav`](https://github.com/wowdev/wow-listfile/blob/master/listfile.txt#L572024). L'interface 1.12.1 appelle aussi `igQuestListComplete` lors de la récompense ; l'association exacte entre l'alias et ce fichier n'est pas démontrée par la liste seule. | Petite cadence ascendante originale, une fois au rendu de quête. |
| Niveau gagné | [`sound/interface/levelup.wav`](https://github.com/wowdev/wow-listfile/blob/master/listfile.txt#L572055). | Fanfare brève et distincte de la quête, sans masquer les valeurs gagnées. |
| Sanglier | [`sound/creature/boar/mwildboarattack1.wav`](https://github.com/wowdev/wow-listfile/blob/master/listfile.txt#L444161), avec variante [`mwildboaraggro1.wav`](https://github.com/wowdev/wow-listfile/blob/master/listfile.txt#L444152). | Grondement bas et bruit sec à l'attaque. Pas de son d'aggro au simple passage près d'un sanglier jaune. |
| Éclair | [`sound/spells/lightningboltimpact.wav`](https://github.com/wowdev/wow-listfile/blob/master/listfile.txt#L583235). | Charge courte, craquement puis impact, synchronisés avec les images de Lightning Bolt. |
| Soin | [`sound/spells/heal_low_base.wav`](https://github.com/wowdev/wow-listfile/blob/master/listfile.txt#L582959). L'attribution précise à Healing Wave n'est pas vérifiée. | Montée douce, accord final léger et effet visuel vert ; écouter une référence avant de prétendre imiter Healing Wave. |

Pour la musique, la liste contient
[`sound/music/zonemusic/desert/daydesert01.mp3`](https://github.com/wowdev/wow-listfile/blob/master/listfile.txt#L579390)
et
[`sound/music/zonemusic/desert/nightdesert01.mp3`](https://github.com/wowdev/wow-listfile/blob/master/listfile.txt#L579396).
Ce sont des pistes de référence possibles pour un paysage désertique. Leur
affectation précise à la Valley/Durotar dans Classic n'est pas vérifiée par
cette liste. Les fichiers `sound/music/cataclysm/mus_durotar...` correspondent
à une autre extension et ne doivent pas être présentés comme la musique
Classic.

La GBC fournit deux canaux carrés, un canal d'onde et un canal de bruit. Les
imitations doivent donc être composées pour cette puce, avec un motif musical
simple et des priorités musique/effets. Les noms historiques ne fournissent
ni l'enregistrement ni une adaptation prête pour la console. Aucun audio
Blizzard n'a été téléchargé ou ajouté aux exports pendant cette revue.

## Références supplémentaires utiles

Le dessin des chemins reste la référence la plus utile pour verrouiller les
sept zones. Un court extrait de gameplay **WoW Classic** montrant le Den,
Hana'zua, Sarkoth, l'entrée de Burning Blade Coven et Spirit Rock permettrait
ensuite de comparer le rythme et les transitions. Pour l'audio, quelques
extraits courts de quête, niveau, sanglier et Lightning Bolt permettraient de
comparer les timbres à nos compositions natives, au lieu de travailler
uniquement à partir de noms de fichiers.

Les dialogues du jeu restent en anglais. Les nouvelles lignes doivent garder
la largeur native des boîtes, afficher le bon portrait et éviter de transformer
les textes Classic longs en blocs illisibles. La cible est une adaptation
reconnaissable du début de Classic, jouable et sauvegardable sur GBC.
