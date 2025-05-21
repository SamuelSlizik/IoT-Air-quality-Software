# IoT-Air-quality-Software
Software of the IoT device for measuring air quality

To successfully run this software you first need to run these following command to change permissions:

sudo chmod +x docker-entrypoint.sh
sudo chmod +x shutdown.sh

You will also need to install these python dependencies:

sudo apt update
sudo apt install python3-smbus i2c-tools
sudo apt install python3-spidev
sudo apt install python3-numpy
sudo apt install python3-paho-mqtt

after this run docker compose up -d --build