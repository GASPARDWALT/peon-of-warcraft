#!/usr/bin/env python3
"""Compose original, synchronized four-channel Durotar prototype themes.

No Warcraft recording or melody is copied. Sparse minor/pentatonic pulse
phrases, a quiet wave bass and restrained toms fit the native Game Boy APU.
The retained score is the source; rebuilding never downloads external audio.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'references/generated/durotar_v022/ambient_music'

SCORES = {
    'Durotar': (176, [
        'D_4:4 -:2 A_3:2 C_4:4 D_4:4',
        'F_4:4 D_4:2 -:2 C_4:4 A_3:4',
        'G_4:4 F_4:4 D_4:4 -:4',
        'C_4:4 A_3:4 G_3:4 A_3:4',
        'D_4:4 -:2 F_4:2 G_4:4 A_4:4',
        'G_4:4 F_4:4 C_4:4 D_4:4',
        'F_4:4 D_4:4 A_3:4 C_4:4',
        'D_4:8 -:8'], ['D_3','F_3','G_3','A_2','D_3','C_3','F_3','D_3']),
    'Cave': (192, [
        'D_3:4 -:4 A_3:4 -:4', 'F_3:4 -:4 E_3:4 -:4',
        'D_3:4 A_2:4 C_3:4 -:4', 'E_3:4 -:4 D_3:4 -:4',
        'A_3:4 -:4 G_3:4 -:4', 'F_3:4 E_3:4 D_3:4 -:4',
        'C_3:4 -:4 A_2:4 -:4', 'D_3:8 -:8'],
        ['D_2','F_2','D_2','A_2','G_2','F_2','A_2','D_2']),
    'Battle': (124, [
        'D_4:2 A_3:2 D_4:2 F_4:2 G_4:4 A_4:4',
        'C_5:2 A_4:2 G_4:2 F_4:2 D_4:4 A_3:4',
        'G_4:2 D_4:2 G_4:2 A_4:2 C_5:4 A_4:4',
        'F_4:2 E_4:2 D_4:2 C_4:2 A_3:4 C_4:4',
        'D_4:2 F_4:2 G_4:2 A_4:2 C_5:4 D_5:4',
        'C_5:2 A_4:2 G_4:2 F_4:2 E_4:4 D_4:4',
        'F_4:2 D_4:2 C_4:2 A_3:2 G_3:4 A_3:4',
        'D_4:4 A_3:4 D_4:4 -:4'],
        ['D_3','F_3','G_3','A_2','D_3','C_3','F_3','D_3']),
    'Inn': (168, [
        'D_4:4 F_4:4 A_4:4 F_4:4', 'C_4:4 E_4:4 G_4:4 E_4:4',
        'F_4:4 A_4:4 C_5:4 A_4:4', 'G_4:4 E_4:4 C_4:4 -:4',
        'D_4:4 F_4:4 A_4:4 G_4:4', 'F_4:4 D_4:4 C_4:4 E_4:4',
        'F_4:4 A_4:4 G_4:4 E_4:4', 'D_4:8 -:8'],
        ['D_3','C_3','F_3','C_3','D_3','C_3','F_3','D_3']),
    'Victory': (132, ['D_4:2 F_4:2 A_4:4 C_5:4 D_5:4',
                       'A_4:4 F_4:4 D_4:8'], ['D_3','D_3']),
    'Barrens': (184, [
        'A_3:4 -:4 D_4:4 E_4:4', 'G_4:4 E_4:4 D_4:4 -:4',
        'E_4:4 G_4:4 A_4:4 -:4', 'G_4:4 D_4:4 C_4:4 -:4',
        'D_4:6 -:2 E_4:4 G_4:4', 'A_4:4 G_4:4 E_4:4 -:4',
        'D_4:4 C_4:4 A_3:4 G_3:4', 'A_3:8 -:8'],
        ['A_2','D_3','E_3','G_2','D_3','A_2','C_3','A_2']),
    'Orgrimmar': (156, [
        'D_3:2 -:2 D_4:4 A_3:4 D_4:4',
        'F_4:4 E_4:4 D_4:4 A_3:4',
        'G_3:2 -:2 G_4:4 D_4:4 G_4:4',
        'F_4:4 D_4:4 C_4:4 A_3:4',
        'D_4:2 F_4:2 A_4:4 G_4:4 F_4:4',
        'E_4:4 D_4:4 A_3:4 C_4:4',
        'F_4:4 G_4:4 A_4:4 C_5:4',
        'D_5:4 A_4:4 D_4:4 -:4'],
        ['D_3','F_3','G_3','A_2','D_3','C_3','F_3','D_3']),
}


def emit_notes(pattern):
    result, total = [], 0
    for token in pattern.split():
        pitch, duration = token.split(':')
        duration = int(duration)
        total += duration
        if pitch == '-':
            result.append(f'\trest {duration}')
        else:
            result += [f'\toctave {pitch[-1]}', f'\tnote {pitch[:-1]}, {duration}']
    assert total == 16, (pattern, total)
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ['; Generated original compositions: tools/build_peon_ambient_music.py.',
             'SECTION "Peon Durotar Music", ROMX', '']
    report = []
    for name, (tempo, melody, roots) in SCORES.items():
        label = f'Music_Peon{name}'
        assert len(melody) == len(roots)
        lines += [label + ':', '\tchannel_count 4']
        lines += [f'\tchannel {i}, {label}_Ch{i}' for i in range(1, 5)]
        for channel in range(1, 5):
            lines += ['', f'{label}_Ch{channel}:']
            if channel == 1:
                lines += [f'\ttempo {tempo}', '\tvolume 7, 7', '\tduty_cycle 1',
                          '\tstereo_panning TRUE, TRUE', '\tvibrato 12, 1, 3',
                          '\tnote_type 12, 6, 3']
            elif channel == 2:
                lines += ['\tduty_cycle 2', '\tstereo_panning TRUE, TRUE',
                          '\tnote_type 12, 4, 2']
            elif channel == 3:
                lines += ['\tstereo_panning TRUE, TRUE', '\tnote_type 12, 2, 1']
            else:
                lines += ['\ttoggle_noise 0', '\tdrum_speed 12',
                          '\tstereo_panning TRUE, TRUE']
            lines.append('.loop:')
            for pattern, root in zip(melody, roots):
                if channel == 1:
                    lines += emit_notes(pattern)
                elif channel == 2:
                    lines += emit_notes(f'-:4 {root}:4 -:4 {root}:4')
                elif channel == 3:
                    low = root[:-1] + str(max(1, int(root[-1]) - 1))
                    lines += emit_notes(f'{low}:6 -:2 {low}:6 -:2')
                elif name == 'Battle':
                    lines += ['\tdrum_note 3, 2', '\trest 2', '\tdrum_note 3, 2',
                              '\trest 2', '\tdrum_note 4, 2', '\trest 2',
                              '\tdrum_note 3, 2', '\trest 2']
                else:
                    lines += ['\tdrum_note 3, 2', '\trest 6',
                              '\tdrum_note 4, 2', '\trest 6']
            lines += ['\tsound_ret' if name == 'Victory' else '\tsound_loop 0, .loop']
        report.append({'name': name, 'label': label, 'tempo': tempo,
                       'channels': 4, 'sixteenth_ticks_per_channel': len(melody)*16,
                       'loops': name != 'Victory', 'original_composition': True,
                       'imported_Warcraft_audio': False})
    (ROOT / 'audio/peon_ambient_music.asm').write_text('\n'.join(lines) + '\n')
    (OUT / 'score_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{len(report)} original synchronized four-channel themes generated')


if __name__ == '__main__':
    main()
