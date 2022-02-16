FROM tensorflow/tensorflow:2.0.0-py3

ADD /src /opt
ADD /data /opt/data

ENV DATA_PATH="./data"
ENV TRAIN="True"
ENV VERSION="1"

WORKDIR /opt
ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/opt/main.py"]