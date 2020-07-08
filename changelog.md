# NorthState Change Log
## Add non-root user to run Docker:
- If docker group does not exist: `sudo groupadd docker`
- Add user to docker group: `sudo usermod -aG docker username`
- Apply new group changes: `newgrp docker`
- Test changes: `docker version; docker run hello-world`
