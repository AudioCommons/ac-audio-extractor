import sys
import os
import json
import math
import subprocess
import numpy as np
import logging
import pyld
import rdflib
import essentia
essentia.log.infoActive = False
essentia.log.warningActive = False
from essentia.standard import MusicExtractor, FreesoundExtractor, MonoLoader, MonoWriter
from rdflib import Graph, URIRef, BNode, Literal, Namespace, plugin
from rdflib.serializer import Serializer
from rdflib.namespace import RDF
from argparse import ArgumentParser
from timbral_models import timbral_brightness, timbral_depth, timbral_hardness,  timbral_roughness, timbral_booming, timbral_warmth, timbral_sharpness

logger = logging.getLogger()

AC = Namespace("https://w3id.org/ac-ontology/aco#")
AFO = Namespace("https://w3id.org/afo/onto/1.1#")
AFV = Namespace("https://w3id.org/afo/vocab/1.1#")
EBU = Namespace("http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#")
NFO = Namespace("http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#")

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


def estimate_number_of_events(audiofile, region_energy_thr=2, silence_thr_scale=4, group_regions_ms=100):
    """
    Returns list of activity "onsets" for an audio signal based on its energy envelope. 
    This is more like "activity detecton" than "onset detection".
    """    

    def group_regions(regions, group_regions_ms):
        """
        Group together regions which are very close in time (i.e. the end of a region is very close to the start of the following).
        """
        if len(regions) <= 1:
            grouped_regions = regions[:]  # Don't do anything if only one region or no regions at all
        else:
            # Iterate over regions and mark which regions should be grouped with the following regions
            to_group = []
            for count, ((at0, at1, a_energy), (bt0, bt1, b_energy)) in enumerate(zip(regions[:-1], regions[1:])):
                if bt0 - at1 < group_regions_ms / 1000:
                    to_group.append(1)
                else:
                    to_group.append(0)
            to_group.append(0)  # Add 0 for the last one which will never be grouped with next (there is no "next region")

            # Now generate the grouped list of regions based on the marked ones in 'to_group'
            grouped_regions = []
            i = 0
            while i < len(to_group):
                current_group_start = None
                current_group_end = None
                x = to_group[i]
                if x == 1 and current_group_start is None:
                    # Start current grouping
                    current_group_start = i
                    while x == 1:
                        i += 1
                        x = to_group[i]
                        current_group_end = i
                    grouped_regions.append( (regions[current_group_start][0], regions[current_group_end][1], sum([z for x,y,z in regions[current_group_start:current_group_end+1]])))
                    current_group_start = None
                    current_group_end = None
                else:
                    grouped_regions.append(regions[i])
                i += 1
        return grouped_regions

    # Load audio file
    sample_rate = 44100
    audio_file = MonoLoader(filename=audiofile, sampleRate=sample_rate)
    audio = audio_file.compute()
    t = np.linspace(0, len(audio)/sample_rate, num=len(audio))
    
    # Compute envelope and average signal energy
    env_algo = essentia.standard.Envelope(
        attackTime = 15,
        releaseTime = 50,
    )
    envelope = env_algo(audio)
    average_signal_energy = np.sum(np.array(envelope)**2)/len(envelope)
    silence_thr = average_signal_energy  * silence_thr_scale
    
    # Get energy regions above threshold
    # Implementation based on https://stackoverflow.com/questions/43258896/extract-subarrays-of-numpy-array-whose-values-are-above-a-threshold
    mask = np.concatenate(([False], envelope > silence_thr, [False] ))
    idx = np.flatnonzero(mask[1:] != mask[:-1])
    regions = [(t[idx[i]], t[idx[i+1]], np.sum(envelope[idx[i]:idx[i+1]]**2)) for i in range(0,len(idx),2)]  # Energy is a list of tuples like (start_time, end_time, energy)
    regions = [region for region in regions if region[2] > region_energy_thr] # Discard those below region_energy_thr
    
    # Group detected regions that happen close together
    regions = group_regions(regions, group_regions_ms)            

    return len(regions)  # Return number of sound events detected


def is_single_event(audiofile):
    return estimate_number_of_events(audiofile) == 1


def ac_general_description(audiofile, fs_pool, ac_descriptors):
    logger.debug('{0}: adding basic AudioCommons descriptors'.format(audiofile))

    # Add Audio Commons descriptors from the fs_pool
    for ac_name, essenia_name in ac_mapping.items():
        if fs_pool.containsKey(essenia_name):
            value = fs_pool[essenia_name]
            ac_descriptors[ac_name] = value
    ac_descriptors["filesize"] = os.stat(audiofile).st_size
    ac_descriptors["single_event"] = is_single_event(audiofile)


