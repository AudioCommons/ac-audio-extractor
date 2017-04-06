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

```python analyze.py -i input_audio.mp3 -o result.json -t sound
```


