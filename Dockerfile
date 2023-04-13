FROM pegi3s/docker:20.04

RUN apt-get update -y && \
    apt-get install -y unzip

COPY auto-phylo-scripts.zip /opt

WORKDIR /opt

RUN unzip auto-phylo-scripts.zip && \
    rm /opt/auto-phylo-scripts.zip

CMD /opt/main
