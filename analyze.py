import sys
import os
import json
import math
import numpy as np
import essentia
essentia.log.infoActive = False
essentia.log.warningActive = False
import logging
from argparse import ArgumentParser
from essentia.standard import MusicExtractor, FreesoundExtractor, YamlOutput, LoopBpmConfidence, PercivalBpmEstimator, EasyLoader, PitchContourSegmentation, PredominantPitchMelodia

logger = logging.getLogger()

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
    logger.debug('{0}: running Essentia\'s FreesoundExtractor'.format(audiofile))

    fs_pool, _ = FreesoundExtractor()(audiofile)
    return fs_pool


def ac_general_description(audiofile, fs_pool, ac_descriptors):
    logger.debug('{0}: adding basic AudioCommons descriptors'.format(audiofile))

    # Add Audio Commons descriptors from the fs_pool
    for ac_name, essenia_name in ac_mapping.items():
        if fs_pool.containsKey(essenia_name):
            value = fs_pool[essenia_name]
            ac_descriptors[ac_name] = value
    ac_descriptors["ac:filesize"] = os.stat(audiofile).st_size


def ac_tempo_description(audiofile, fs_pool, ac_descriptors):
    logger.debug('{0}: adding tempo descriptors'.format(audiofile))

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
    logger.debug('{0}: adding tonality descriptors'.format(audiofile))

    key = fs_pool['tonal.key_edma.key'] + " " + fs_pool['tonal.key_edma.scale']
    ac_descriptors["ac:tonality"] = key
    ac_descriptors["ac:tonality_confidence"] = fs_pool['tonal.key_edma.strength']
    

def ac_pitch_description(audiofile, fs_pool, ac_descriptors):
    logger.debug('{0}: adding pitch descriptors'.format(audiofile))

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


def ac_timbral_models(audiofile, ac_descriptors):
    logger.debug('{0}: computing timbral models'.format(audiofile))

    # TODO: update to latest version of timbral descriptors: https://github.com/AudioCommons/timbral_models/issues/5#issuecomment-376178206
    from timbral_models import timbral_brightness, timbral_depth, timbral_hardness, timbral_metallic, timbral_reverb, timbral_roughness
    for name, function in [
        ('ac:brightness', timbral_brightness), 
        ('ac:depth', timbral_depth), 
        ('ac:hardness', timbral_hardness), 
        ('ac:metallic', timbral_metallic), 
        ('ac:reverb', timbral_reverb), 
        ('ac:roughness', timbral_roughness)
    ]:
        try:
            value = function(audiofile)
        except Exception as e:
            logger.debug('{0}: analysis failed ({1}, "{2}")'.format(audiofile, function, e))
            value = 0
        ac_descriptors[name] = value


def ac_highlevel_music_description(audiofile, ac_descriptors):
    logger.debug('{0}: running Essentia\'s MusicExtractor'.format(audiofile))
    me_pool, _ = MusicExtractor(profile='music_extractor_profile.yaml')(audiofile)
    ac_descriptors["ac:genre"] = me_pool['highlevel.genre_test.value']
    ac_descriptors["ac:mood"] = me_pool['highlevel.mood_test.value']


