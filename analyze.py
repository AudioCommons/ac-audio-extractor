import sys
import os
import json
import math
import numpy as np
import essentia
essentia.log.infoActive = False
essentia.log.warningActive = False
import logging
import pyld
import rdflib
from rdflib import Graph, URIRef, BNode, Literal, Namespace, plugin
from rdflib.serializer import Serializer
from rdflib.namespace import RDF
from argparse import ArgumentParser
from essentia.standard import MusicExtractor, FreesoundExtractor, YamlOutput, LoopBpmConfidence, PercivalBpmEstimator, EasyLoader, PitchContourSegmentation, PredominantPitchMelodia

logger = logging.getLogger()

# TODO: add correct URLs here
AC = Namespace("http://audiocommons.org/vocab/")
AFO = Namespace("http://motools.sourceforge.net/doc/audio_features.html#")
AFV = Namespace("http://motools.sourceforge.net/doc/?#")
EBU = Namespace("https://www.ebu.ch/metadata/ontologies/ebucore/index.html#")

ac_mapping = {
    "duration": "metadata.audio_properties.length",
    "lossless": "metadata.audio_properties.lossless",
    "codec": "metadata.audio_properties.codec",
    "bitrate": "metadata.audio_properties.bit_rate",
    "samplerate": "metadata.audio_properties.sample_rate",
    "channels": "metadata.audio_properties.number_channels",
    "audio_md5": "metadata.audio_properties.md5_encoded",
    "loudness": "lowlevel.loudness_ebu128.integrated",
    "dynamic_range": "lowlevel.loudness_ebu128.loudness_range",
    "temporal_centroid": "sfx.temporal_centroid",
    "log_attack_time": "sfx.logattacktime",
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
    ac_descriptors["filesize"] = os.stat(audiofile).st_size


def ac_tempo_description(audiofile, fs_pool, ac_descriptors):
    logger.debug('{0}: adding tempo descriptors'.format(audiofile))

    tempo = int(round(fs_pool['rhythm.bpm']))
    tempo_confidence = fs_pool['rhythm.bpm_confidence'] / 5.0  # Normalize BPM confidence value
    if tempo_confidence < 0.0:
        tempo_confidence = 0.0
    elif tempo_confidence > 1.0:
        tempo_confidence = 1.0
    ac_descriptors["tempo"] = tempo
    ac_descriptors["tempo_confidence"] = tempo_confidence
    ac_descriptors["tempo_loop"] = int(round(fs_pool['rhythm.bpm_loop']))
    ac_descriptors["tempo_loop_confidence"] = fs_pool['rhythm.bpm_loop_confidence.mean']
    return ac_descriptors


def ac_key_description(audiofile, fs_pool, ac_descriptors):
    logger.debug('{0}: adding tonality descriptors'.format(audiofile))

    key = fs_pool['tonal.key_edma.key'] + " " + fs_pool['tonal.key_edma.scale']
    ac_descriptors["tonality"] = key
    ac_descriptors["tonality_confidence"] = fs_pool['tonal.key_edma.strength']
    

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
    ac_descriptors["note_midi"] = midi_note
    ac_descriptors["note_name"] = note_name
    ac_descriptors["note_frequency"] = pitch_median
    ac_descriptors["note_confidence"] = float(fs_pool['lowlevel.pitch_instantaneous_confidence.median'])


def ac_timbral_models(audiofile, ac_descriptors):
    logger.debug('{0}: computing timbral models'.format(audiofile))

    # TODO: update to latest version of timbral descriptors: https://github.com/AudioCommons/timbral_models/issues/5#issuecomment-376178206
    from timbral_models import timbral_brightness, timbral_depth, timbral_hardness, timbral_metallic, timbral_reverb, timbral_roughness
    for name, function in [
        ('brightness', timbral_brightness), 
        ('depth', timbral_depth), 
        ('hardness', timbral_hardness), 
        ('metallic', timbral_metallic), 
        ('reverb', timbral_reverb), 
        ('roughness', timbral_roughness)
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
    ac_descriptors["genre"] = me_pool['highlevel.genre_test.value']
    ac_descriptors["mood"] = me_pool['highlevel.mood_test.value']


def build_graph(ac_descriptors, uri=None):

    g = Graph()
    
    if uri is None:
        analysisOutput = BNode()
    else:
        analysisOutput = URIRef(uri)
    g.add((analysisOutput, RDF['type'], AC['AnalysisOutput']))
    g.add((analysisOutput, AC['duration'], Literal(ac_descriptors['duration'])))

    audioFile = BNode()
    g.add((audioFile, RDF['type'], AC['AudioFile']))
    g.add((audioFile, EBU['bitrate'], Literal(ac_descriptors['bitrate'])))
    g.add((audioFile, EBU['filesize'], Literal(ac_descriptors['filesize'])))
    g.add((audioFile, EBU['hasCodec'], Literal(ac_descriptors['codec'])))
    g.add((analysisOutput, AC['availableAs'], audioFile))

    digitalSignal = BNode()
    g.add((digitalSignal, RDF['type'], AC['DigitalSignal']))
    g.add((digitalSignal, AC['samplerate'], Literal(ac_descriptors['samplerate'])))
    g.add((digitalSignal, AC['channels'], Literal(int(ac_descriptors['channels']))))
    g.add((digitalSignal, AC['audio_md5'], Literal(ac_descriptors['audio_md5'])))
    g.add((digitalSignal, AC['lossless'], Literal(True if ac_descriptors['lossless'] else False)))
    for type_name, value_field, confidence_field in [
        ('Tempo', 'tempo', 'tempo_confidence'),
        ('Key', 'tonality', 'tonality_confidence'),
        ('Loudness', 'loudness', None),
        ('TemporalCentroid', 'temporal_centroid', None),
        ('LogAttackTime', 'log_attack_time', None),
        ('MIDINote', 'note_midi', 'note_confidence'),
        ('Note', 'note_name', 'note_confidence'),
        ('Pitch', 'note_frequency', 'note_confidence'),
    ]:
        if value_field in ac_descriptors:
            # Only include descriptors if present in analysis
            signalFeature = BNode()
            g.add((signalFeature, RDF['type'], AFV[type_name]))
            g.add((signalFeature, AFO['value'], Literal(ac_descriptors[value_field])))
            if confidence_field is not None:
                g.add((signalFeature, AFO['confidence'], Literal(ac_descriptors[confidence_field])))
            g.add((digitalSignal, AC['signal_feature'], signalFeature))
    g.add((analysisOutput, AC['publicationOf'], digitalSignal))

    return g


def render_jsonld_output(g):

    def dlfake(input):
        '''This is to avoid a bug in PyLD (should be easy to fix and avoid this hack really..)'''
        return {'contextUrl': None,'documentUrl': None,'document': input}

    context = {
        "rdf": str(RDF),
        "ac": str(AC),
        "afo": str(AFO),
        "afv": str(AFV),
        "ebucore": str(EBU),
    }
    frame = {"@type": str(AC['AnalysisOutput'])}  # Apparently just by indicating the frame like this it already builds the desired output
    jsonld = g.serialize(format='json-ld', context=context).decode() # this gives us direct triple representation in a compact form
    jsonld = pyld.jsonld.frame(jsonld, frame, options={"documentLoader":dlfake}) # this "frames" the JSON-LD doc but it also expands it (writes out full URIs)
    jsonld = pyld.jsonld.compact(jsonld, context, options={"documentLoader":dlfake}) # so we need to compact it again (turn URIs into CURIEs)
    return jsonld

def analyze(audiofile, outfile, compute_timbral_models=False, compute_highlevel_music_descriptors=False, out_format="json", uri=None):
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
        graph = build_graph(ac_descriptors, uri=uri)
        output = render_jsonld_output(graph)
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
    parser.add_argument('-u', '--uri', help='URI for the analyzed sound (only used if "jsonld" format is chosen)', default=None)
    
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO if not args.verbose else logging.DEBUG)

    analyze(args.input, args.output, args.timbral_models, args.music_highlevel, args.format, args.uri)
    