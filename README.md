# AudioCommons audio extractor

This tool incorporates algorithms for extracting music properties for music samples and music pieces, and other high-level non-musical properties for other kinds of sounds. 

To facilitate its usage, the tool has been *dockerized* and should run successfully in any platform with [Docker](https://www.docker.com/) installed.


## Running the audio extractor

You can easily analyze sound from an audio file in the current directory using the following command:

```
docker run -it --rm -v `pwd`:/tmp mtgupf/ac-audio-extractor:v2 -i /tmp/audio.wav -o /tmp/analysis.json -smt
```

The example above mounts the current directory ``pwd`` in the virtual `tmp` directory inside Docker. The output file `audio.json` is also written in `tmp`, and therefore appears in the current directory. You can also mount different volumes and specify paths for input audio and analysis output like this (for more information, checkout [Docker volumes](https://docs.docker.com/storage/volumes/)):

```
docker run -it --rm -v /local/path/to/your/audio/file.wav:/audio.wav -v /local/path/to/output_directory/:/outdir mtgupf/ac-audio-extractor:v2 -i /audio.wav -o /outdir/analysis.json  -smt
```

Run help command to learn about available options:

```
docker run -it --rm -v `pwd`:/tmp mtgupf/ac-audio-extractor:v2 --help

uusage: analyze.py [-h] [-v] [-t] [-m] [-s] -i INPUT -o OUTPUT [-f FORMAT]
                  [-u URI]

AudioCommons audio extractor (v2). Analyzes a given audio file and writes
results to a JSON file.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         if set, prints detailed info on screen during the
                        analysis
  -t, --timbral-models  include descriptors computed from timbral models
  -m, --music-pieces    include descriptors designed for music pieces
  -s, --music-samples   include descriptors designed for music samples
  -i INPUT, --input INPUT
                        input audio file
  -o OUTPUT, --output OUTPUT
                        output analysis file
  -f FORMAT, --format FORMAT
                        format of the output analysis file ("json" or
                        "jsonld", defaults to "jsonld")
  -u URI, --uri URI     URI for the analyzed sound (only used if "jsonld"
                        format is chosen)
```


## Output formats

The Audio Commons audio extractor can write the analysis output to a **JSON** file with a flat hierarchy, or generate a structured output in **JSON-LD** ([JSON for linked data](https://json-ld.org/)). You can choose the format to use with the `--format` argument. By default `format` is set to `jsonld`. When using JSON-LD, you can optionally specify a URI for the analyzed sound resource so that the triples added in the graph are referenced to that URI. For that, use the `--uri` argument. Bellow are example outputs for the JSON and JSON-LD formats.


### JSON output example
```
{
    "duration": 6.0,
    "lossless": 1.0,
    "codec": "pcm_s16le",
    "bitrate": 705600.0,
    "samplerate": 44100.0,
    "channels": 1.0,
    "audio_md5": "8da67c9c2acbd13998c9002aa0f60466",
    "loudness": -28.207069396972656,
    "dynamic_range": 0.6650657653808594,
    "temporal_centroid": 0.5078766345977783,
    "log_attack_time": 0.30115795135498047,
    "filesize": 529278,
    "single_event": false,
    "tonality": "G# minor",
    "tonality_confidence": 0.2868785858154297,
    "is_loop": true,
    "tempo": 120,
    "tempo_confidence": 1.0,
    "note_midi": 74,
    "note_name": "D5",
    "note_frequency": 592.681884765625,
    "note_confidence": 0.0,
    "brightness": 50.56954356039029,
    "depth": 13.000903137777897,
    "hardness": 0,
    "metallic": 0.4906048209174263,
    "reverb": 0,
    "roughness": 0.7237051954207928,
    "genre": "Genre B",
    "mood": "Mood B"
}
```


### JSON-LD output example

```
{
    "@context": {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "ac": "https://w3id.org/ac-ontology/aco#",
        "afo": "https://w3id.org/afo/onto/1.1#",
        "afv": "https://w3id.org/afo/vocab/1.1#",
        "ebucore": "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#"
    },
    "@type": "ac:AnalysisOutput",
    "ac:availableAs": {
        "@type": "ac:AudioFile",
        "ebucore:bitrate": 705600.0,
        "ebucore:filesize": 529278,
        "ebucore:hasCodec": "pcm_s16le"
    },
    "ac:duration": 6.0,
    "ac:publicationOf": {
        "@type": "ac:DigitalSignal",
        "ac:audio_md5": "8da67c9c2acbd13998c9002aa0f60466",
        "ac:channels": 1,
        "ac:lossless": true,
        "ac:samplerate": 44100.0,
        "ac:signal_feature": [
            {
                "@type": "afv:Key",
                "afo:confidence": 0.2868785858154297,
                "afo:value": "G# minor"
            },
            {
                "@type": "afv:TimbreBrightness",
                "afo:confidence": 0.0,
                "afo:value": 50.56954356039029
            },
            {
                "@type": "afv:TimbreRoughness",
                "afo:value": 0.7237051954207928
            },
            {
                "@type": "afv:TimbreHardness",
                "afo:value": 0
            },
            {
                "@type": "afv:LogAttackTime",
                "afo:value": 0.30115795135498047
            },
            {
                "@type": "afv:MIDINote",
                "afo:confidence": 0.0,
                "afo:value": 74
            },
            {
                "@type": "afv:Loudness",
                "afo:value": -28.207069396972656
            },
            {
                "@type": "afv:TimbreMetallic",
                "afo:value": 0.4906048209174263
            },
            {
                "@type": "afv:TimbreReverb",
                "afo:value": 0
            },
            {
                "@type": "afv:IsLoop",
                "afo:value": true
            },
            {
                "@type": "afv:Note",
                "afo:confidence": 0.0,
                "afo:value": "D5"
            },
            {
                "@type": "afv:Pitch",
                "afo:confidence": 0.0,
                "afo:value": 592.681884765625
            },
            {
                "@type": "afv:TemporalCentroid",
                "afo:value": 0.5078766345977783
            },
            {
                "@type": "afv:Tempo",
                "afo:confidence": 1.0,
                "afo:value": 120
            },
            {
                "@type": "afv:TimbreDepth",
                "afo:value": 13.000903137777897
            }
        ]
    },
    "ac:single_event": false
}
```


## Build the docker image locally

There is no need to build the Docker image locally because Docker will automatically retrieve the image from the remote [Docker Hub](https://hub.docker.com). However, if you need a custom version of the image you can also build it locally using the instructions in the `Dockerfile` of this repository. Use the following command:

```
docker build -t mtgupf/ac-audio-extractor:v2 .
```

### Pushing the image to MTG's Docker Hub

The pre-built image for the Audio Commons annotations tools is hosted in [MTG](http://mtg.upf.edu/)'s Docker Hub account. To push a new version of the image use the following command (and change the tag if needed):

```
docker push mtgupf/ac-audio-extractor:v2
```

This is only meant for the admins/maintainers of the image. You'll need a Docker account with wrtie access to MTG's Docker Hub space.


## Included descriptors (TODO: update that section)

### Audio file properties
- ```duration```: duration of audio file (sec.)
- ```lossless```: whether audio file is in lossless codec (True or False)
- ```codec```: audio codec
- ```bitrate```: bit rate
- ```samplerate```: sample rate
- ```channels```: number of audio channels
- ```audio_md5```: the MD5 checksum of raw undecoded audio payload. It can be used as a unique identifier of audio content

### Music pieces
- ```ac:tempo```: BPM value estimated by beat tracking algorithm by [Degara et al., 2012](http://essentia.upf.edu/documentation/reference/std_RhythmExtractor2013.html).
- ```ac:tonality```: [key and scale](http://essentia.upf.edu/documentation/reference/std_Key.html) estimate based on HPCP descriptor and "Krumhansl" key detection profile which should work generally fine for pop music. 
- ```ac:note```: Pitch note name based on median of estimated fundamental frequency.
- ```ac:mini_note```: Estimated midi note number pitch note.

### Dynamics
- ```ac:loudness```: the integrated (overall) loudness (LUFS) measured using the [EBU R128 standard](http://essentia.upf.edu/documentation/reference/std_LoudnessEBUR128.html).
- ```ac:dynamic_range```: loudness range (dB, LU) measured using the [EBU R128 standard](http://essentia.upf.edu/documentation/reference/std_LoudnessEBUR128.html).
- ```ac_temporal_centroid```: temporal centroid (sec.) of the audio signal. It is the point in time in a signal that is a temporal balancing point of the sound event energy.
- ```ac:log_attack_time```: the [log (base 10) of the attack time](http://essentia.upf.edu/documentation/reference/std_LogAttackTime.html) of a signal envelope. The attack time is defined as the time duration from when the sound becomes perceptually audible to when it reaches its maximum intensity.
