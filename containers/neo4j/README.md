# Neo4j Docker Image Setup

## Initial Setup

- **Linux** - Please retrieve the current user IDs (**UID** and **GID**) with the command `id` and update the environment file [`env`](/containers/neo4j/.env) accordingly.
- **MacOS/Windows** - No steps necessary

If you are running inside a virtual machine and using a `shared folder`, please update **UID** and **GID** inside [`env`](/containers/neo4j/.env) with the **IDs** of the snapshots folder owner or group.

### Example

```bash
cd containers/neo4j/neo4j/

ls -la
# drwxrwx---  3 root  vboxsf  96 Jun 25 17:12 .
# drwxrwx---  3 root  vboxsf  96 Jun 25 17:12 ..
# drwxrwx---  3 root  vboxsf  96 Jun 25 17:27 .env
# drwxrwx---  3 root  vboxsf  96 Jun 25 17:27 README.md
# drwxrwx---  3 root  vboxsf  96 Jun 25 17:27 docker-compose.yaml
# drwxrwx---  3 root  vboxsf  96 Jun 25 17:27 snapshots
```

In this example, `root` is the **owner** and `vboxsf` is the **group** of the respective files.

We do not want applications inside the Docker image to run with sudo permission. Looking at the permissions we can see that **group** has **read** and **write** (drwx`rw`x---) permissions on the folder files.

`vboxsf` should be used as user for the Docker image because of its **rw** access. If this situation does not correspond to yours, please *change permissions or ownership* of the folder.

```bash
cd neo4j

# Allow everyone to have access
chmod -R 777 snapshots 
# Change ownership of the folder
chown -R [OWNER]:[GROUP] snapshots
```

Now that the owner of the folder has been established, we can proceed in looking up their **UID/GID**.

```bash
id
# uid=1000([OWNER]) gid=1000([GROUP]) groups=1000([GROUP]),27(sudo),999(vboxsf)

# Based on the setup we are going to use either 999 or 1000 if we changed ownership/permissions.
```

## Running

Please execute the following commands. Depending on the operating system you may need privileged rights.

```bash
cd neo4j

docker compose up -d 
# or
docker-compose up -d 
```

`-d` detaches the terminal from the container.

The Neo4j ports can also be changed inside the environment file [`.env`](/containers/neo4j/.env), in order to prevent failure due to already used ports by other services you may have active on your machine.

### Knowledge Graph Snapshots

Snapshots of the Neo4j database will be stored in the `neo4j/snapshots` directory. We provide a [tool](/snapshots_visualization_tool) to visualize these snapshots as well as changes to the knowledge graph.
