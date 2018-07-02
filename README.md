# AudioCommons audio extractor

This tool incorporates algorithms for extracting music properties for music samples and music pieces, and other high-level non-musical properties for other kinds of sounds. 

To facilitate its usage, the tool has been *dockerized* and should run successfully in any platform with [Docker](https://www.docker.com/) installed.


## Using the tool

You can easily analyze sound from an audio file in the current directory using the following command:

```
docker run -it --rm -v `pwd`:/tmp mtgupf/ac-audio-extractor:v2 -i /tmp/audio.wav -o /tmp/analysis.json
```

The example above mounts the current directory ``pwd`` in the virtual `tmp` directory inside Docker. The output file `audio.json` is also written in `tmp`, and therefore appears in the current directory. You can also mount different volumes and specify paths for input audio and analysis output like this (for more information, checkout [Docker volumes](https://docs.docker.com/storage/volumes/)):

```
docker run -it --rm -v /local/path/to/your/audio/file.wav:/audio.wav -v /local/path/to/output_directory/:/outdir mtgupf/ac-audio-extractor:v2 -i /audio.wav -o /outdir/analysis.json
```

Run help command to learn about available options (TODO: update that section):

```
docker run -it --rm -v `pwd`:/tmp mtgupf/ac-audio-extractor:v2 --help

usage: analyze.py [-h] [-v] [-t] [-m] -i INPUT -o OUTPUT [-f FORMAT]

AudioCommons audio extractor (v2). Analyzes a given audio file and writes
results to a JSON file.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         if set prints more info on screen
  -t, --timbral-models  if set, compute timbral models as well
  -m, --music-highlevel
                        if set, compute high-level music descriptors
  -i INPUT, --input INPUT
                        input audio file
  -o OUTPUT, --output OUTPUT
                        output analysis file
  -f FORMAT, --format FORMAT
                        format of the output analysis file ("json" or
                        "jsonld", defaults to "jsonld")
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
- ```ac:duration```: duration of audio file (sec.)
- ```ac:lossless```: whether audio file is in lossless codec (1 or 0)
- ```ac:codec```: audio codec
- ```ac:bitrate```: bit rate
- ```ac:samplerate```: sample rate
- ```ac:channels```: number of audio channels
- ```ac:audio_md5```: the MD5 checksum of raw undecoded audio payload. It can be used as a unique identifier of audio content

### Music
- ```ac:tempo```: BPM value estimated by beat tracking algorithm by [Degara et al., 2012](http://essentia.upf.edu/documentation/reference/std_RhythmExtractor2013.html).
- ```ac:tonality```: [key and scale](http://essentia.upf.edu/documentation/reference/std_Key.html) estimate based on HPCP descriptor and "Krumhansl" key detection profile which should work generally fine for pop music. 
- ```ac:note```: Pitch note name based on median of estimated fundamental frequency.
- ```ac:mini_note```: Estimated midi note number pitch note.

### Dynamics
- ```ac:loudness```: the integrated (overall) loudness (LUFS) measured using the [EBU R128 standard](http://essentia.upf.edu/documentation/reference/std_LoudnessEBUR128.html).
- ```ac:dynamic_range```: loudness range (dB, LU) measured using the [EBU R128 standard](http://essentia.upf.edu/documentation/reference/std_LoudnessEBUR128.html).
- ```ac_temporal_centroid```: temporal centroid (sec.) of the audio signal. It is the point in time in a signal that is a temporal balancing point of the sound event energy.
- ```ac:log_attack_time```: the [log (base 10) of the attack time](http://essentia.upf.edu/documentation/reference/std_LogAttackTime.html) of a signal envelope. The attack time is defined as the time duration from when the sound becomes perceptually audible to when it reaches its maximum intensity.
