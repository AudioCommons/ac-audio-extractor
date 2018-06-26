# AudioCommons audio extractor for music samples

Build an image from the root directory (containing Dockerimage file):

```
docker build -t audiocommons/ac-audio-extractor .
```

Analyze sound from an audio file in the current directory:

```
docker run -it --rm -v `pwd`:/tmp audiocommons/ac-audio-extractor -i /tmp/audio.wav -o /tmp/analysis.json
```

The example above mounts the current directory ``pwd`` in the virtual `tmp` directory inside Docker. The output file `audio.json` is also written in `tmp`, and therefore appears in the current directory. You can also mount different volumes and specify paths for input audio and analysis output like this:

```
docker run -it --rm -v /local/path/to/your/audio/file.wav:/audio.wav -v /local/path/to/output_directory/:/outdir audiocommons/ac-audio-extractor -i /audio.wav -o /outdir/analysis.json
```

See how Docker volumes work for more information.


## Included descriptors (TODO: update that)

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
