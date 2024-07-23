FROM pegi3s/docker:20.04

RUN apt-get update -y && \
    apt-get install -y unzip wget

WORKDIR /opt

COPY version3.zip /opt

RUN unzip version3.zip && \
     rm /opt/version3.zip
CMD /opt/pre_main
