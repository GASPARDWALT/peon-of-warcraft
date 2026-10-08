# Native enemy rank emblems

Original dragon concepts are compiled into 16×24 pixel, six-tile CGB emblems. The native transparent PNGs are the actual ROM pixels, limited to three opaque colours and transparency. On the Game Boy background layer, transparent pixels use the white battle background. The full concept is an art reference, not a promise of higher ROM resolution.

Gold for Yarrog and silver for Sarkoth are explicit prototype boss/rank adaptations. No unverified claim about their original WoW Classic rank is implied. Ordinary enemies have no dragon. The emblem is placed below the enemy name/HP panel, left of the 56×56 animated front portrait, and above the player HUD. It uses bank-1 signed BG tiles $80..$85 at $8800..$885f and palette 5. Both idle and animated enemy-front copies, player backpic, bank-0 font and battle OAM are untouched. Normal overworld sprite-cache loading restores this area when combat ends.
