# Sources des illustrations de sélection v0.2.18

Ces trois PNG sont les sorties originales d'imagegen, copiées sans modification.
La demande autorise une nouvelle illustration d'accueil et les portraits de
classe dans le style pixel art Warcraft des menus. Le péon de base et le paysage
ont été présentés à l'utilisateur ; son dernier schéma place le personnage à
gauche et l'interface à droite.

| Original | Dimensions | Direction artistique |
| --- | --- | --- |
| `base_generated_source.png` | 1122×1402 | Péon vert, crête noire, défenses, harnais, pantalon et bottes de cuir ; silhouette complète sur fond prune. |
| `durotar_background_generated_source.png` | 1322×1190 | Ciel orange et rouge, falaises, camp orque, tentes, piques et bannière ; paysage sans personnage ni texte. |
| `classes_generated_source.png` | 1881×836 | Même péon décliné en shaman, guerrier et démoniste, de gauche à droite ; figures complètes sur fond transparent. |

Les grandes références de héros consultées sont conservées sous
`references/generated/peon_sprite_redesign_v030/originals/` :
`peon_base_design_reference.png`, `peon_shaman_totemic_design_reference.png`,
`peon_warrior_design_reference.png`, `peon_warlock_design_reference.png`.
Les images de conversation servent de direction visuelle ; ces nouveaux PNG
ne sont pas présentés comme une extraction de leurs pixels.

`tools/import_peon_welcome_scenes_v0218.py` utilise ces copies versionnées.
Il conserve les contours complets, les débordements d'armes et la transparence
binaire avant composition. Il réduit les figures à 64×84 au maximum et le
paysage à 160×144 par échantillonnage au plus proche, sans lissage. La réduction
et les cinq palettes GBC impliquent une perte ; aucune grille native exacte
des grandes images n'est revendiquée. Les SHA256, recadrages, composantes alpha,
positions, palettes et paquets sont enregistrés dans
`gfx/welcome_scenes_v0218/manifest.json`.

Les portraits des maîtres ont une provenance distincte : anciens dessins
natifs 64×68, conservés intégralement, avec quatre lignes de marge ajoutées.
Voir `gfx/class_portraits_v0218/manifest.json`. Aucun de ces imports ne remplace
les personnages du monde ou de combat.
