FROM python:3

# Common requirements
RUN apt-get update \
    && apt-get install -y \
        libyaml-0-2 \ 
        libfftw3-3 \ 
        libtag1v5 \ 
        libsamplerate0 \
        libavcodec57 \ 
        libavformat57 \ 
        libavutil55 \
        libavresample3 \ 
        python3 \ 
        python3-numpy \ 
        libpython3.5 \ 
        python3-yaml \ 
        python3-six \
        libsndfile1 \
        pkg-config \
        swig \
	&& rm -rf /var/lib/apt/lists/*


# Python dependencies (needed for essentia)
RUN pip install numpy==1.14.5


# Gaia
# See https://github.com/MTG/gaia
RUN apt-get update \
    && apt-get install -y \
        build-essential \
        python \
        libqt4-dev \
        libyaml-dev \
        python-dev \
    && git clone https://github.com/MTG/gaia /tmp/gaia \
    && cd /tmp/gaia \
    && python2 ./waf configure \
    && python2 ./waf \
    && python2 ./waf install \
    && cd / && rm -r /tmp/gaia


# Essentia
RUN apt-get update \
    && apt-get install -y \
        build-essential \ 
        libyaml-dev \
        libfftw3-dev \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        libavresample-dev \
        python-dev \
        libsamplerate0-dev \
        libtag1-dev \
        python3-numpy-dev \
        git \
    && mkdir /essentia && cd /essentia && git clone https://github.com/MTG/essentia.git \
    && cd /essentia/essentia && git checkout 74b355fc14fe48f59bdff9608dfe5ce3c54640a4 \ 
    && ./waf configure --with-examples --with-python --with-gaia \
    && ./waf && ./waf install && ldconfig \
    &&  apt-get remove -y \
        build-essential \
        libyaml-dev \
        libfftw3-dev \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        libavresample-dev \
        python3-dev \
        libsamplerate0-dev \
        libtag1-dev \
        python3-numpy-dev \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/* \
    && cd / && rm -rf /essentia/essentia

# Extra python dependencies
RUN pip install SoundFile==0.10.2 librosa==0.6.1 scipy==1.1.0
RUN pip install rdflib==4.2.2 rdflib-jsonld==0.4.0 PyLD==1.0.3
RUN git clone https://github.com/AudioCommons/timbral_models.git && cd timbral_models && git checkout e12791458a4c896c40b00096004fd7b260b7f5fb && python setup.py install  # Using commit with division fixes for Python3 (this is temporal, should be set to master once new version is out)


# Add high-level models and music extractor configuration
RUN mkdir -p models
ADD models /models
ADD music_extractor_profile.yaml /


RUN pip install matplotlib

# Add analysis script
ADD analyze.py /
ENTRYPOINT [ "python", "/analyze.py" ]
