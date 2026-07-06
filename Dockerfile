FROM python:3.11-slim-bookworm

# Common requirements
RUN apt-get update \
    && apt-get install -y \
        libyaml-0-2 \
        libfftw3-double3 \
        libfftw3-single3 \
        libtag1v5 \
        libsamplerate0 \
        libavcodec59 \
        libavformat59 \
        libavutil57 \
        python3 \
        python3-numpy \
        python3-yaml \
        python3-six \
        libsndfile1 \
        pkg-config \
        swig \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (needed for essentia)
RUN pip install numpy

# Essentia
RUN apt-get update \
    && apt-get install -y \
        build-essential \
        libyaml-dev \
        libfftw3-dev \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        python3-dev \
        libsamplerate0-dev \
        libtag1-dev \
        libeigen3-dev \
        git \
    && mkdir /essentia && cd /essentia && git clone https://github.com/MTG/essentia.git \
    && cd /essentia/essentia \
    && ./waf configure --with-examples --with-python \
    && ./waf && ./waf install && ldconfig \
    && apt-get remove -y \
        build-essential \
        libyaml-dev \
        libfftw3-dev \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        python3-dev \
        libsamplerate0-dev \
        libtag1-dev \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/* \
    && cd / && rm -rf /essentia/essentia


# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Extra python dependencies
RUN pip install SoundFile librosa scipy ffmpeg-python
RUN pip install rdflib rdflib-jsonld PyLD

# Install timbral models
# Also install numpy version pinned for timbral models to work
RUN git clone https://github.com/AudioCommons/timbral_models.git \
    && cd timbral_models \
    && git checkout 1aa6f639d7f781c08eee83caae89202f32b6333f \
    && pip install .
RUN pip install numpy==1.26.4

# Add high-level models and music extractor configuration
RUN mkdir -p models
ADD models /models
ADD music_extractor_profile.yaml /

ENV NUMBA_CACHE_DIR=/tmp

# Add analysis script
ADD analyze.py /
ENTRYPOINT [ "python3", "/analyze.py" ]