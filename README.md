# AudioCommons audio extractor

Command-line extractor for audio descriptors compliant with AudioCommons schema.

Using Essentia library: http://essentia.upf.edu

## Example usage
```
usage: analyze.py [-h] -i INPUT -o OUTPUT -t TYPE

AudioCommons audio extractor. Analyzes a given audio file and writes results
to a json file.

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        input audio file
  -o OUTPUT, --output OUTPUT
                        output json file
  -t TYPE, --type TYPE  type of extractor [music|sound]
```

Example:
```
python analyze.py -i input_audio.mp3 -o result.json -t sound
```

## Audio descriptors
### Metadata
- ```ac:duration```: duration of audio file (sec.)
- ```ac:lossless```: whether audio file is in lossless codec (1 or 0)
- ```ac:codec```: audio codec
- ```ac:bitrate```: bit rate
- ```ac:samplerate```: sample rate
- ```ac:channels```: number of audio channels
- ```ac:audio_md5```: the MD5 checksum of raw undecoded audio payload. It can be used as a unique identifier of audio content

### Rhythm

- ```ac:tempo```: BPM value estimated by beat tracking algorithm by [Degara et al., 2012](http://essentia.upf.edu/documentation/reference/std_RhythmExtractor2013.html).

### Timbre

- ```ac:dissonance```: [sensory dissonance](http://essentia.upf.edu/documentation/reference/std_Dissonance.html) of the spectrum. It measures perceptual roughness of the sound and is based on the roughness of its spectral peaks.
- ```ac:tristimulus```: [tristimulus](http://essentia.upf.edu/documentation/reference/std_Tristimulus.html) of the spectrum. It measures the mixture of harmonics in a given sound, grouped into three sections. The first tristimulus measures the relative weight of the first harmonic; the second tristimulus measures the relative weight of the second, third, and fourth harmonics taken together; and the third tristimulus measures the relative weight of all the remaining harmonics.
- ```ac:odd_to_even_harmonic_ratio```: the ratio between a signal's [odd and even harmonic energy](http://essentia.upf.edu/documentation/reference/std_OddToEvenHarmonicEnergyRatio.html). It is a measure allowing to distinguish odd-harmonic-energy predominant sounds (e.g. a clarinet) from equally important even-harmonic-energy sounds (e.g. a trumpet). 
- ```ac:mfcc```: the first 13 [mel frequency cepstrum coefficients](http://essentia.upf.edu/documentation/reference/std_MFCC.html) characterizing overall spectral shape of the signal.
- ```ac:spectral_centroid```: [spectral centroid](http://essentia.upf.edu/documentation/reference/std_Centroid.html) (Hz). It is a measure that indicates where the "center of mass" of the spectrum is. Perceptually, it has a robust connection with the impression of "brightness" of a sound.


### Dynamics
- ```ac:loudness```: the integrated (overall) loudness (LUFS) measured using the [EBU R128 standard](http://essentia.upf.edu/documentation/reference/std_LoudnessEBUR128.html).
- ```ac:dynamic_range```: loudness range (dB, LU) measured using the [EBU R128 standard](http://essentia.upf.edu/documentation/reference/std_LoudnessEBUR128.html).
- ```ac_temporal_centroid```: temporal centroid (sec.) of the audio signal. It is the point in time in a signal that is a temporal balancing point of the sound event energy.
- ```ac:log_attack_time```: the [log (base 10) of the attack time](http://essentia.upf.edu/documentation/reference/std_LogAttackTime.html) of a signal envelope. The attack time is defined as the time duration from when the sound becomes perceptually audible to when it reaches its maximum intensity.

### Tonality
- ```ac:hpcp```: harmonic pitch class profile ([HPCP](http://essentia.upf.edu/documentation/reference/std_HPCP.html)) measuring the relative intensity of each of the 12 pitch classes of the equal-tempered scale.
