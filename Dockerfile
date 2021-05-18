FROM python:3.9-alpine3.13

RUN apk add git
RUN pip install git+https://github.com/devottys/darkdraw.git
RUN sh -c "echo >>~/.visidatarc import darkdraw"
RUN git clone https://github.com/devottys/studio

ENV TERM="xterm-256color"
ENTRYPOINT ["vd", "studio/darkdraw-tutorial.ddw"]
