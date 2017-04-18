FROM mtgupf/essentia
ADD analyze.py /
ENTRYPOINT [ "python", "/analyze.py" ]