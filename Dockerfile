FROM mtgupf/essentia
ADD analyze.py /
CMD [ "python", "./analyze.py" ]