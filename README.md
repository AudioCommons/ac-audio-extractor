# Audio Commons Audio Extractor

The Audio Commons Audio Extractor is a tool for analyzing audio files and extract both music properties (for music samples and music pieces) as well as high-level non-musical properties (timbre models). See [this blog post](https://www.audiocommons.org/2018/07/15/audio-commons-audio-extractor.html) for further details about the Audio Commons Audio Extractor.

To facilitate its usage, the tool has been *dockerized* and should run efforlessly in any platform with [Docker](https://www.docker.com/) installed. Below you'll find some instructions for running the tool as well as the full list of included audio features.

Checkout the [web demonstrator](http://www.audiocommons.org/ac-audio-extractor/web_demonstrator/) that shows the power of some of the music properties extracted with this tool.

## License

The Audio Commons Audio Extractor is licensed under AGPLv3 except for the included [timbral models](https://github.com/AudioCommons/timbral_models) code which is licensed under Apache 2. Both license files are included in this source code repository.


## Running the audio extractor

The Audio Commons Audio Extractor is expected to be used as a command line tool and run from a terminal. Assuming you have Docker installed, you can easily analyze an audio file using the following command (the audio file must be located in the same folder from where you run the command, be aware that the first time you run this command it will take a lot of time as Docker will need to download the actual Audio Commons Audio Extractor tool first):

```
docker run -it --rm -v `pwd`:/tmp mtgupf/ac-audio-extractor:v3 -i /tmp/audio.wav -o /tmp/analysis.json -st
```

The example above mounts the current directory ``pwd`` in the virtual `tmp` directory inside Docker. The output file `audio.json` is also written in `tmp`, and therefore appears in the current directory. You can also mount different volumes and specify paths for input audio and analysis output using the following command (read the [Docker volumes](https://docs.docker.com/storage/volumes/) documentation for more information):

```
docker run -it --rm -v /local/path/to/your/audio/file.wav:/audio.wav -v /local/path/to/output_directory/:/outdir mtgupf/ac-audio-extractor:v3 -i /audio.wav -o /outdir/analysis.json  -st
```

You can also run the analysis on several files contained in a directory by entering directories as input and output arguments to the extractor. For instance, you can use the following command:

```
docker run -it --rm -v /local/path/to/your/input_directory/:/audio -v /local/path/to/output_directory/:/outdir mtgupf/ac-audio-extractor:v3 -i /audio/ -o /outdir/  -st
```

You can use the `--help` flag with the Audio Commons Audio Extractor so see a complete list of all available options:

```
docker run -it --rm -v `pwd`:/tmp mtgupf/ac-audio-extractor:v3 --help

uusage: analyze.py [-h] [-v] [-t] [-m] [-s] -i INPUT -o OUTPUT [-f FORMAT]
                  [-u URI]

Audio Commons Audio Extractor (v3). Analyzes a given audio file and writes
results to a JSON file.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         if set, prints detailed info on screen during the
                        analysis
  -t, --timbral-models  include descriptors computed from timbral models
  -m, --music-pieces    include descriptors designed for music pieces
  -s, --music-samples   include descriptors designed for music samples
  -i INPUT, --input INPUT
                        input audio file or input directory containing the audio files to analyze
  -o OUTPUT, --output OUTPUT
                        output analysis file or output directory where the analysis files will be saved
  -f FORMAT, --format FORMAT
                        format of the output analysis file ("json" or
                        "jsonld", defaults to "jsonld")
  -u URI, --uri URI     URI for the analyzed sound (only used if "jsonld"
                        format is chosen)
```

Note that you can use the flags `t`, `m` and `s` to enable or disable the computation of some specific audio features.


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
    "loop": true,
    "tempo": 120,
    "tempo_confidence": 1.0,
    "note_midi": 74,
    "note_name": "D5",
    "note_frequency": 592.681884765625,
    "note_confidence": 0.0,
    "brightness": 50.56954356039029,
    "depth": 13.000903137777897,
    "metallic": 0.4906048209174263,
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
        "ebucore": "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#",
        "nfo": "http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#"
    },
    "@type": "ac:AudioFile",
    "ebucore:bitrate": 705600.0,
    "ebucore:filesize": 529278,
    "ebucore:hasCodec": {
        "@type": "ebucore:AudioCodec",
        "ebucore:codecId": "pcm_s16le"
    },
    "nfo:compressionType": "nfo:losslessCompressionType",
    "ac:audioMd5": "8da67c9c2acbd13998c9002aa0f60466",
    "ac:availableItemOf": {
        "@type": "ac:AudioClip"
    },
    "ac:signalAudioFeature": [
        {
            "@type": "afv:Loop",
            "afo:value": true
        },
        {
            "@type": "afv:Tempo",
            "afo:confidence": 1.0,
            "afo:value": 120
        },
        {
            "@type": "afv:Key",
            "afo:confidence": 0.2868785858154297,
            "afo:value": "G# minor"
        },
        {
            "@type": "afv:TemporalCentroid",
            "afo:value": 0.5078766345977783
        },
        {
            "@type": "afv:MIDINote",
            "afo:confidence": 0.0,
            "afo:value": 74
        },
        {
            "@type": "afv:Pitch",
            "afo:confidence": 0.0,
            "afo:value": 592.681884765625
        },
        {
            "@type": "afv:Loudness",
            "afo:value": -28.207069396972656
        },
        {
            "@type": "afv:Note",
            "afo:confidence": 0.0,
            "afo:value": "D5"
        },
        {
            "@type": "afv:LogAttackTime",
            "afo:value": 0.30115795135498047
        }
    ],
    "ac:signalChannels": 1,
    "ac:signalDuration": 6.0,
    "ac:singalSamplerate": 44100.0
}
```


## Build the docker image locally

There is no need to build the Docker image locally because Docker will automatically retrieve the image from the remote [Docker Hub](https://hub.docker.com). However, if you need a custom version of the image you can also build it locally using the instructions in the `Dockerfile` of this repository. Use the following command:

```
docker build -t mtgupf/ac-audio-extractor:v3 .
```

### Pushing the image to MTG's Docker Hub

The pre-built image for the Audio Commons annotations tools is hosted in [MTG](http://mtg.upf.edu/)'s Docker Hub account. To push a new version of the image use the following command (and change the tag if needed):

```
docker push mtgupf/ac-audio-extractor:v3
```

This is only meant for the admins/maintainers of the image. You'll need a Docker account with wrtie access to MTG's Docker Hub space.


## Included audio features

### Audio file properties

These audio features are always computed and include:

- ```duration```: Duration of audio file in seconds.
- ```lossless```: Whether audio file is in lossless codec (true or false).
- ```codec```: Audio codec.
- ```bitrate```: Bit rate.
- ```samplerate```: Sample rate in Hz.
- ```channels```: Number of audio channels.
- ```audio_md5```: The MD5 checksum of raw undecoded audio payload. It can be used as a unique identifier of audio content.
- ```filesize```: Size of the file in nytes.

### Dynamics

These audio features are always computed and include:

- ```loudness```: The integrated (overall) loudness (LUFS) measured using the [EBU R128 standard](http://essentia.upf.edu/documentation/reference/std_LoudnessEBUR128.html).
- ```dynamic_range```: Loudness range (dB, LU) measured using the [EBU R128 standard](http://essentia.upf.edu/documentation/reference/std_LoudnessEBUR128.html).
- ```temporal_centroid```: Temporal centroid (sec.) of the audio signal. It is the point in time in a signal that is a temporal balancing point of the sound event energy.
- ```log_attack_time```: The [log (base 10) of the attack time](http://essentia.upf.edu/documentation/reference/std_LogAttackTime.html) of a signal envelope. The attack time is defined as the time duration from when the sound becomes perceptually audible to when it reaches its maximum intensity.
- ```single_event```: Whether the audio file contains one single *audio event* or more than one (true or false). This computation is based on the loudness of the signal and does not do any frequency analysis.

### Music samples and music pieces

These audio features are only computed when using the `-m` or `-s` flags and include:

- ```tempo```: BPM value estimated by beat tracking algorithm.
- ```tempo_confidence```: Reliability of the tempo estimation above (in a range between 0 and 1).
- ```loop```: Whether audio file is *loopable* (true or false).
- ```tonality```: Key value estimated by key detection algorithm. 
- ```tonality_confidence```: Reliability of the key estimation above (in a range between 0 and 1).


### Music samples 

These audio features are only computed when using the `-s` flag and include:

- ```note_name```: Pitch note name based on median of estimated fundamental frequency.
- ```note_midi```: MIDI value corresponding to the estimated note.
- ```note_frequency```: Frequency corresponding to the estimated note.
- ```note_confidence```: Reliability of the note name/midi/frequency estimation above (in a range between 0 and 1).


### Music pieces 

These audio features are only computed when using the `-m` flag and include:

- ```genre```: Music genre of the analysed music track (not yet implemented).
- ```mood```: Mood estimation for the analysed music track (not yet implemented).


### Timbre models

As described in [deliverable D5.2](https://www.audiocommons.org/assets/files/AC-WP5-SURREY-D5.2%20First%20prototype%20of%20timbral%20characterisation%20tools%20for%20semantically%20annotating%20non-musical%20content.pdf), a number of timbre models have been developed and are included in this tool. Timbre models estimate perceptual qualities of the sounds which tend to be quite subjective and ill-defined. These audio features are only computed when using the `-t` flag and include:

- ```brightness```: brightness of the analyzed audio in a scale from [0-100]. A *bright* sound is one that is clear/vibrant and/or contains significant high-pitched elements.
- ```hardness```: hardness of the analyzed audio in a scale from [0-100]. A *hard* sound is one that conveys the sense of having been made (i) by something solid, firm or rigid; or (ii) with a great deal of force.
- ```depth```: depth of the analyzed audio in a scale from [0-100]. A *deep* sound is one that conveys the sense of having been made far down below the surface of its source.
- ```roughness```: roughness of the analyzed audio in a scale from [0-100]. A *rough* sound is one that has an uneven or irregular sonic texture.
- ```boominess```: bominess of the analyzedn sound in a scale from [0-100]. A *boomy* sound is one that conveys a sense of loudness, depth and resonance.
- ```warmth```: warmth of the analyzedn sound in a scale from [0-100]. A *warm* sound is one that promotes a sensation analogous to that caused by a physical increase in temperature.  
- ```sharpness```: sharpness of the analyzedn sound in a scale from [0-100]. A *sharp* sound is one that suggests it might cut if it were to take on physical form.
- ```reverb```: will return `true` if the signal has reverb or `false` otherwise.
