FROM python:3.11.7-slim-bookworm

# last line is dependencies for weasyprint (for generating pdfs in lafede pilot) https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#debian-11
RUN apt update && \
    apt-get install -y \
    gosu \
    git \
    sqlite3 \
    postgresql-client \
    jq \
    libpango-1.0-0 libpangoft2-1.0-0 \
      && pip install cffi brotli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/idhub

# reduce size (python specifics) -> src https://stackoverflow.com/questions/74616667/removing-pip-cache-after-installing-dependencies-in-docker-image
ENV PYTHONDONTWRITEBYTECODE=1
# here document in dockerfile src https://stackoverflow.com/questions/40359282/launch-a-cat-command-unix-into-dockerfile
RUN cat > /etc/pip.conf <<END
[install]
compile = no

[global]
no-cache-dir = True
END

# not needed anymore?
#COPY ssikit_trustchain/didkit-0.3.2-cp311-cp311-manylinux_2_34_x86_64.whl /opt/idhub
COPY ./requirements.txt /opt/idhub
RUN pip install -r requirements.txt

COPY docker/idhub.entrypoint.sh /

COPY . /opt/idhub/

ENTRYPOINT sh /idhub.entrypoint.sh
