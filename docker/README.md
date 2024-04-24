# TURN server

## setup TURN server

### create ssl certificate

```bash

sudo certbot certonly --standalone --preferred-challenges http \
    --deploy-hook "systemctl restart coturn" \
    -d turn.genai-vm.amprajin.in
```

### config

Update the `turnserver.conf` file with the following content:

replace turn.genai-vm.amprajin.in with your own domain name.

replace 34.100.139.35 with your own IP address.

move the turn folder to the vm.

```bash
mkdir turn
cd turn

sudo nano turnserver.conf

sudo nano docker-compose.yml
```

```bash
```

```bash
```

```bash

then run the following command to start the TURN server:

```bash
docker compose up -d
```

test the TURN server:

refer <https://gabrieltanner.org/blog/turn-server/>


turn:turn.genai-vm.amprajin.in:3478
test
test123

turn:turn.genai-vm.amprajin.in:8443
test
test123