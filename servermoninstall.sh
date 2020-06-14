#/bin/bash
# this script sets up a newly configured rpi for influxDB, grafana & mosquitto
# 
set -x 
# you must have the correct arm build for grafana
# pi zero, zero w or rpi 1
# all other rpi's use arch 7 arm
telegraf_user=telegraf
telegraf_passwd=PassW0rd
cli_user=ian
pi_zero=1
if [[ ${pi_zero} -eq 1 ]]
then
grafana=grafana-rpi_7.0.3_armhf.deb
else
# for pi 2 and above use
grafana=grafana_7.0.3_armhf.deb
fi
# update OS and install and configure influxDB, telegraf, grafana & mosquitto 
sudo apt update
sudo apt upgrade -y
sudo apt install apt-transport-https curl mosquitto mosquitto-clients vim -y 
wget -qO- https://repos.influxdata.com/influxdb.key | sudo apt-key add -
echo "deb https://repos.influxdata.com/debian buster stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
sudo apt update
sudo apt install influxdb telegraf
sudo systemctl unmask influxdb
sudo systemctl enable influxdb
sudo systemctl unmask telegraf
sudo systemctl enable telegraf
sudo systemctl start influxdb
echo "Sleeping for 1 minute to let things startup"
sleep 60

# create user and database for influxdb
echo "creating 'sensors' database with ${telegraf_user} user with one week data retention period"
echo " if the next three influxdb commands fail when the script is finished try running them from the command line then restart influxdb & telegraf "
curl "http://localhost:8086/query" --data-urlencode "q=CREATE USER ${telegraf_user} WITH PASSWORD ${telegraf_passwd} WITH ALL PRIVILEGES"
curl --user ${telegraf_user}:${telegraf_passwd} -XPOST 'http://localhost:8086/query' --data-urlencode 'q=CREATE DATABASE "sensors"'
curl -i --user  ${telegraf_user}:${telegraf_passwd} -XPOST http://localhost:8086/query --data-urlencode 'q=CREATE RETENTION POLICY "one_week_only" ON "sensors" DURATION 1w REPLICATION 1 DEFAULT'
# install & start grafana
wget https://dl.grafana.com/oss/release/${grafana}
sudo apt install ./${pi_2} -y
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

# Configure telegraf service for mqtt ingest
sudo mv /etc/telegraf/telegraf.conf /etc/telegraf/telegraf.conf.orig.$(date +"%Y-%m-%d_%H%M%S")
sudo cat > telegraf.conf <<EOF
[global_tags]
[agent]
  interval = "10s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  collection_jitter = "0s"
  flush_interval = "10s"
  flush_jitter = "0s"
  precision = ""
  hostname = ""
  omit_hostname = false
[[outputs.influxdb]]
 urls = ["http://127.0.0.1:8086"]
 database = "sensors"
 skip_database_creation = true
  username = ${telegraf_user}
  password = ${telegraf_passwd}
[[inputs.cpu]]
  percpu = true
  totalcpu = true
  collect_cpu_time = false
  report_active = false
[[inputs.disk]]
  ignore_fs = ["tmpfs", "devtmpfs", "devfs", "iso9660", "overlay", "aufs", "squashfs"]
[[inputs.diskio]]
[[inputs.kernel]]
[[inputs.mem]]
[[inputs.processes]]
[[inputs.swap]]
[[inputs.system]]
[[inputs.mqtt_consumer]]
        servers = ["tcp://localhost:1883"]
        data_format = "json"
        username = ${telegraf_user}
        password = ${telegraf_passwd}
        topics = [
          "tele/ServerRoom/SENSOR/#",
          "stat/ServerRoom/POWER/#",
        ]
EOF
sudo cp telegraf.conf /etc/telegraf
sudo systemctl restart telegraf.service

# Configure mosquitto mqtt service
sudo mv /etc/mosquitto/mosquitto.conf /etc/mosquitto/mosquitto.conf.orig.$(date +"%Y-%m-%d_%H%M%S")
sudo cat > mosquitto.conf <<EOF
# Place your local configuration in /etc/mosquitto/conf.d/
#
# A full description of the configuration file is at
# /usr/share/doc/mosquitto/examples/mosquitto.conf.example

pid_file /var/run/mosquitto.pid

persistence true
persistence_location /var/lib/mosquitto/

log_dest file /var/log/mosquitto/mosquitto.log

include_dir /etc/mosquitto/conf.d
allow_anonymous false
password_file /etc/mosquitto/mqtt_passwd
EOF

sudo mv mosquitto.conf /etc/mosquitto/

touch /tmp/passwd && mosquitto_passwd -b /tmp/passwd ${telegraf_user} ${telegraf_passwd} 
sudo mv /tmp/passwd  /etc/mosquitto/mqtt_passwd 
sudo systemctl restart mosquitto.service 

# add OA user
echo "will now add user ${cli_user} supply passowrd when asked"
sudo adduser ${cli_user}
echo "adding ${cli_user} to sudoers group"
sudo adduser ${cli_user} sudo
echo "finish off with the following"
echo "change pi user password or delete it \'sudo deluser -remove-home pi\' "
echo "go to http://$(hostname  -I | cut -f1 -d' '):3000 and setup grafana admin password for first run"
echo "then configure a data sources like this"
echo "type: infulkDB"
echo "Name InfluxDB"
echo
echo "HTTP"
echo "URL: http://localhost:8086"
echo "Access: Server"
echo
echo "Auth"
echo "Nothing set"
echo
echo "InfluxDB Details"
echo "Database: sensors"
echo "User: openans"
echo "Password: OpenAn5"
echo "Click save and test"
echo
echo "If you want to add further topics for ingest"
echo "sudo vim /etc/telegraf/telegraf.conf"
echo "Add the required topics into the list "
echo "# is wild card at the end of the topic"
echo "+ matches a single subtopic and can be placed anywhere"
echo
echo "topics = ["
echo "         "tele/ServerRoom/SENSOR/#","
echo "          "stat/ServerRoom/POWER/#","
echo "        ]"
echo "to check influxDB from command line"
echo "influx"
echo "use sensors"
echo "show field keys"
echo "SELECT BME280_Temperature FROM mqtt_consumer;"

# if you want to use the rpi for temperature monitoring as well
# setup rpi with one wire ds18b20 sensors
# pin 1 3.3v pin 7 gpio4 1 wire bus pin6 gnd
# ls /sys/bus/w1/devices
# 28-0004332d9dff 28 = device type 0004332d9dff = Device ID
# sudo apt install python-pip
# enable 1 wire on boot sudo raspi-config interfacing options -> P7 1 wire -> enable yes
# you will need to publish the 1wire device outputs to mqtt
# clone and install
# https://github.com/ijm51000/rpi-temperature-mqtt.git
#