def ac_rhythm_description(audiofile, fs_pool, ac_descriptors):
    logger.debug('{0}: adding rhythm descriptors'.format(audiofile))
    
    IS_LOOP_CONFIDENCE_THRESHOLD = 0.95
    is_loop = fs_pool['rhythm.bpm_loop_confidence.mean'] > IS_LOOP_CONFIDENCE_THRESHOLD
    ac_descriptors["loop"] = is_loop

    if is_loop:
        ac_descriptors["tempo"] = int(round(fs_pool['rhythm.bpm_loop']))
        ac_descriptors["tempo_confidence"] = fs_pool['rhythm.bpm_loop_confidence.mean']
    else:
        ac_descriptors["tempo"] = int(round(fs_pool['rhythm.bpm']))
        tempo_confidence = fs_pool['rhythm.bpm_confidence'] / 5.0  # Normalize BPM confidence value to be in range [0, 1]
        ac_descriptors["tempo_confidence"] = np.clip(tempo_confidence, 0.0, 1.0)

    return ac_descriptors


def ac_tonality_description(audiofile, fs_pool, ac_descriptors):
    logger.debug('{0}: adding tonality descriptors'.format(audiofile))

    key = fs_pool['tonal.key.key'] + " " + fs_pool['tonal.key.scale']
    ac_descriptors["tonality"] = key
    ac_descriptors["tonality_confidence"] = fs_pool['tonal.key.strength']
    

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

    # As a post-processing step, check if 'single_event' descriptor has been computed. If that is the
    # case and the estimate is that the sound has more than one event, set note confidence to 0.
    if 'single_event' in ac_descriptors and not ac_descriptors['single_event']:
        ac_descriptors["note_confidence"] = 0.0


def ac_timbral_models(audiofile, ac_descriptors):
    logger.debug('{0}: computing timbral models'.format(audiofile))

    def convert_to_wav(audiofile, samplerate=44100):
        logger.debug('{0}: converting to WAV'.format(audiofile))

        # Convert to WAV using Essentia so that timbral models always read WAV file
        output_filename = '{0}-converted.wav'.format(audiofile)
        audio = MonoLoader(filename=audiofile, sampleRate=samplerate)()
        MonoWriter(filename=output_filename, format='wav', sampleRate=samplerate)(audio)
        return output_filename

    converted_filename = convert_to_wav(audiofile)  # Convert file to PCM for running timbral models
    for name, function in [
        ('brightness', timbral_brightness), 
        ('depth', timbral_depth), 
        ('hardness', timbral_hardness), 
        ('roughness', timbral_roughness),
        ('booming', timbral_booming), 
        ('warmth', timbral_warmth), 
        ('sharpness', timbral_sharpness)
    ]:
        try:
            value = function(converted_filename)
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

    audioFile = BNode()

    if uri is None:
        availableItemOf = BNode()
    else:
        availableItemOf = URIRef(uri)
    g.add((availableItemOf, RDF['type'], AC['AudioClip']))
    g.add((audioFile, AC['availableItemOf'], availableItemOf))

    g.add((audioFile, RDF['type'], AC['AudioFile'])) 
    g.add((audioFile, AC['singalSamplerate'], Literal(ac_descriptors['samplerate'])))
    g.add((audioFile, AC['signalChannels'], Literal(int(ac_descriptors['channels']))))
    g.add((audioFile, AC['signalDuration'], Literal(ac_descriptors['duration'])))
    g.add((audioFile, EBU['bitrate'], Literal(ac_descriptors['bitrate'])))
    g.add((audioFile, EBU['filesize'], Literal(ac_descriptors['filesize'])))  
    g.add((audioFile, AC['audioMd5'], Literal(ac_descriptors['audio_md5'])))
    #g.add((audioFile, AC['singleEvent'], Literal(ac_descriptors['single_event'])))

    audioCodec = BNode()
    g.add((audioCodec, RDF['type'], EBU['AudioCodec']))
    g.add((audioCodec, EBU['codecId'], Literal(ac_descriptors['codec'])))  
    g.add((audioFile, EBU['hasCodec'], audioCodec))

    if ac_descriptors['lossless']:
        g.add((audioFile, NFO['compressionType'], Literal('nfo:losslessCompressionType')))
    else:
        g.add((audioFile, NFO['compressionType'], Literal('nfo:lossyCompressionType')))

    
    for type_name, value_field, confidence_field in [
        ('Tempo', 'tempo', 'tempo_confidence'),
        ('Loop', 'loop', None),
        ('Key', 'tonality', 'tonality_confidence'),
        ('Loudness', 'loudness', None),
        ('TemporalCentroid', 'temporal_centroid', None),
        ('LogAttackTime', 'log_attack_time', None),
        ('MIDINote', 'note_midi', 'note_confidence'),
        ('Note', 'note_name', 'note_confidence'),
        ('Pitch', 'note_frequency', 'note_confidence'),
        #('TimbreBrightness', 'brightness', 'note_confidence'),
        #('TimbreDepth', 'depth', None),
        #('TimbreHardness', 'hardness', None),
        #('TimbreMetallic', 'metallic', None),
        #('TimbreReverb', 'reverb', None),
        #('TimbreRoughness', 'roughness', None),
        #('TimbreBoominess', 'booming', None),
        #('TimbreWarmth', 'warmth', None),
        #('TimbreSharpness', 'sharpness', None),
    ]:
        if value_field in ac_descriptors:
            # Only include descriptors if present in analysis
            signalFeature = BNode()
            g.add((signalFeature, RDF['type'], AFV[type_name]))
            g.add((signalFeature, AFO['value'], Literal(ac_descriptors[value_field])))
            if confidence_field is not None:
                g.add((signalFeature, AFO['confidence'], Literal(ac_descriptors[confidence_field])))
            g.add((audioFile, AC['signalAudioFeature'], signalFeature))
    
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
        "nfo": str(NFO),
    }
    frame = {"@type": str(AC['AudioFile'])}  # Apparently just by indicating the frame like this it already builds the desired output
    jsonld = g.serialize(format='json-ld', context=context).decode() # this gives us direct triple representation in a compact form
    jsonld = pyld.jsonld.frame(jsonld, frame, options={"documentLoader":dlfake}) # this "frames" the JSON-LD doc but it also expands it (writes out full URIs)
    jsonld = pyld.jsonld.compact(jsonld, context, options={"documentLoader":dlfake}) # so we need to compact it again (turn URIs into CURIEs)
    return jsonld

