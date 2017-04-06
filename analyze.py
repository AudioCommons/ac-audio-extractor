from argparse import ArgumentParser
from essentia.standard import MusicExtractor, FreesoundExtractor, YamlOutput
from essentia import Pool
import sys, os, json
import numpy

ac_mapping = {
    # Audio properties
    "ac:duration": "metadata.audio_properties.length",  # Other candidates: sfx.duration
    # TODO "ac:format" can be implemented in Essentia's AudioLoader, but only if we really need it!
    "ac:lossless": "metadata.audio_properties.lossless",
    "ac:codec": "metadata.audio_properties.codec",
    "ac:bitrate": "metadata.audio_properties.bit_rate",
    #"ac:bitdepth" # TODO bitdepth does not have sense for some codecs (eg: mp3)
    "ac:samplerate": "metadata.audio_properties.sample_rate",
    "ac:channels": "metadata.audio_properties.number_channels",
    "ac:audio_md5": "metadata.md5_encoded",
    #"ac:filesize", # compute in post-processing

    # Musical properties
    #"ac:genres",
    #"ac:mood",
    #"ac:tonality": # compute in post-processing
    "ac:tempo": "rhythm.bpm",  # TODO add Percival BPM algo?
    #"ac:note": #lowlevel.pitch.mean, lowlevel.pitch_instantaneous_confidence.mean (to check)
    #"ac:midi_note":

    # TODO: no sense to compute note from pitch mean,
    # we should compute pitch contour and segment it instead.
    # This is not implemented in FreesoundExtractor yet.

    # Timbral descriptors
    "ac:dissonance": "lowlevel.dissonance.mean",
    #"ac:brightness": #IoSR brightness
    "ac:tristimulus": "sfx.tristimulus.mean",
    "ac:odd_to_even_harmonic_ratio": "sfx.oddtoevenharmonicenergyratio.mean",

    # Dynamics
    "ac:loudness": "loudness_ebu128.integrated",  # Other candidates: average_loudness, metadata.replay_gain
    "ac:dynamic_range": "loudness_ebu128.loudness_range",
    "ac_temporal_centroid": "sfx.temporal_centroid.mean",
    "ac:log_attack_time": "sfx.logattacktime.mean",

    # Lower-level audio descriptors
    "ac:spectral_centroid": "lowlevel.spectral_centroid.mean",
    "ac:mfcc": "lowlevel.mfcc.mean",
    "ac:hpcp": "tonal.hpcp.mean"
}


def analyze(audiofile, jsonfile, extractor):

    # Compute descriptors
    if extractor == "music":
        pool, poolFrames = MusicExtractor()(audiofile)
    elif extractor == "sound":
        pool, poolFrames = FreesoundExtractor()(audiofile)
    else:
        print "Wrong extractor type:", extractor
        sys.exit(1)

    # Rename according to AudioCommons schema
    # Using a single mapping for both music and sound extractors
    #result = {}
    result_pool = Pool()

    for ac_name, essenia_name in ac_mapping.items():
        if pool.containsKey(essenia_name):
            value = pool[essenia_name]
            #if type(value) is numpy.ndarray:
            #    value = value.tolist()
            #result[ac_name] = value
            result_pool.set(ac_name, value)

    #with open(jsonfile, 'w') as f:
    #    json.dump(result, f)

    # Post-processing
    result_pool.set("ac:filesize", os.stat(audiofile).st_size)

    key = pool['tonal.key_krumhansl.key'] + " " + pool['tonal.key_krumhansl.scale']
    result_pool.set("ac:tonality", key)  # TODO: add tonal.key_krumhansl.strength

    YamlOutput(filename=jsonfile, doubleCheck=True, format="json", writeVersion=False)(result_pool)

    return


if __name__ == '__main__':
    parser = ArgumentParser(description="""
AudioCommons audio extractor. Analyzes a given audio file and writes results to a json file.
""")

    parser.add_argument('-i', '--input', help='input audio file', required=True)
    parser.add_argument('-o', '--output', help='output json file', required=True)
    parser.add_argument('-t', '--type', help='type of extractor [music|sound]', required=True)
    # TODO: frames needed?
    #parser.add_argument('--frames', help='store frames data', action='store_true', required=False)

    args = parser.parse_args()

    analyze(args.input, args.output, args.type)
