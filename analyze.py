import sys
import os
import json
import math
import numpy as np
import essentia
from argparse import ArgumentParser
from essentia.standard import FreesoundExtractor, YamlOutput, LoopBpmConfidence, PercivalBpmEstimator, EasyLoader, PitchContourSegmentation, PredominantPitchMelodia

ac_mapping = {
    "ac:duration": "metadata.audio_properties.length",
    "ac:lossless": "metadata.audio_properties.lossless",
    "ac:codec": "metadata.audio_properties.codec",
    "ac:bitrate": "metadata.audio_properties.bit_rate",
    "ac:samplerate": "metadata.audio_properties.sample_rate",
    "ac:channels": "metadata.audio_properties.number_channels",
    "ac:audio_md5": "metadata.audio_properties.md5_encoded",
    "ac:loudness": "lowlevel.loudness_ebu128.integrated",
    "ac:dynamic_range": "lowlevel.loudness_ebu128.loudness_range",
    "ac:temporal_centroid": "sfx.temporal_centroid",
    "ac:log_attack_time": "sfx.logattacktime",
}

def run_freesound_extractor(audiofile):
    # Disable Essentia logging and run extractor
    essentia.log.infoActive = False
    essentia.log.warningActive = False
    fs_pool, _ = FreesoundExtractor()(audiofile)
    return fs_pool


def ac_general_description(audiofile, fs_pool, ac_descriptors):
    # Add Audio Commons descriptors from the fs_pool
    for ac_name, essenia_name in ac_mapping.items():
        if fs_pool.containsKey(essenia_name):
            value = fs_pool[essenia_name]
            ac_descriptors[ac_name] = value
    ac_descriptors["ac:filesize"] = os.stat(audiofile).st_size


def ac_tempo_description(audiofile, fs_pool, ac_descriptors):
    tempo = int(round(fs_pool['rhythm.bpm']))
    tempo_confidence = fs_pool['rhythm.bpm_confidence'] / 5.0  # Normalize BPM confidence value
    if tempo_confidence < 0.0:
        tempo_confidence = 0.0
    elif tempo_confidence > 1.0:
        tempo_confidence = 1.0
    ac_descriptors["ac:tempo"] = tempo
    ac_descriptors["ac:tempo_confidence"] = tempo_confidence
    ac_descriptors["ac:tempo_loop"] = int(round(fs_pool['rhythm.bpm_loop']))
    ac_descriptors["ac:tempo_loop_confidence"] = fs_pool['rhythm.bpm_loop_confidence.mean']
    return ac_descriptors


def ac_key_description(audiofile, fs_pool, ac_descriptors):
    key = fs_pool['tonal.key_edma.key'] + " " + fs_pool['tonal.key_edma.scale']
    ac_descriptors["ac:tonality"] = key
    ac_descriptors["ac:tonality_confidence"] = fs_pool['tonal.key_edma.strength']
    

def ac_pitch_description(audiofile, fs_pool, ac_descriptors):

    def midi_note_to_note(midi_note):
        # Use convention MIDI value 69 = 440.0 Hz = A4
        note = midi_note % 12
        octave = midi_note / 12
        return '%s%i' % (['C', 'C#', 'D', 'D#', 'E', 'E#', 'F', 'F#', 'G', 'A', 'A#', 'B'][note], octave - 1)

    def frequency_to_midi_note(frequency):
        return int(69 + (12 * math.log(frequency / 440.0)) / math.log(2))

    pitch_median = float(fs_pool['lowlevel.pitch.median'])
    midi_note = frequency_to_midi_note(pitch_median)
    note_name = midi_note_to_note(midi_note)
    ac_descriptors["ac:note_midi"] = midi_note
    ac_descriptors["ac:note_name"] = note_name
    ac_descriptors["ac:note_frequency"] = pitch_median
    ac_descriptors["ac:note_confidence"] = float(fs_pool['lowlevel.pitch_instantaneous_confidence.median'])


def ac_timbral_models(audiofile, fs_pool, ac_descriptors):
    # TODO: update to latest version of timbral descriptors: https://github.com/AudioCommons/timbral_models/issues/5#issuecomment-376178206
    from timbral_models import timbral_brightness, timbral_depth, timbral_hardness, timbral_metallic, timbral_reverb, timbral_roughness
    for name, function in [
        ('perceptual.ac:brightness', timbral_brightness), 
        ('perceptual.ac:depth', timbral_depth), 
        ('perceptual.ac:hardness', timbral_hardness), 
        ('perceptual.ac:metallic', timbral_metallic), 
        ('perceptual.ac:reverb', timbral_reverb), 
        ('perceptual.ac:roughness', timbral_roughness)
    ]:
        try:
            value = function(audiofile)
        except Exception as e:
            print('{0} failed to compute'.format(str(function)))
            print(e)
            value = 0
        ac_descriptors[name] = value

def analyze(audiofile, jsonfile):

    # Get initial descriptors from Freesound Extractor
    fs_pool = run_freesound_extractor(audiofile)

    # Post-process descriptors to get AudioCommons descirptors and compute extra ones
    ac_descriptors = dict()
    ac_general_description(audiofile, fs_pool, ac_descriptors)
    ac_key_description(audiofile, fs_pool, ac_descriptors)
    ac_tempo_description(audiofile, fs_pool, ac_descriptors)
    ac_pitch_description(audiofile, fs_pool, ac_descriptors)
    #ac_timbral_models(audiofile, fs_pool, ac_descriptors)

    print('Done with analysis of {0}!'.format(audiofile))
    json.dump(ac_descriptors, open(jsonfile, 'w'))

    
if __name__ == '__main__':
    parser = ArgumentParser(description="""
    AudioCommons audio extractor. Analyzes a given audio file and writes results to a json file.
    """)

    parser.add_argument('-i', '--input', help='input audio file', required=True)
    parser.add_argument('-o', '--output', help='output json file', required=True)
    args = parser.parse_args()
    analyze(args.input, args.output)
    