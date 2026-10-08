#!/usr/bin/env python3
"""Idempotent original four-channel ambience refinement, after the base builder.

Only Durotar, Cave and Inn are replaced. The seven existing song IDs, section,
headers and channel labels remain stable; Battle/Victory/Barrens/Orgrimmar are
retained byte for byte. No title music, engine file or published asset is edited.
Use --validate only after the parent has compiled this source: listening
previews are captured from the actual ROM APU into the new update directory.
"""
import argparse
import ast
import hashlib
import inspect
import json
import logging
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from build_peon_ambient_music import SCORES

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'audio/peon_ambient_music.asm'
OUT=ROOT/'references/generated/warcraft_audio_update/music'
ORDER=list(SCORES)
HEADER='; Refined original ambiences: tools/build_peon_ambient_refinement.py.'

# Each row is a complete bar. Short plucked notes and longer call/response
# voices share an exact clock, including every rest and the final breath.
REFINEMENTS={
    'Durotar':dict(tempo=176,bar=16,kit=3,lead=(6,3),answer=(3,5),wave=(2,0),
        lead_duty=2,answer_duty=1,
        description='Rustic D-minor pentatonic call/response, warm drone, irregular hand-drum pulse.',
        melody=[
            'D_4:6 -:2 A_3:4 C_4:4','D_4:4 F_4:6 D_4:2 -:4',
            'G_4:6 F_4:2 D_4:4 C_4:4','A_3:8 -:4 C_4:2 D_4:2',
            'F_4:6 -:2 G_4:4 A_4:4','C_5:4 A_4:6 G_4:2 -:4',
            'F_4:4 G_4:2 F_4:2 D_4:4 C_4:4','D_4:8 -:8',
            'A_3:4 D_4:4 F_4:6 -:2','G_4:4 A_4:4 G_4:4 F_4:4',
            'D_4:6 C_4:2 A_3:4 G_3:4','A_3:8 C_4:4 -:4',
            'D_4:4 F_4:4 G_4:4 A_4:4','C_5:6 A_4:2 G_4:4 -:4',
            'F_4:4 D_4:4 C_4:4 A_3:4','D_4:10 -:6'],
        chords=[('D_3','F_3','A_3'),('F_3','A_3','C_4'),('G_3','C_4','D_4'),('D_3','F_3','A_3'),
            ('F_3','A_3','C_4'),('C_3','G_3','C_4'),('G_3','C_4','D_4'),('D_3','F_3','A_3'),
            ('D_3','F_3','A_3'),('G_3','C_4','D_4'),('F_3','A_3','C_4'),('C_3','G_3','C_4'),
            ('D_3','F_3','A_3'),('C_3','G_3','C_4'),('A_2','D_3','A_3'),('D_3','F_3','A_3')]),
    'Cave':dict(tempo=196,bar=16,kit=3,lead=(4,4),answer=(2,5),wave=(3,0),
        lead_duty=0,answer_duty=2,
        description='Hollow low pulse echoes, unresolved minor seconds, sparse low drum and sustained wave drone.',
        melody=[
            'D_3:8 -:8','A_3:4 -:4 F_3:4 -:4','D#3:4 D_3:4 -:8','C_3:6 -:2 A_2:4 -:4',
            'D_3:6 F_3:2 -:8','G_3:4 -:4 F_3:4 -:4','D#3:4 D_3:4 C_3:4 -:4','A_2:8 -:8',
            'F_3:4 -:4 A_3:6 -:2','G_3:6 F_3:2 -:8','D_3:4 D#3:2 D_3:2 C_3:4 -:4','A_2:12 -:4',
            'C_3:6 -:2 D_3:4 F_3:4','D#3:4 -:4 D_3:4 -:4','C_3:4 A_2:4 G_2:4 -:4','D_3:8 -:8'],
        answers=[
            '-:8 A_2:4 -:4','-:6 D_3:4 -:6','-:8 F_2:4 -:4','-:8 A_2:4 -:4',
            '-:6 A_2:4 -:6','-:8 D_3:4 -:4','-:8 F_2:4 -:4','-:10 D_3:2 -:4',
            '-:8 D_3:4 -:4','-:6 C_3:4 -:6','-:8 A_2:4 -:4','-:8 C_3:4 -:4',
            '-:8 F_2:4 -:4','-:8 A_2:4 -:4','-:8 C_3:4 -:4','-:8 A_2:4 -:4'],
        roots=['D_2','D_2','F_2','D_2','D_2','G_2','D_2','A_1',
               'F_2','G_2','D_2','A_1','F_2','D_2','C_2','D_2']),
    'Inn':dict(tempo=164,bar=12,kit=0,lead=(5,3),answer=(3,1),wave=(2,0),
        lead_duty=2,answer_duty=1,
        description='Restful three-beat hearth tune, plucked modal arpeggios and quiet brushed percussion.',
        melody=[
            'D_4:4 F_4:2 A_4:2 F_4:4','E_4:4 G_4:2 C_5:2 G_4:4',
            'F_4:4 A_4:2 C_5:2 A_4:4','G_4:4 E_4:4 -:4',
            'D_4:4 F_4:4 A_4:4','G_4:2 F_4:2 E_4:4 C_4:4',
            'F_4:4 G_4:2 A_4:2 F_4:4','D_4:8 -:4',
            'A_4:4 G_4:2 F_4:2 D_4:4','E_4:4 G_4:4 C_5:4',
            'A_4:4 C_5:2 A_4:2 F_4:4','G_4:6 E_4:2 -:4',
            'F_4:4 D_4:2 F_4:2 A_4:4','G_4:4 F_4:4 E_4:4',
            'C_4:4 E_4:2 F_4:2 A_4:4','D_4:8 -:4'],
        chords=[('D_3','F_3','A_3'),('C_3','E_3','G_3'),('F_3','A_3','C_4'),('C_3','E_3','G_3'),
            ('D_3','F_3','A_3'),('C_3','E_3','G_3'),('F_3','A_3','C_4'),('D_3','F_3','A_3'),
            ('D_3','F_3','A_3'),('C_3','E_3','G_3'),('F_3','A_3','C_4'),('C_3','E_3','G_3'),
            ('D_3','F_3','A_3'),('C_3','E_3','G_3'),('F_3','A_3','C_4'),('D_3','F_3','A_3')])}


