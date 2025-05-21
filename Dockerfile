FROM python:3.10-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      openssl \
      openssh-client \
      sshpass \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker-entrypoint.sh /usr/local/bin/
COPY shutdown.sh    /usr/local/bin/

VOLUME ["/certs"]
EXPOSE 443

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn","app:app","-b","0.0.0.0:443","--certfile","/certs/cert.pem","--keyfile","/certs/key.pem","--workers","2"]
