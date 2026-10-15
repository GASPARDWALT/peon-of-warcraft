# Accueil et sélection illustrés — v0.2.18

L'accueil reprend le paysage orange et rouge de Durotar : le personnage occupe
la partie gauche, les choix **Continuer** et **Créer un nouveau péon** la partie
droite. Le péon sans classe apparaît en l'absence de sauvegarde. Une sauvegarde
valide affiche ensuite le shaman, guerrier ou démoniste correspondant, avec son
nom. Le paysage visible reste identique entre les quatre illustrations.

Le choix de classe montre le portrait du maître sélectionné : Kento Brandenhoof,
MoCMoc Zogzog, ou Bismillah LesTenèbres. Haut/bas change de maître, A confirme,
B revient au dialogue de Thrall sans attribuer de classe. Le nom reste saisi
dans l'écran natif du jeu. Les personnages du monde et les combats restent
ceux de la v0.2.17.

## Sauvegarde et commandes

L'accueil lit uniquement le nom et la classe de la sauvegarde après vérification
de sa somme de contrôle, avec recours à la copie de secours native. Continuer
utilise toujours le chargement natif complet. EXIT revient au titre et ne crée
pas de sauvegarde : utiliser SAVE avant EXIT pour conserver la progression et
voir la nouvelle classe à l'accueil.

Il existe toujours un seul emplacement. Créer un nouveau péon en présence d'une
sauvegarde ouvre la confirmation native ; Non ou B conserve la sauvegarde et
revient à une sélection utilisable. Le menu relit ses métadonnées après cette
confirmation, car YesNoBox réutilise les champs de curseur du moteur.

## Sources et conversion

- Sources originales d'accueil : `assets/selection_v0218/`, trois PNG générés
  pour cette demande et conservés sans modification. Le fichier README de ce
  dossier précise leur provenance et la direction artistique.
- Portraits historiques des maîtres :
  `references/generated/peon_sprite_redesign_v030/selection/master_{kento,zogzog,xasthur}_portrait_64x68.png`.
  L'ancien nom de fichier xasthur fournit le portrait de Bismillah. Il s'agit
  d'art natif historiquement dessiné, pas de sprites fournis extraits.
- Paquets natifs : `gfx/welcome_scenes_v0218/`,
  `gfx/class_portraits_v0218/`, `gfx/selection_labels_v0218/`.
- Importeurs : `tools/import_peon_welcome_scenes_v0218.py`,
  `tools/import_peon_class_portraits_v0218.py`,
  `tools/build_peon_selection_labels_v0218.py`.

La conversion d'accueil réduit les grandes images sans lissage et ajuste leurs
couleurs aux palettes GBC. C'est une conversion avec perte, documentée par les
manifestes. Les maîtres gardent leurs positions de pixels et leur silhouette
alpha ; leurs couleurs subissent également une conversion de palette.
Les revues statiques sous `references/generated/selection_v0218/welcome/` et
`references/generated/class_selection_v0218/` sont séparées des captures réelles.

## Intégration native et limites

`engine/menus/peon_selection_screens_v0218.asm` charge des tuiles 2bpp, attributs
et palettes sur le fond GBC. Aucune illustration ne consomme les sprites OAM.
L'accueil réserve 312 tuiles pour ses scènes ; les quatre états utilisent
respectivement 238, 243, 239 et 243 tuiles uniques. Cinq palettes servent au
paysage et au personnage, trois au texte et aux cadres. Les portraits des
maîtres utilisent chacun 72 tuiles et cinq palettes.

Les scènes empruntent temporairement des tuiles de terrain dans les deux
banques VRAM. La sortie du choix de classe recharge les graphismes et attributs
du monde avec `ExitAllMenus`. Continuer et Nouvelle partie conservent les
chargements natifs de maps. Les prompts de l'accueil ne réaffichent pas le
portrait du dernier PNJ. Le nom est copié dans un tampon avant affichage pour
éviter que le cache de police grasse écrase le paysage.

L'écran reste limité à 160×144 et à quatre couleurs par tuile 8×8. Les libellés
français du panneau étroit utilisent une police bitmap compacte. La
confirmation native conserve son texte anglais. Aucun format de sauvegarde,
système de combat, sprite du monde, bâtiment, collision ou warp n'est modifié.
Les deux lignes ajoutées dans `maps/GrommashHold.asm` permettent seulement
d'annuler le choix du maître et de revenir au dialogue.

## Compilation et preuves

Exécuter `python3 tools/build_peon_v0218.py` avec RGBDS 1.0.4. Les paquets
versionnés restent figés ; aucun ancien générateur graphique n'est relancé.
Les tests dédiés utilisent PyBoy 2.7, de vraies commandes et des observations
en lecture seule, sans écriture dans la RAM ni injection de sauvegarde d'état.

Le rapport final est `references/generated/v0218/validation.json`. Il référence
les tests des quatre accueils, trois maîtres, retours B/A, confirmation Non/B,
SAVE/EXIT/Continue à froid, restauration des terrains et personnages du monde.
Les captures distribuées sous `releases/v0.2.18/runtime/` proviennent de cette
même ROM. Un export propre des sources doit reproduire ses octets et symboles.

La ROM est GBC, MBC3 avec horloge et batterie, 2 Mio avec 32 Kio de RAM. Les
sommes de contrôle sont vérifiées. Les essais physiques Chromatic/ModRetro
restent à effectuer.