def lower(pitch):return pitch[:-1]+str(max(1,int(pitch[-1])-1))


def emit(pattern,bar,drums=False):
    result=[];total=0
    for token in pattern.split():
        pitch,duration=token.rsplit(':',1);duration=int(duration)
        assert 1<=duration<=16;total+=duration
        if pitch=='-':result.append(f'\trest {duration}')
        elif drums:
            assert 1<=int(pitch)<=12;result.append(f'\tdrum_note {pitch}, {duration}')
        else:
            assert re.fullmatch(r'[A-G](?:_|#)[1-8]',pitch),pitch
            result.extend([f'\toctave {pitch[-1]}',f'\tnote {pitch[:-1]}, {duration}'])
    assert total==bar,(pattern,total,bar)
    return result


def channels(name,score):
    melody=score['melody'];bar=score['bar'];result=[melody,[],[],[]]
    assert len(melody)==16
    for i in range(16):
        if name=='Cave':
            result[1].append(score['answers'][i])
            root=score['roots'][i];result[2].append(f'{root}:12 -:4')
            result[3].append('4:1 -:15' if i%2 else '-:8 2:1 -:7')
        else:
            root,third,fifth=score['chords'][i]
            if name=='Inn':
                result[1].append(f'{root}:2 {third}:2 {fifth}:2 {third}:2 {fifth}:2 -:2')
                result[2].append(f'{lower(root)}:4 -:2 {lower(fifth)}:4 -:2')
                result[3].append('6:1 -:7 8:1 -:3' if i%4!=3 else '6:1 -:3 8:1 -:3 6:1 -:3')
            else:
                result[1].append(f'-:4 {root}:6 -:2 {fifth}:4' if i%2==0 else f'-:6 {third}:4 {root}:4 -:2')
                result[2].append(f'{lower(root)}:10 -:2 {lower(fifth)}:4')
                result[3].append(['4:1 -:7 2:1 -:3 7:1 -:3','4:1 -:5 2:1 -:5 4:1 -:3',
                    '4:1 -:7 2:1 -:7','4:1 -:5 2:1 -:1 4:1 -:3 2:1 -:3'][i%4])
    for channel,patterns in enumerate(result):
        assert len(patterns)==16
        for pattern in patterns:emit(pattern,bar,channel==3)
    return result


