# TURN server

## setup TURN server

### create ssl certificate

```bash
docker compose down
```

```bash
docker run --rm  \
  --network host\
  -v $(pwd)/etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot:v2.10.0 \
  -it \
  certonly --standalone --preferred-challenges http \
  --email prajin.ults@gmail.com \
  -d turn.genai.amprajin.in \
  --agree-tos --no-eff-email --force-renewal -v \
  && sudo chmod -R 777 ./etc/letsencrypt


```bash
docker run --rm  \
  --network host\
  -v $(pwd)/etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot:v2.10.0 \
  -it \
  certonly --standalone --preferred-challenges http \
  --email prajin.ults@gmail.com \
  -d shop.genai.amprajin.in\
  --agree-tos --no-eff-email --force-renewal -v \
  && sudo chmod -R 777 ./etc/letsencrypt
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