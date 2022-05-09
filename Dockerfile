FROM python:3.8-alpine

RUN pip install requests python-dateutil wcwidth

RUN apk add git
RUN pip install git+https://github.com/devottys/darkdraw.git --no-deps
RUN pip install --upgrade git+https://github.com/saulpw/visidata.git@develop
RUN sh -c "echo >>~/.visidatarc import darkdraw"
RUN git clone https://github.com/devottys/studio

ENV TERM="xterm-256color"
ENTRYPOINT ["vd", "studio/darkdraw-tutorial.ddw"]