def track(name):
    score=REFINEMENTS[name];label='Music_Peon'+name;parts=channels(name,score)
    lines=[label+':','\tchannel_count 4']+[f'\tchannel {i}, {label}_Ch{i}' for i in range(1,5)]
    for i,patterns in enumerate(parts,1):
        lines.extend(['',f'{label}_Ch{i}:'])
        if i==1:
            lines.extend([f'\ttempo {score["tempo"]}','\tvolume 7, 7',f'\tduty_cycle {score["lead_duty"]}',
                '\tstereo_panning TRUE, TRUE','\tvibrato 16, 1, 3',
                f'\tnote_type 12, {score["lead"][0]}, {score["lead"][1]}'])
        elif i==2:
            lines.extend([f'\tduty_cycle {score["answer_duty"]}','\tstereo_panning TRUE, TRUE',
                f'\tnote_type 12, {score["answer"][0]}, {score["answer"][1]}'])
        elif i==3:
            lines.extend(['\tstereo_panning TRUE, TRUE',f'\tnote_type 12, {score["wave"][0]}, {score["wave"][1]}'])
        else:lines.extend([f'\ttoggle_noise {score["kit"]}','\tdrum_speed 12','\tstereo_panning TRUE, TRUE'])
        lines.append('.loop:')
        for bar,pattern in enumerate(patterns,1):
            lines.append(f'\t; Bar {bar:02d}: {"hearth 3/4" if name=="Inn" else "four-beat phrase"}')
            lines.extend(emit(pattern,score['bar'],i==4))
        lines.append('\tsound_loop 0, .loop')
    return '\n'.join(lines)+'\n'


def blocks(text):
    pattern=r'(?m)^Music_Peon('+ '|'.join(ORDER)+r'):$'
    starts=list(re.finditer(pattern,text))
    assert [match[1] for match in starts]==ORDER,'Native song order/labels changed'
    return {match[1]:(match.start(),starts[i+1].start() if i+1<len(starts) else len(text))
            for i,match in enumerate(starts)}


def refined(text):
    spans=blocks(text);preserved={name:text[a:b] for name,(a,b) in spans.items() if name not in REFINEMENTS}
    for name,(a,b) in reversed(list(spans.items())):
        if name in REFINEMENTS:text=text[:a]+track(name)+text[b:]
    text=text.replace(HEADER+'\n','')
    text=HEADER+'\n'+text
    assert text.count('SECTION "Peon Durotar Music", ROMX')==1
    for name,(a,b) in blocks(text).items():
        if name in preserved:assert text[a:b]==preserved[name],(name,'Unowned theme changed')
    return text


def manifest():
    result=[]
    for index,name in enumerate(ORDER):
        tempo,melody,_=SCORES[name]
        if name in REFINEMENTS:
            score=REFINEMENTS[name];tempo=score['tempo'];ticks=len(score['melody'])*score['bar']
        else:ticks=len(melody)*16
        frames=ticks*12*tempo/256
        result.append({'name':name,'label':'Music_Peon'+name,'native_music_id':0x67+index,
            'tempo':tempo,'channels':4,'sixteenth_ticks_per_channel':ticks,'loops':name!='Victory',
            'original_composition':True,'imported_Warcraft_audio':False,
            'refined_in_this_update':name in REFINEMENTS,'expected_phrase_frames':frames,
            'expected_phrase_seconds':round(frames/(4194304/(456*154)),3),
            'arrangement':REFINEMENTS[name]['description'] if name in REFINEMENTS else 'Retained existing original arrangement.'})
    return result


def generate():
    OUT.mkdir(parents=True,exist_ok=True)
    before=SOURCE.read_text();after=refined(before)
    SOURCE.write_text(after)
    assert refined(after)==after,'Override is not idempotent'
    scores=manifest();(OUT/'score_manifest.json').write_text(json.dumps(scores,indent=2)+'\n')
    report={'source_sha256':hashlib.sha256(after.encode()).hexdigest(),'modified_themes':list(REFINEMENTS),
        'retained_themes':[name for name in ORDER if name not in REFINEMENTS],
        'section_preserved':True,'song_ids_and_channel_labels_preserved':True,'idempotent_override':True,
        'all_four_channels_have_equal_phrase_ticks':True,'title_music_untouched':True,
        'original_composition_not_a_transcription_of_verified_WoW_audio':True}
    (OUT/'composition.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'README.md').write_text('# Original Warcraft-inspired GBC ambiences\n\n'
        'Durotar/Den, Burning Blade Cave and the inns receive original four-channel arrangements. '
        'They are not verified transcriptions of Blizzard music. Battle, victory, Barrens and '
        'Orgrimmar remain the previous original scores; the supplied title theme is untouched.\n\n'
        'Run the existing base generator first, then `python tools/build_peon_ambient_refinement.py`. '
        'After the ROM is compiled, use `--validate` to capture the actual APU as WAV and MP3. '
        'Native captures are isolated song-selection diagnostics; ordinary map selection is tested separately.\n')
    for score in scores:
        print(score['name'],'refined' if score['refined_in_this_update'] else 'retained',
              score['sixteenth_ticks_per_channel'],'ticks',score['expected_phrase_seconds'],'seconds',flush=True)