def render_jsonld_output(ac_descriptors):
    # NOTE: this is a fake implementation that renders arbitrary JSON-LD data

    import rdflib,pyld
    from rdflib import Graph, URIRef, BNode, Literal, Namespace, plugin
    from rdflib.serializer import Serializer
    from rdflib.namespace import RDF, FOAF
    from pprint import pprint

    def dlfake(input):
        '''This is to avoid a bug in PyLD (should be easy to fix and avoid this hack really..)'''
        return {'contextUrl': None,'documentUrl': None,'document': input}

    g = Graph()
    AC = Namespace("http://audiocommons.org/vocab/")
    MO = Namespace("http://musicontology.com/")
    DC = Namespace("http://purl.org/dc/terms/")
    response_stats = BNode()
    g.add((response_stats, RDF.type, AC.AggregatedResponseStats))
    g.add((response_stats, AC.sent_timestamp, Literal("2016-12-22 16:58:55.128886")))
    g.add((response_stats, AC.current_timestamp, Literal("2016-12-22 16:58:55.158931")))
    g.add((response_stats, AC.n_received_responses, Literal(5)))  # Add 1 for simulated error response
    g.add((response_stats, AC.response_status, Literal("FI")))
    g.add((response_stats, AC.response_id, Literal("9097e3bb-2cc8-4f99-89ec-2dfbe1739e67")))
    g.add((response_stats, AC.collect_url, Literal("https://m.audiocommons.org/api/v1/collect/?rid=9097e3bb-2cc8-4f99-89ec-2dfbe1739e67")))

    context = {
        "rdf": str(RDF),  #  This might not be needed if we only use RDF.type
        "ac": str(AC),
        "mo": str(MO),
        "dc": str(DC),
    }

    '''
    frame = {
      #"@context": context,  # I think this is not needed
      "@type": str(AC.AggregatedResponse),
      str(AC.stats): {
        "@type": str(AC.AggregatedResponseStats),
      },
      str(AC.contents): {
        "@type": str(AC.IndividualResponse),
      },
      str(AC.errors): {
        "@type": str(AC.IndividualErrorResponse),
      },
      str(AC.warnings): {
        "@type": str(AC.IndividualWarningsResponse),
      },
    }
    '''
    frame = {"@type": str(AC.AggregatedResponse)}  # Apparently just by indicating the frame like this it already builds the desired output
    jsonld = g.serialize(format='json-ld', context=context).decode() # this gives us direct triple representation in a compact form
    jsonld = pyld.jsonld.frame(jsonld, frame, options={"documentLoader":dlfake}) # this "frames" the JSON-LD doc but it also expands it (writes out full URIs)
    jsonld = pyld.jsonld.compact(jsonld, context, options={"documentLoader":dlfake}) # so we need to compact it again (turn URIs into CURIEs)
    return jsonld


def analyze(audiofile, outfile, compute_timbral_models=False, compute_highlevel_music_descriptors=False, out_format="json"):
    logger.info('{0}: starting analysis'.format(audiofile))

    # Get initial descriptors from Freesound Extractor
    fs_pool = run_freesound_extractor(audiofile)

    # Post-process descriptors to get AudioCommons descirptors and compute extra ones
    ac_descriptors = dict()
    ac_general_description(audiofile, fs_pool, ac_descriptors)
    ac_key_description(audiofile, fs_pool, ac_descriptors)
    ac_tempo_description(audiofile, fs_pool, ac_descriptors)
    ac_pitch_description(audiofile, fs_pool, ac_descriptors)
    if compute_timbral_models:
        ac_timbral_models(audiofile, ac_descriptors)
    if compute_highlevel_music_descriptors:
        ac_highlevel_music_description(audiofile, ac_descriptors)
    
    if out_format == 'jsonld':
        # Convert output to JSON-LD
        output = render_jsonld_output(ac_descriptors)
    else:
        # By default (or in case of unknown format, use JSON)
        output = ac_descriptors

    logger.info('{0}: analysis finished'.format(audiofile))
    json.dump(output, open(outfile, 'w'), indent=4)

    
if __name__ == '__main__':
    parser = ArgumentParser(description="""
    AudioCommons audio extractor (v2). Analyzes a given audio file and writes results to a JSON file.
    """)
    parser.add_argument('-v', '--verbose', help='if set prints more info on screen', action='store_const', const=True, default=False)
    parser.add_argument('-t', '--timbral-models', help='if set, compute timbral models as well', action='store_const', const=True, default=False)
    parser.add_argument('-m', '--music-highlevel', help='if set, compute high-level music descriptors', action='store_const', const=True, default=False)
    parser.add_argument('-i', '--input', help='input audio file', required=True)
    parser.add_argument('-o', '--output', help='output analysis file', required=True)
    parser.add_argument('-f', '--format', help='format of the output analysis file ("json" or "jsonld", defaults to "jsonld")', default="json")
    
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO if not args.verbose else logging.DEBUG)

    analyze(args.input, args.output, args.timbral_models, args.music_highlevel, args.format)
    