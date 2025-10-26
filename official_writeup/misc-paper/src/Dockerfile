FROM texlive/texlive:latest

RUN apt-get update && apt-get install python3-pip -y
RUN pip install --break-system-packages matplotlib

ADD tex/ /workdir/tex/
ADD main.py /workdir/

ENTRYPOINT ["python3", "-u", "main.py"]