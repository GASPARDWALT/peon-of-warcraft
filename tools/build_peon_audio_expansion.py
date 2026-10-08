#!/usr/bin/env python3
"""Append original, restrained GBC sounds for the existing Shaman chapter.

Run after build_peon_valley_sfx.py. Existing sound IDs, pointers and note data
are preserved; the expansion owns only its labelled sections. No WoW sound
recording was available for audition or transcription.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/warcraft_audio_update/sound_effects'
BEGIN = '; BEGIN PEON AUDIO EXPANSION'
END = '; END PEON AUDIO EXPANSION'

# duration, envelope volume, envelope decay, hardware frequency/noise control.
# Durations are deliberately short; silence notes separate tactile gestures.
EFFECTS = [
    ('level_up', 'LevelUp', 'LEVEL_UP', 'Small ascending bell with a quiet harmonic.', [
        (5, 1, [(2,7,2,1760),(2,7,2,1818),(3,6,2,1856),(7,5,2,1884)]),
        (6, 1, [(2,3,2,1617),(2,3,2,1695),(3,3,2,1758),(7,2,2,1804)]),
    ]),
    ('quest_accept', 'QuestAccept', 'QUEST_ACCEPT', 'Quiet parchment tap followed by a rising confirmation.', [
        (5, 2, [(2,4,1,1510),(4,5,2,1740),(3,2,1,1800)]),
        (8, None, [(1,3,1,0x54),(2,2,1,0x65)]),
    ]),
    ('quest_ready', 'QuestReady', 'QUEST_READY', 'Two restrained bright notes announcing a completed objective.', [
        (5, 1, [(2,5,1,1835),(1,0,0,0),(5,4,2,1900)]),
    ]),
    ('quest_reward', 'QuestReward', 'QUEST_REWARD', 'Warm resolved triad with a small metallic overtone.', [
        (5, 1, [(2,6,1,1740),(2,6,1,1818),(6,4,2,1884)]),
        (6, 2, [(2,2,1,1884),(2,3,1,1914),(6,2,2,1958)]),
    ]),
    ('healing', 'Healing', 'HEALING', 'Soft upward light with a gentle airy decay.', [
        (5, 1, [(3,3,2,1548),(3,4,2,1695),(5,4,2,1804),(5,2,2,1884)]),
        (8, None, [(3,2,2,0x35),(3,3,2,0x45),(5,2,2,0x54),(5,1,1,0x65)]),
    ]),
    ('potion', 'Potion', 'POTION', 'Bottle pop, two liquid bubbles and a short restoration note.', [
        (5, 2, [(1,4,1,1730),(2,3,1,1250),(2,4,1,1530),(5,3,2,1804)]),
        (8, None, [(1,5,1,0x25),(2,3,1,0x53),(2,3,1,0x43),(5,1,2,0x65)]),
    ]),
    ('food', 'Food', 'FOOD', 'Two small dry bread crunches; no melodic fanfare.', [
        (8, None, [(2,4,1,0x43),(2,2,1,0x65),(2,0,0,0),
                    (2,4,1,0x44),(3,2,1,0x65)]),
    ]),
    ('totem_place', 'TotemPlace', 'TOTEM_PLACE', 'Wood touches ground, followed by a low shamanic resonance.', [
        (5, 2, [(1,7,1,920),(3,4,2,460),(5,3,2,1180),(4,2,2,1510)]),
        (8, None, [(1,6,1,0x43),(3,3,1,0x64),(5,1,2,0x75)]),
    ]),
    ('hearthstone', 'Hearthstone', 'HEARTHSTONE', 'A rising then settling magical shimmer for the existing inn return.', [
        (5, 1, [(3,3,2,1460),(3,4,2,1660),(3,5,2,1818),(4,5,2,1914),
                 (4,3,2,1856),(6,2,2,1740)]),
        (8, None, [(3,2,2,0x45),(3,3,2,0x35),(3,3,2,0x25),(4,2,2,0x35),
                    (4,2,2,0x45),(6,1,1,0x65)]),
    ]),
    ('defeat', 'Defeat', 'DEFEAT', 'Brief descending acknowledgement; no full battle music theme.', [
        (5, 2, [(3,5,2,1510),(3,4,2,1280),(6,2,2,850)]),
    ]),
    ('victory', 'Victory', 'VICTORY', 'Three compact upward notes after a won encounter.', [
        (5, 1, [(2,5,1,1660),(2,5,1,1760),(5,4,2,1856)]),
    ]),
    ('scorpid_rattle', 'ScorpidRattle', 'SCORPID_RATTLE', 'Chitin clicks and a dry scraping hiss, distinct from Poison Sting.', [
        (5, 0, [(1,2,1,1810),(2,0,0,0),(1,2,1,1680),(5,1,1,1120)]),
        (8, None, [(1,7,1,0x24),(2,3,1,0x45),(1,6,1,0x34),(5,3,2,0x53)]),
    ]),
    ('imp_yelp', 'ImpYelp', 'IMP_YELP', 'Thin, uneven upward squeal with a short raspy tail.', [
        (5, 0, [(2,5,1,1440),(2,6,1,1810),(1,5,1,1660),(2,6,1,1870),(4,3,2,1390)]),
        (8, None, [(2,2,1,0x2d),(2,3,1,0x1d),(1,2,1,0x2c),(2,3,1,0x1c),(4,2,2,0x3d)]),
    ]),
    ('wolf_growl', 'WolfGrowl', 'WOLF_GROWL', 'Longer throat growl rising into one low bark; no copied creature cry.', [
        (5, 2, [(4,5,2,550),(4,6,2,780),(2,8,1,1260),(3,5,1,920),(4,2,2,450)]),
        (8, None, [(4,3,2,0x64),(4,4,2,0x54),(2,6,1,0x35),(3,4,1,0x54),(4,2,2,0x65)]),
    ]),
    ('water', 'Water', 'WATER', 'Two liquid drops and a quiet flowing water tail.', [
        (5, 2, [(2,3,1,1740),(2,4,1,1510),(2,3,1,1818),(5,2,2,1617)]),
        (8, None, [(2,2,2,0x35),(2,3,1,0x45),(2,2,2,0x35),(5,1,2,0x54)]),
    ]),
    ('frost', 'Frost', 'FROST', 'Brittle bright ice crack fading into a cold fine hiss.', [
        (5, 0, [(1,5,1,1958),(2,4,1,1900),(3,3,1,1835),(5,1,2,1740)]),
        (8, None, [(1,7,1,0x14),(2,5,1,0x24),(3,3,2,0x35),(5,1,2,0x45)]),
    ]),
    ('earth', 'Earth', 'EARTH', 'Low stone knock and coarse settling rubble.', [
        (5, 2, [(1,7,1,1120),(3,6,1,740),(5,3,2,350)]),
        (8, None, [(1,8,1,0x34),(3,5,1,0x54),(5,2,2,0x65)]),
    ]),
    ('purge', 'Purge', 'PURGE', 'Quick stripping sweep with a clean magical release.', [
        (5, 0, [(2,4,1,1900),(2,5,1,1740),(3,3,1,1510),(4,2,2,1100)]),
        (8, None, [(2,3,1,0x25),(2,4,1,0x35),(3,3,1,0x45),(4,1,2,0x65)]),
    ]),
    ('nature', 'Nature', 'NATURE', 'Soft wooden resonance and a short leafy breeze.', [
        (5, 1, [(3,3,2,1460),(3,4,2,1695),(5,3,2,1760)]),
        (8, None, [(3,2,2,0x54),(3,3,2,0x45),(5,1,2,0x65)]),
    ]),
]


def strip_owned(text):
    if BEGIN not in text:
        assert END not in text
        return text
    assert text.count(BEGIN) == text.count(END) == 1
    before, tail = text.split(BEGIN, 1)
    _owned, after = tail.split(END, 1)
    return before + after.lstrip('\n')


def table_entries(text, command):
    return re.findall(r'^\s*' + command + r'\s+(\w+)', text, re.M)


def render(effect, sound_id):
    name, short, suffix, description, voices = effect
    label, constant = 'PeonSfx_' + short, 'SFX_PEON_' + suffix
    assert 1 <= len(voices) <= 2
    lines = ['; ' + description, label + ':', f'\tchannel_count {len(voices)}']
    lines += [f'\tchannel {voice}, {label}_Ch{voice}' for voice, _, _ in voices]
    durations = {}
    for voice, duty, notes in voices:
        assert voice in (5, 6, 8)
        lines += ['', f'{label}_Ch{voice}:']
        if duty is not None:
            assert duty in (0, 1, 2, 3)
            lines.append(f'\tduty_cycle {duty}')
        if voice == 5:
            lines.append('\tpitch_sweep 0, 8')
        for duration, volume, decay, frequency in notes:
            assert 0 <= duration <= 12 and 0 <= volume <= 9 and 0 <= decay <= 7
            assert 0 <= frequency <= (255 if voice == 8 else 2047)
            command = 'noise_note' if voice == 8 else 'square_note'
            lines.append(f'\t{command} {duration}, {volume}, {decay}, {frequency}')
        durations[voice] = sum(n[0] + 1 for n in notes)
        lines.append('\tsound_ret')
    assert max(durations.values()) <= 40
    return '\n'.join(lines) + '\n', {
        'name': name, 'header': label, 'existing_sfx_id': constant,
        'sfx_id': sound_id, 'sfx_id_hex': f'${sound_id:02x}',
        'description': description, 'channels': [v[0] for v in voices],
        'estimated_channel_frames': durations,
        'maximum_envelope_volume': max(n[1] for _, _, notes in voices for n in notes),
        'source': 'Original newly authored GBC pulse/noise synthesis.',
        'runtime_integration_owned_by_root': True,
    }


def main():
    paths = [ROOT / 'audio/peon_sfx.asm', ROOT / 'constants/sfx_constants.asm',
             ROOT / 'audio/sfx_pointers.asm']
    original = [path.read_text() for path in paths]
    source, constants, pointers = [strip_owned(text) for text in original]
    source = source.rstrip() + '\n'
    ids, addresses = table_entries(constants, 'const'), table_entries(pointers, 'dba')
    assert len(ids) == len(addresses) == 208, 'Baseline must preserve all 208 existing sounds'
    assert ids[-1] == 'SFX_PEON_BOAR_GRUNT' and addresses[-1] == 'PeonSfx_BoarGrunt'
    assert 'PeonSfx_Lightning:\n' in source and 'PeonSfx_BoarGrunt:\n' in source
    assert len(ids) + len(EFFECTS) <= 256
    rendered, effects, constant_lines, pointer_lines = [], [], [], []
    for offset, effect in enumerate(EFFECTS):
        text, metadata = render(effect, len(ids) + offset)
        rendered.append(text)
        effects.append(metadata)
        constant_lines.append(f"\tconst {metadata['existing_sfx_id']:<32} ; {metadata['sfx_id']:02x}")
        pointer_lines.append('\tdba ' + metadata['header'])
    source = source.rstrip() + '\n\n' + BEGIN + '\n' + \
        '; Generated by tools/build_peon_audio_expansion.py; original synthesis.\n' + \
        'SECTION "Peon Audio Expansion", ROMX\n\n' + '\n'.join(rendered) + END + '\n'
    const_marker = 'DEF NUM_SFX EQU const_value'
    ptr_marker = '\tassert_table_length NUM_SFX'
    assert constants.count(const_marker) == pointers.count(ptr_marker) == 1
    constants = constants.replace(const_marker, BEGIN + '\n' + '\n'.join(constant_lines) + '\n' + END + '\n\n' + const_marker)
    pointers = pointers.replace(ptr_marker, BEGIN + '\n' + '\n'.join(pointer_lines) + '\n' + END + '\n' + ptr_marker)
    assert table_entries(constants, 'const')[:208] == ids
    assert table_entries(pointers, 'dba')[:208] == addresses
    assert strip_owned(source).rstrip() == strip_owned(original[0]).rstrip()
    for path, text in zip(paths, (source, constants, pointers)):
        path.write_text(text)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        'effects': effects, 'new_effects': len(effects), 'native_sfx_count': 208 + len(effects),
        'existing_sound_count_preserved': 208, 'existing_ids_shifted': False,
        'existing_note_data_preserved': True,
        'baseline_note_data_sha256': hashlib.sha256((strip_owned(original[0]).rstrip() + '\n').encode()).hexdigest(),
        'regeneration_order': 'build_peon_sfx.py baseline, build_peon_valley_sfx.py override, build_peon_audio_expansion.py last.',
        'reference_access': 'Original WoW recording unavailable; not auditioned, copied or transcribed.',
        'no_music_or_engine_code_written': True,
    }
    (OUT / 'design.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({e['existing_sfx_id']: e['sfx_id_hex'] for e in effects}, indent=2))


if __name__ == '__main__':
    main()
