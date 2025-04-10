# Snapshot Visualization Tool

## Initial Setup

- **Linux** - Please retrieve the current user IDs (**UID** and **GID**) with the command `id` and update the environment file [`.env`](.env) accordingly.
- **MacOS/Windows** - No steps necessary

If you are running inside a virtual machine and using a `shared folder`, please update **UID** and **GID** inside [`.env`](.env) with the **IDs** of the current folder owner or group.

### Example

```bash
cd visualization/backend/db/

ls -la
# drwxrwx---  3 root  vboxsf  96 Jun 25 17:12 .
# drwxrwx---  3 root  vboxsf  96 Jun 25 17:12 ..
# drwxrwx---  3 root  vboxsf  96 Jun 25 17:27 import
```

In this example, `root` is the **owner** and `vboxsf` is the **group** of the respective files.

We do not want applications inside the Docker image to run with sudo permission. Looking at the permissions we can see that **group** has **read** and **write** (drwx`rw`x---) permissions on the folder files.

`vboxsf` should be used as user for the Docker image because of its **rw** access. If this situation does not correspond to yours, please *change permissions or ownership* of the folder.

```bash
cd visualization

# Allow everyone to have access
chmod -R 777 backend/db/import 
# Change ownership of the folder
chown -R [OWNER]:[GROUP] backend/db/import
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
cd visualization

docker compose up -d 
# or
docker-compose up -d 
```

`-d` detach the terminal from the container.

Once everything is running, open any browser and navigate to:
`localhost` or `127.0.0.1`

The port on which the website is hosted is the standard `80`. If you have any other service running on the same port, you can easily change the port of the visualization tool inside [`.env`](.env) under `FRONTEND_PORT`.

If you change the default port, you will need to specify that port, when accessing the visualization tool in your browser, for example `localhost:1234` or `127.0.0.1:1234`.
