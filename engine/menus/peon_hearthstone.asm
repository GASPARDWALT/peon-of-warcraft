; Hearthstone uses Crystal's event bits, queued overworld scripts and native
; warp transition. No save structure or world-coordinate field is added.

SECTION "Peon Hearthstone", ROMX

PeonBindAtInn::
	ld a, [wBattleMode]
	and a
	ret nz
	ld a, [wMapGroup]
	cp GROUP_PEON_ORC_INN
	ret nz
	ld a, [wMapNumber]
	cp MAP_PEON_ORC_INN
	jr z, .valid
	cp MAP_PEON_TROLL_INN
	ret nz
.valid:
	ld de, EVENT_PEON_HOME_DEN
	ld b, RESET_FLAG
	call EventFlagAction
	ld de, EVENT_PEON_HOME_SENJIN
	ld b, RESET_FLAG
	call EventFlagAction
	ld de, EVENT_PEON_HOME_RAZOR
	ld b, RESET_FLAG
	call EventFlagAction
	ld de, EVENT_PEON_HEARTH_GRANTED
	ld b, SET_FLAG
	call EventFlagAction
	ld a, [wMapNumber]
	cp MAP_PEON_TROLL_INN
	ld de, EVENT_PEON_HOME_SENJIN
	jr z, .bind
	ld a, [wBackupMapNumber]
	cp MAP_RAZOR_HILL
	ld de, EVENT_PEON_HOME_RAZOR
	jr z, .bind
	ld de, EVENT_PEON_HOME_DEN
.bind:
	ld b, SET_FLAG
	jp EventFlagAction

PeonHearthstoneMenu::
	ld a, [wBattleMode]
	and a
	jr nz, .cancel
	ld de, EVENT_PEON_HEARTH_GRANTED
	call .Check
	jr z, .unbound
	ld hl, .DenQuestion
	ld de, EVENT_PEON_HOME_SENJIN
	call .Check
	jr z, .razor
	ld hl, .SenjinQuestion
	jr .ask
.razor:
	ld de, EVENT_PEON_HOME_RAZOR
	call .Check
	jr z, .ask
	ld hl, .RazorQuestion
.ask:
	call MenuTextbox
	call YesNoBox
	push af
	call CloseWindow
	pop af
	jr c, .cancel
	ld hl, PeonHearthReturnScript
	call QueueScript
	ld a, 4 ; StartMenu's normal queued-overworld-script return
	ld c, a ; FarCall restores A from C, so carry the menu result in C.
	ret
.unbound:
	ld hl, .UnboundText
	call MenuTextboxBackup
.cancel:
	xor a
	ld c, a
	ret
.Check:
	push hl
	ld b, CHECK_FLAG
	call EventFlagAction
	pop hl
	ld a, c
	and a
	ret
.DenQuestion:
	text "HEARTHSTONE"
	para "Return to The Den?"
	done
.SenjinQuestion:
	text "HEARTHSTONE"
	para "Return to Sen'jin?"
	done
.RazorQuestion:
	text "HEARTHSTONE"
	para "Return to Razor"
	line "Hill?"
	done
.UnboundText:
	text "HEARTHSTONE"
	para "Visit an innkeeper"
	line "to choose your"
	cont "home first."
	done

; Also available to the prototype's defeat recovery through farsjump. An
; unbound character returns to The Den; recovery/healing is the caller's job.
PeonHearthReturnScript::
	refreshmap
	special UpdateTimePals
	closetext
	playsound SFX_WARP_TO
	applymovement PLAYER, .Cast
	checkevent EVENT_PEON_HOME_SENJIN
	iftrue .Senjin
	checkevent EVENT_PEON_HOME_RAZOR
	iftrue .Razor
	warpmod 2, THE_DEN
	warpfacing DOWN, PEON_ORC_INN, 5, 6
	sjump .Arrived
.Senjin:
	warpmod 3, SENJIN_VILLAGE
	warpfacing DOWN, PEON_TROLL_INN, 5, 6
	sjump .Arrived
.Razor:
	warpmod 4, RAZOR_HILL
	warpfacing DOWN, PEON_ORC_INN, 5, 6
.Arrived:
	playsound SFX_WARP_FROM
	applymovement PLAYER, .Arrive
	end
.Cast:
	teleport_from
	step_end
.Arrive:
	teleport_to
	step_end
