#!/usr/bin/env python3
"""Author two original native effects while preserving every existing SFX ID.

Run after build_peon_sfx.py if rebuilding its baseline. These are original GBC
pulse/noise gestures; unavailable WoW recordings have not been auditioned.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/valley_layout_update/sound_effects'
EFFECTS = [
    ('lightning_bolt', 'PeonSfx_Lightning', 'SFX_THUNDERSHOCK',
     'Quiet rising charge, sharp broadband crack, descending electric hiss.', [
         (5, 0, [(2,2,2,1100),(2,3,2,1480),(1,4,1,1750),(1,4,1,850),
                 (2,2,1,1740),(3,1,1,1900),(4,0,0,0)]),
         (8, None, [(2,3,3,0x35),(2,5,2,0x25),(1,7,1,0x14),(1,12,1,0x02),
                    (2,9,1,0x24),(3,6,2,0x35),(4,3,1,0x45),(4,2,1,0x54)]),
     ]),
    ('boar_grunt', 'PeonSfx_BoarGrunt', 'SFX_PEON_BOAR_GRUNT',
     'Two brief warm low-register grunts with a gravelly noise layer.', [
         (5, 2, [(2,8,2,1280),(2,9,1,940),(3,5,1,550),(2,0,0,0),
                 (2,9,1,1100),(3,6,1,760),(2,3,1,450)]),
         (8, None, [(2,4,2,0x35),(2,6,1,0x53),(3,3,1,0x64),(2,0,0,0),
                    (2,5,1,0x45),(3,4,1,0x54),(2,2,1,0x65)]),
     ]),
]


def render(effect):
    name,label,constant,description,channels = effect
    lines = [f'; {description}', '; Original override: tools/build_peon_valley_sfx.py.',
             label+':', f'\tchannel_count {len(channels)}']
    lines += [f'\tchannel {c}, {label}_Ch{c}' for c,_,_ in channels]
    lengths = {}
    for channel,duty,notes in channels:
        lines += ['', f'{label}_Ch{channel}:']
        if duty is not None: lines.append(f'\tduty_cycle {duty}')
        if channel == 5: lines.append('\tpitch_sweep 0, 8')
        command = 'noise_note' if channel == 8 else 'square_note'
        for duration,volume,envelope,frequency in notes:
            assert 0<=duration<0xd0 and 0<=volume<=12 and 0<=envelope<=7
            assert 0<=frequency<=(255 if channel==8 else 2047)
            lines.append(f'\t{command} {duration}, {volume}, {envelope}, {frequency}')
        lines.append('\tsound_ret'); lengths[channel]=sum(n[0]+1 for n in notes)
    assert max(lengths.values())<=40
    return '\n'.join(lines)+'\n', {'name':name,'header':label,'existing_sfx_id':constant,
        'description':description,'channels':[c for c,_,_ in channels],
        'channel_frames':lengths,'estimated_engine_frames':max(lengths.values()),
        'estimated_seconds':max(lengths.values())/60,
        'source':'Original newly authored native GBC pulse/noise synthesis.'}


def main():
    path=ROOT/'audio/peon_sfx.asm'; source=path.read_text()
    # Bound the replacement by native labels, so unrelated effects stay byte-identical.
    start=source.index('PeonSfx_Lightning:\n')
    start=source.rfind('\n;',0,start)+1
    if source[start:].startswith('; Original override:'):
        start=source.rfind('\n;',0,start-1)+1
    end=source.index('; Flame ignition, fiery rush and low impact',start)
    new,lightning=render(EFFECTS[0]); source=source[:start]+new+'\n'+source[end:]
    if 'PeonSfx_BoarGrunt:\n' in source:
        start=source.index('PeonSfx_BoarGrunt:\n'); start=source.rfind('\n;',0,start)+1
        if source[start:].startswith('; Original override:'):
            start=source.rfind('\n;',0,start-1)+1
        source=source[:start].rstrip()+'\n'
    new,boar=render(EFFECTS[1]); source=source.rstrip()+'\n\n'+new
    path.write_text(source)
    const_path=ROOT/'constants/sfx_constants.asm'; constants=const_path.read_text()
    if not re.search(r'^\s*const SFX_PEON_BOAR_GRUNT\b',constants,re.M):
        assert constants.count('DEF NUM_SFX EQU const_value')==1
        constants=constants.replace('DEF NUM_SFX EQU const_value',
            '\tconst SFX_PEON_BOAR_GRUNT             ; cf — appended native encounter sound\n\nDEF NUM_SFX EQU const_value')
        const_path.write_text(constants)
    pointer_path=ROOT/'audio/sfx_pointers.asm'; pointers=pointer_path.read_text()
    if not re.search(r'^\s*dba PeonSfx_BoarGrunt\b',pointers,re.M):
        assert pointers.count('\tassert_table_length NUM_SFX')==1
        pointers=pointers.replace('\tassert_table_length NUM_SFX',
            '\tdba PeonSfx_BoarGrunt\n\tassert_table_length NUM_SFX')
        pointer_path.write_text(pointers)
    count=len(re.findall(r'^\s*const SFX_',constants,re.M)); assert count<=256
    assert len(re.findall(r'^\s*dba\b',pointers,re.M))==count
    OUT.mkdir(parents=True,exist_ok=True)
    design={'effects':[lightning,boar],'native_sfx_count':count,
        'existing_ids_shifted':False,'reference_access':'Wowhead Classic request denied; no original audio auditioned or copied.',
        'regeneration_order':'build_peon_sfx.py baseline, then build_peon_valley_sfx.py override.',
        'native_effect_source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT/'design.json').write_text(json.dumps(design,indent=2)+'\n')
    print(json.dumps({'effects':2,'native_sfx_count':count,'existing_ids_shifted':False}))


if __name__=='__main__':main()