def validate():
    # Reuse every existing native APU assertion. Only the maximum diagnostic
    # wait is extended for the deliberately longer phrases; no test is removed.
    import validate_peon_ambient_music as native
    from validate_peon_villages import load_symbols
    native.OUT=OUT;OUT.mkdir(exist_ok=True,parents=True);logging.disable(logging.CRITICAL)
    def native_audio_metrics(raw):
        """Measure the raw int8 emulator mix before DC removal or preview gain."""
        count=int(raw.size);limits=int(((raw==127)|(raw==-128)).sum())
        result={'raw_dtype':str(raw.dtype),'raw_sample_count':count,
            'raw_minimum':int(raw.min()),'raw_maximum':int(raw.max()),
            'raw_mixer_limit_samples':limits,'raw_mixer_limit_fraction':limits/count,
            'measured_before_DC_removal_or_preview_normalization':True}
        assert limits==0,('Native APU mixer reached clipping limits',result)
        return result
    native._refined_native_audio_metrics=native_audio_metrics
    source=inspect.getsource(native.capture_score);tree=ast.parse(source)
    replacements=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='range' and len(node.args)==1:
            if isinstance(node.args[0],ast.Constant) and node.args[0].value==3300:
                node.args[0]=ast.Name(id='_refined_capture_frame_limit',ctx=ast.Load());replacements+=1
    assert replacements==1,'Review original native capture loop before adapting it'
    function=tree.body[0];audio_assignments=[i for i,node in enumerate(function.body)
        if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='audio'
            for target in node.targets)]
    assert len(audio_assignments)==1,'Review native audio normalization before instrumenting it'
    function.body[audio_assignments[0]:audio_assignments[0]]=ast.parse(
        'native_metrics = _refined_native_audio_metrics(np.concatenate(samples[start:end]))').body
    returned=[node for node in function.body if isinstance(node,ast.Return)]
    assert len(returned)==1 and isinstance(returned[0].value,ast.Dict)
    returned[0].value.keys.append(ast.Constant(value='native_audio_metrics'))
    returned[0].value.values.append(ast.Name(id='native_metrics',ctx=ast.Load()))
    exec(compile(ast.fix_missing_locations(tree),str(native.__file__),'exec'),native.__dict__)
    sym=load_symbols();scores=manifest();report={'tracks':{},
        'method':'Actual ROM APU capture through native PlayMusic API; isolated song ID diagnostic, not externally synthesized.',
        'source_matches_refinement':SOURCE.read_text()==refined(SOURCE.read_text()),
        'no_imported_Warcraft_recording':True,'title_music_not_selected_or_modified':True}
    assert report['source_matches_refinement']
    with tempfile.TemporaryDirectory(prefix='peon-refined-music-') as temporary:
        frozen=Path(temporary)/'frozen.gbc';shutil.copyfile(ROOT/'pokecrystal.gbc',frozen)
        report['rom_sha256']=hashlib.sha256(frozen.read_bytes()).hexdigest()
        for score in scores:
            native._refined_capture_frame_limit=max(3300,int(score['expected_phrase_frames']*2)+900)
            rom=Path(temporary)/(score['name'].lower()+'.gbc');shutil.copyfile(frozen,rom)
            capture=native.capture_score(rom,sym,score,score['native_music_id'])
            filename=score['name'].lower()+'_native.mp3'
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(OUT/capture['wav']),
                '-codec:a','libmp3lame','-b:a','128k',str(OUT/filename)],check=True)
            capture['mp3']=filename;capture['mp3_derived_from_native_apu_wav']=True
            report['tracks'][score['name']]=capture
            print('Native synchronized APU capture PASS:',score['name'],flush=True)
    assert len(report['tracks'])==7
    report['all_checks_passed']=True
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Seven native music captures passed',report['rom_sha256'],flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--validate',action='store_true');args=parser.parse_args()
    if args.validate:validate()
    else:generate()


if __name__=='__main__':main()
