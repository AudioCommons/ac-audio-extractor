from argparse import ArgumentParser
from essentia.standard import FreesoundExtractor, YamlOutput
from essentia import Pool
import sys, os, json, math
import numpy

ac_mapping = {
    
    "ac:duration": "metadata.audio_properties.length",
    "ac:lossless": "metadata.audio_properties.lossless",
    "ac:codec": "metadata.audio_properties.codec",
    "ac:bitrate": "metadata.audio_properties.bit_rate",
    "ac:samplerate": "metadata.audio_properties.sample_rate",
    "ac:channels": "metadata.audio_properties.number_channels",
    "ac:audio_md5": "metadata.audio_properties.md5_encoded",
    "ac:loudness": "lowlevel.loudness_ebu128.integrated",  # Other candidates: average_loudness, metadata.replay_gain
    "ac:dynamic_range": "lowlevel.loudness_ebu128.loudness_range",
    "ac:temporal_centroid": "sfx.temporal_centroid",
    "ac:log_attack_time": "sfx.logattacktime",
    
    # Not yet implemented descriptors
    # ac:format - not yet implemented, can be implemented in Essentia's AudioLoader
    # ac:bitdepth - not yet implemented, bitdepth does not make sense for some codecs (eg: mp3)
    # ac:instruments - not yet implemented, could borrow from 4.3
    # ac:chord - not yet implemented
    # ac:attack - not yet implemented
    # ac:decay - not yet implemented
    # ac:sustain - not yet implemented
    # ac:release - not yet implemented

    # Descriptors implemented in post-processing stage
    # ac:filesize - implemented below
    # ac:tonality - implemented below
    # ac:note - implemented below
    # ac:midi_note - implemented below
    # ac:tempo - implemented below
}


def midi_note_to_note(midi_note):
    # Use convention MIDI value 69 = 440.0 Hz = A4
    note = midi_note % 12
    octave = midi_note / 12
    return '%s%i' % (['C', 'C#', 'D', 'D#', 'E', 'E#', 'F', 'F#', 'G', 'A', 'A#', 'B'][note], octave - 1)

def frequency_to_midi_note(frequency):
    return int(69 + (12 * math.log(frequency / 440.0)) / math.log(2))

def analyze(audiofile, jsonfile):

    # Compute descriptors
    pool, _ = FreesoundExtractor()(audiofile)
   
    # Rename according to AudioCommons schema
    result_pool = Pool()

    for ac_name, essenia_name in ac_mapping.items():
        if pool.containsKey(essenia_name):
            value = pool[essenia_name]
            result_pool.set(ac_name, value)

    # Post-processing (add more descriptors)
    result_pool.set("ac:filesize", os.stat(audiofile).st_size)
    
    pitch_frequency = float(pool['lowlevel.pitch.median'])
    midi_note = frequency_to_midi_note(pitch_frequency)
    result_pool.set("ac:midi_note", midi_note)
    result_pool.set("ac:note", midi_note_to_note(midi_note))
    # TODO: no sense to compute note from pitch mean/median,
    # we should compute pitch contour and segment it instead.
    # This is not implemented in FreesoundExtractor yet.

    key = pool['tonal.key_krumhansl.key'] + " " + pool['tonal.key_krumhansl.scale']
    result_pool.set("ac:tonality", key)  # TODO: add tonal.key_krumhansl.strength

    tempo = int(round(pool['rhythm.bpm']))  # TODO: use percival's method and add confidence
    result_pool.set("ac:tempo", tempo)

    YamlOutput(filename=jsonfile, doubleCheck=True, format="json", writeVersion=False)(result_pool)

    return


if __name__ == '__main__':
    parser = ArgumentParser(description="""
    AudioCommons audio extractor. Analyzes a given audio file and writes results to a json file.
    """)

    parser.add_argument('-i', '--input', help='input audio file', required=True)
    parser.add_argument('-o', '--output', help='output json file', required=True)
    args = parser.parse_args()
    analyze(args.input, args.output)

