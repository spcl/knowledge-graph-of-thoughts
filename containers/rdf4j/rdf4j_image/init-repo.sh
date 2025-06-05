#!/bin/bash

RDF4J_URL="http://localhost:8080/rdf4j-server/repositories"
REPO_ID="kgot"
CONFIG_FILE="/opt/repository-config.ttl"
MAX_RETRIES=10

# Start RDF4J in the background
echo "Starting RDF4J server..."
/usr/local/tomcat/bin/catalina.sh run &
SERVER_PID=$!

# Wait until RDF4J server is available
echo "Waiting for RDF4J to be ready..."
for i in $(seq 1 $MAX_RETRIES); do
  if curl -sf "$RDF4J_URL"; then
    echo "RDF4J is up!"
    break
  fi
  echo "[$i/$MAX_RETRIES] Still waiting..."
  sleep 3
done

# Check final availability
if ! curl -sf "$RDF4J_URL"; then
  echo "Error: RDF4J server not responding after $MAX_RETRIES attempts."
  kill $SERVER_PID
  exit 1
fi

# Create the repository
echo "Creating repository..."
curl -X PUT \
  -H "Content-Type: application/x-turtle" \
  --data-binary @"$CONFIG_FILE" \
  "$RDF4J_URL/$REPO_ID"

echo "Repository '$REPO_ID' created successfully."

# Keep the server running
wait $SERVER_PID
