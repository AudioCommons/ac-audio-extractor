FROM python:3.6.8-stretch

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
    && git checkout v2.4.5 \
    && python2 ./waf configure \
    && python2 ./waf \
    && python2 ./waf install \
    && cd / && rm -r /tmp/gaia


# Essentia (checkout freesound_extractor_update branch at specific commit)
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
    && cd /essentia/essentia && git checkout 0ddaedd3ba8988ae759cc746ff7e4ad995dcfeae \ 
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


# Install ffmpeg (NOTE: this could be probably optimized using libav from above)
RUN apt-get update && apt-get install -y ffmpeg

# Extra python dependencies
RUN pip install SoundFile==0.10.2 librosa==0.6.1 scipy==1.1.0 ffmpeg-python==0.1.17
RUN pip install rdflib==4.2.2 rdflib-jsonld==0.4.0 PyLD==1.0.3

# Install version 0.4 (commit be443e54f5b8865d7a055e438545f139899d17bc) of timbral models
RUN git clone https://github.com/AudioCommons/timbral_models.git && cd timbral_models && git checkout be443e54f5b8865d7a055e438545f139899d17bc && python setup.py install  # Using commit corresponding to v0.5 (D5.8)

# Add high-level models and music extractor configuration
RUN mkdir -p models
ADD models /models
ADD music_extractor_profile.yaml /

# Add analysis script
ADD analyze.py /
ENTRYPOINT [ "python", "/analyze.py" ]