def analyze(audiofile, outfile, compute_timbral_models=False, compute_descriptors_music_pieces=False, compute_descriptors_music_samples=False, out_format="json", uri=None):
    logger.info('{0}: starting analysis'.format(audiofile))

    # Get initial descriptors from Freesound Extractor
    fs_pool = run_freesound_extractor(audiofile)

    # Post-process descriptors to get AudioCommons descirptors and compute extra ones
    ac_descriptors = dict()
    ac_general_description(audiofile, fs_pool, ac_descriptors)
    if compute_descriptors_music_pieces or compute_descriptors_music_samples:
        ac_tonality_description(audiofile, fs_pool, ac_descriptors)
        ac_rhythm_description(audiofile, fs_pool, ac_descriptors)
    if compute_descriptors_music_samples:
        ac_pitch_description(audiofile, fs_pool, ac_descriptors)
    if compute_timbral_models:
        ac_timbral_models(audiofile, ac_descriptors)
    if compute_descriptors_music_pieces:
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
    Audio Commons Audio Extractor (v2). Analyzes a given audio file and writes results to a JSON file.
    """)
    parser.add_argument('-v', '--verbose', help='if set, prints detailed info on screen during the analysis', action='store_const', const=True, default=False)
    parser.add_argument('-t', '--timbral-models', help='include descriptors computed from timbral models', action='store_const', const=True, default=False)
    parser.add_argument('-m', '--music-pieces', help='include descriptors designed for music pieces', action='store_const', const=True, default=False)
    parser.add_argument('-s', '--music-samples', help='include descriptors designed for music samples', action='store_const', const=True, default=False)
    parser.add_argument('-i', '--input', help='input audio file', required=True)
    parser.add_argument('-o', '--output', help='output analysis file', required=True)
    parser.add_argument('-f', '--format', help='format of the output analysis file ("json" or "jsonld", defaults to "jsonld")', default="jsonld")
    parser.add_argument('-u', '--uri', help='URI for the analyzed sound (only used if "jsonld" format is chosen)', default=None)
    
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO if not args.verbose else logging.DEBUG)

    analyze(args.input, args.output, args.timbral_models, args.music_pieces, args.music_samples, args.format, args.uri)
    
