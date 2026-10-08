SECTION "Peon Defeat Recovery", ROMX

; CANLOSE encounters never award loot, retire the enemy, or fully heal the
; player. Leave one HP so the apprentice can walk to an inn after the respawn.
; Clear poison on this defeat recovery to avoid an immediate overworld faint.
PeonRecoverFromDefeat::
	xor a
	ld [wPartyMon1Status], a
	ld [wPartyMon1HP], a
	inc a
	ld [wPartyMon1HP + 1], a
	ret
