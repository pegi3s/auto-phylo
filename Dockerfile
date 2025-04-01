FROM pegi3s/docker:20.04

RUN apt-get update -y && \
    apt-get install -y unzip

ADD auto-phylo-scripts/* /opt

WORKDIR /opt

CMD /opt/pre_main
