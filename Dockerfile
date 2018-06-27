FROM python:3

RUN apt-get update \
    && apt-get install -y libyaml-0-2 libfftw3-3 libtag1v5 libsamplerate0 \
       libavcodec57 libavformat57 libavutil55 \
       libavresample3 python3 python3-numpy libpython3.5 python3-yaml python3-six libsndfile1 \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install numpy soundfile librosa scipy
RUN git clone https://github.com/AudioCommons/timbral_models.git && cd timbral_models && python setup.py install

RUN apt-get update \
    && apt-get install -y build-essential libyaml-dev libfftw3-dev \
       libavcodec-dev libavformat-dev libavutil-dev libavresample-dev \
       python-dev libsamplerate0-dev libtag1-dev python3-numpy-dev git \
    && mkdir /essentia && cd /essentia && git clone https://github.com/MTG/essentia.git \
    && cd /essentia/essentia && git checkout 76142076e563173397349517bff15c9fe54cb163 \
    && ./waf configure --with-examples --with-python \
    && ./waf && ./waf install && ldconfig \
    &&  apt-get remove -y build-essential libyaml-dev libfftw3-dev libavcodec-dev \
        libavformat-dev libavutil-dev libavresample-dev python3-dev libsamplerate0-dev \
        libtag1-dev python3-numpy-dev \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/* \
    && cd / && rm -rf /essentia/essentia

ADD analyze.py /
ENTRYPOINT [ "python", "/analyze.py" ]
