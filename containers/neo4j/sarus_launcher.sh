#!/bin/bash

# Load environment variables
set -a
source .env
set +a

NEO4J_IMPORT_DIR=$(realpath ../../kgot/knowledge_graph/_snapshots)

bash -c "
nohup sarus run \
  --env NEO4J_dbms_security_procedures_unrestricted=apoc.export.*,apoc.meta.* \
  --env NEO4J_dbms_security_procedures_allowlist=apoc.* \
  --env NEO4J_apoc_export_file_enabled=true \
  --env NEO4J_apoc_import_file_enabled=true \
  --env NEO4J_apoc_import_file_use__neo4j__config=true \
  --env NEO4J_AUTH=$AUTH \
  --env 'NEO4J_PLUGINS=[\"apoc\"]' \
  --env TINI_SUBREAPER=1 \
  --env NEO4J_server_http_listen__address=:$HTTP_PORT \
  --env NEO4J_server_bolt_listen__address=:$BOLT_PORT \
  --mount=type=bind,source=$NEO4J_IMPORT_DIR,destination=/import \
  neo4j:5.26.2 > sarus_neo4j.log 2>&1 &
"