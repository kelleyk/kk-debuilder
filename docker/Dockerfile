FROM ubuntu:xenial
MAINTAINER Kevin Kelley <kelleyk@kelleyk.net>

RUN apt-get update && apt-get dist-upgrade -y
RUN apt-get install -y python python-setuptools git
RUN easy_install pip
RUN pip install --upgrade pip

RUN pip install git+git://github.com/kelleyk/apt-config-tool.git
RUN pip install git+git://github.com/kelleyk/docker-debuild.git
RUN pip install git+git://github.com/kelleyk/kk-debuilder.git

# XXX: Temporary workaround for test-data submodule being unavailable.
RUN mkdir -p /tmp/src && cd /tmp/src && git clone https://github.com/kelleyk/git-buildpackage.git && cd git-buildpackage && python setup.py install

