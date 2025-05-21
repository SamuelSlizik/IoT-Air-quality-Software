# IoT-Air-quality-Software
Software of the IoT device for measuring air quality

To successfully run this software you first need to run these following command to change permissions:

sudo chmod +x docker-entrypoint.sh
sudo chmod 777 settings.json

You will also need to install these python dependencies:

sudo apt update
sudo apt install python3-smbus i2c-tools
sudo apt install python3-spidev
sudo apt install python3-numpy
sudo apt install python3-paho-mqtt

after this run docker compose up -d --build

To make the rest of the system work you need to move the I2cReader.service into /etc/systemd/system/ and change the paths in the script to point to your I2cReader.py location
After that run these following commands

sudo systemctl daemon-reload
sudo systemctl enable I2cReader.service
sudo systemctl start  I2cReader.service

The last thing you need to do is run sudo crontab -e
And append this line to the end, also change the location to your location of the script

* * * * * cd /home/samo/IoT-Air-quality-Software/ && /usr/bin/python3 NetworkManager.py
