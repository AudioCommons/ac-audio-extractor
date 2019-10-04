import sys
import os
import json
import math
import hashlib
import subprocess
from pathlib import Path
import numpy as np
import logging
import pyld
import rdflib
import essentia
essentia.log.infoActive = False
essentia.log.warningActive = False
import uuid
import ffmpeg
import warnings
warnings.filterwarnings("ignore")
from essentia.standard import MusicExtractor, FreesoundExtractor, MonoLoader, MonoWriter
from rdflib import Graph, URIRef, BNode, Literal, Namespace, plugin
from rdflib.serializer import Serializer
from rdflib.namespace import RDF
from argparse import ArgumentParser, ArgumentTypeError
import timbral_models

MORE_THAN_2_CHANNELS_EXCEPTION_MATCH_TEXT = 'Audio file has more than 2 channels'
METADATA_READER_EXCEPTION_MATCH_TEXT = 'pcmMetadata cannot read files which are neither "wav" nor "aiff"'

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

def convert_to_wav(audiofile, samplerate=44100):
    # Convert to mono WAV using ffmpeg
    output_filename = '/tmp/{0}-converted.wav'.format(hashlib.md5(audiofile.encode('utf-8')).hexdigest())
    if not os.path.exists(output_filename):
        logger.debug('{0}: converting to WAV'.format(audiofile))
        ffmpeg.input(audiofile).output(output_filename, ac=1).run(quiet=True, overwrite_output=True)            
    
    return output_filename

def run_freesound_extractor(audiofile):
    logger.debug('{0}: running Essentia\'s FreesoundExtractor'.format(audiofile))

    try:
        fs_pool, _ = FreesoundExtractor()(audiofile)
    except RuntimeError as e:
        if MORE_THAN_2_CHANNELS_EXCEPTION_MATCH_TEXT in str(e) or METADATA_READER_EXCEPTION_MATCH_TEXT in (str(e)):
            converted_audiofile = convert_to_wav(audiofile)
            fs_pool, _ = FreesoundExtractor()(converted_audiofile)
        else:
            raise e
    return fs_pool


def estimate_number_of_events(audiofile, audio, sample_rate=44100, region_energy_thr=0.5, silence_thr_scale=4.5, group_regions_ms=50):
    """
    Returns list of activity "onsets" for an audio signal based on its energy envelope. 
    This is more like "activity detecton" than "onset detection".
    """    
    logger.debug('{0}: estimating number of sound events'.format(audiofile))

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
    idx -= 1  # Avoid index out of bounds (0-index)
    regions = [(t[idx[i]], t[idx[i+1]], np.sum(envelope[idx[i]:idx[i+1]]**2)) for i in range(0, len(idx), 2)]  # Energy is a list of tuples like (start_time, end_time, energy)
    regions = [region for region in regions if region[2] > region_energy_thr] # Discard those below region_energy_thr
    
    # Group detected regions that happen close together
    regions = group_regions(regions, group_regions_ms)            

    return len(regions)  # Return number of sound events detected


_is_single_event_cache = None
def is_single_event(audiofile, max_duration=7):
    '''
    Estimate if the audio signal contains one single event using the 'estimate_number_of_events'
    function above. We store the result of 'estimate_number_of_events' in a global variable so
    it can be reused in the different calls of 'is_single_event'.
    '''
    global _is_single_event_cache
    if _is_single_event_cache is None:
        sample_rate = 44100
        try:
            audio_file = MonoLoader(filename=audiofile, sampleRate=sample_rate)
        except RuntimeError as e:
            if MORE_THAN_2_CHANNELS_EXCEPTION_MATCH_TEXT in str(e):
                converted_audiofile = convert_to_wav(audiofile)
                audio_file = MonoLoader(filename=converted_audiofile, sampleRate=sample_rate)
        audio = audio_file.compute()
        if len(audio)/sample_rate > max_duration:
            # If file is longer than max duration, we don't consider it to be single event
            _is_single_event_cache = False
        else:
            _is_single_event_cache = estimate_number_of_events(audiofile, audio, sample_rate=sample_rate) == 1
    return _is_single_event_cache


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
        return '%s%i' % (['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][note], octave - 1)

    def frequency_to_midi_note(frequency):
        return int(round(69 + (12 * math.log(frequency / 440.0)) / math.log(2)))
    
    pitch_median = float(fs_pool['lowlevel.pitch.median'])
    midi_note = frequency_to_midi_note(pitch_median)
    note_name = midi_note_to_note(midi_note)
    ac_descriptors["note_midi"] = midi_note
    ac_descriptors["note_name"] = note_name
    ac_descriptors["note_frequency"] = pitch_median
    ac_descriptors["note_confidence"] = float(fs_pool['lowlevel.pitch_instantaneous_confidence.median'])


def ac_timbral_models(audiofile, ac_descriptors):
    logger.debug('{0}: computing timbral models'.format(audiofile))

    converted_filename = convert_to_wav(audiofile)
    try:
        timbre = timbral_models.timbral_extractor(converted_filename, clip_output=True, verbose=False)
        timbre['reverb'] = timbre['reverb'] == 1
        ac_descriptors.update(timbre)
    except Exception as e:
        logger.debug('{0}: timbral models computation failed ("{1}")'.format(audiofile, e))


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
        MAX_SOUND_DURATION_FOR_TIMBRAL_MODELS = 30  # Avoid computing timbral models for sound longer than 30 seconds to avoid too many slow computations
        if ac_descriptors['duration'] < MAX_SOUND_DURATION_FOR_TIMBRAL_MODELS:
            ac_timbral_models(audiofile, ac_descriptors)
        else:
            logger.debug('{0}: skipping computation of timbral models as audio is longer than {1} seconds'.format(audiofile, MAX_SOUND_DURATION_FOR_TIMBRAL_MODELS))

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
    Audio Commons Audio Extractor (v3). Analyzes a given audio file and writes results to a JSON file.
    """)
    parser.add_argument('-v', '--verbose', help='if set, prints detailed info on screen during the analysis', action='store_const', const=True, default=False)
    parser.add_argument('-t', '--timbral-models', help='include descriptors computed from timbral models', action='store_const', const=True, default=False)
    parser.add_argument('-m', '--music-pieces', help='include descriptors designed for music pieces', action='store_const', const=True, default=False)
    parser.add_argument('-s', '--music-samples', help='include descriptors designed for music samples', action='store_const', const=True, default=False)
    parser.add_argument('-i', '--input', help='input audio file or input directory containing the audio files to analyze', required=True)
    parser.add_argument('-o', '--output', help='output analysis file or output directory where the analysis files will be saved', required=True)
    parser.add_argument('-f', '--format', help='format of the output analysis file ("json" or "jsonld", defaults to "jsonld")', default="jsonld")
    parser.add_argument('-u', '--uri', help='URI for the analyzed sound (only used if "jsonld" format is chosen)', default=None)
    
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO if not args.verbose else logging.DEBUG)

    # check if input and output arguments point to directories
    if os.path.isdir(args.input) and os.path.isdir(args.output):
        folder = args.input
        input_files = [x for x in Path(folder).iterdir() if x.is_file()]
        for input_file in input_files:
            output_file = os.path.join(args.output, '{}_analysis.json'.format(input_file.stem))
            analyze(str(input_file), output_file, args.timbral_models, args.music_pieces, args.music_samples, args.format, args.uri)

    # check if input argument points to a file
    elif os.path.isfile(args.input):
        analyze(args.input, args.output, args.timbral_models, args.music_pieces, args.music_samples, args.format, args.uri)

    else:
        raise ArgumentTypeError('Make sure input and output arguments are both files or folders')
