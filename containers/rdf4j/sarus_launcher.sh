#!/bin/bash

bash -c "
nohup sarus run \
  spcleth/kgot-rdf4j:latest \
  > sarus_rdf4j.log 2>&1 &
"