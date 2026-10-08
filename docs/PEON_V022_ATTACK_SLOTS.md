# Four attacks now; six active actions later

The v0.2.2 battle menu keeps Crystal's four attack slots. Mace Strike and Lightning Bolt are the basic attacks; the trainer prepares the two additional slots. Learned spells remain available for later preparation. Earth Totem is a reusable battle **BAGS** action: placing it consumes one turn and gives the player priority for that encounter. It is not a fifth permanent attack slot.

Six active attacks are feasible as a separate feature, but changing `NUM_MOVES` from four to six is not a safe shortcut. Party and boxed character structures, PP arrays, move-learning copies, battle buffers, menus, serialization and save offsets assume four entries. A global structure expansion risks misreading existing battery saves.

A possible future implementation uses a paged six-action menu, explicit extra-action storage and a temporary adapter into an existing battle slot. It must restore the underlying move/PP after execution and saving, preserve effects and targeting, and define how trainer preparation replaces actions. Any persistent extension needs a versioned migration plan. It also needs native menu, PP, item-action, level-up and cold-restart tests; it is not implemented in this release.

The current two-scorpid pack is two consecutive one-on-one encounters. There is still one active peon, one real battery save, and one functional Shaman route. Multi-character saves and simultaneous group combat remain separate future systems.
