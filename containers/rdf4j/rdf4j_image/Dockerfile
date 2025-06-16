FROM eclipse/rdf4j-workbench:latest

USER root
RUN apt-get update && apt-get install -y curl

COPY init-repo.sh /usr/local/bin/init-repo.sh
COPY repository-config.ttl /opt/repository-config.ttl

RUN chmod +x /usr/local/bin/init-repo.sh

ENTRYPOINT ["/usr/local/bin/init-repo.sh"]
