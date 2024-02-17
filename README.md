# How to set up a captive portal on a Raspberry Pi

# Introduction

This tutorial explains how I set up a custom captive portal on a Raspberry Pi. The methods described here are not secured and don't aim to be, this is just some of my findings. I used an existing captive portal page from my school as a demonstration. Don't use this to steal the passwords of people you don't know without their consent. Have fun!

I suggest doing the first part of the configuration using `ssh` over Ethernet.

# Online mode
Raspberry connected to the internet via ethernet

## Set up the Raspberry as a routed wireless Access Point
Source: [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/computers/configuration.html#host-a-wireless-network-on-your-raspberry-pi)

> _**Note:**_ It seems like the documentation and the recommended way to do this part has changed. Try the new version at your own risk.


### Install AP and management software
Update the pi and download hostapd, dnsmasq, netfilter-persistent and iptables-persistent:

    sudo apt update
    sudo apt full-upgrade
    sudo apt install hostapd dnsmasq
    sudo DEBIAN_FRONTEND=noninteractive apt install -y netfilter-persistent iptables-persistent

Enable hostapd:

    sudo systemctl unmask hostapd
    sudo systemctl enable hostapd

### Set the wireless interface IP configuration
Edit the configuration file:

    sudo nano /etc/dhcpcd.conf

Add the following to the end of the file:

    interface wlan0
        static ip_address=10.0.0.1/24
        nohook wpa_supplicant

### Enable routing and IP masquerading
Edit the configuration file:
    
    sudo nano /etc/sysctl.d/routed-ap.conf

Paste this into it:

    # Enable IPv4 routing
    net.ipv4.ip_forward=1

Add a firewall rule:

    sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE


> _**Note:**_ If you get this error: `iptables/1.8.7 Failed to initialize nft: Protocol not supported`, try rebooting the pi  (`sudo reboot`)

Make this configuration persistent:

    sudo netfilter-persistent save

### Configure the DHCP and DNS services for the wireless network
Rename the default configuration file and create a new one:

    sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig
    sudo nano /etc/dnsmasq.conf

Add the following to the file and save it:

    # Listening interface
    interface=wlan0

    # Pool of IP addresses served via DHCP
    dhcp-range=10.0.0.2, 10.0.0.20, 255.255.255.0, 24h
    
    # Local wireless DNS domain
    domain=wlan     
    
    # Alias for this router
    address=/gw.wlan/10.0.0.1

### Ensure wireless operation
To ensure WiFi is not blocked on your Raspberry Pi, execute the following command:

    sudo rfkill unblock wlan

### Configure the AP software
Open the configuration file:

    sudo nano /etc/hostapd/hostapd.conf

Insert the following lines to create an open network with the name "wifiedu"

    country_code=CH
    interface=wlan0
    ssid=wifiedu
    hw_mode=g
    channel=7
    macaddr_acl=0
    auth_algs=1
    ignore_broadcast_ssid=0

### Restart

    sudo reboot

You should now see a network called "wifiedu". You should be able to connect to it and access the internet (provided the pi is connected through ethernet).
You can now also connect to the Raspberry directly if you are on its network:

    ssh pi@10.0.0.1


## Compile openNDS for the Raspberry
Source: [openNDS Documentation](https://opennds.readthedocs.io/en/stable/compile.html#linux-unix-compile-in-place-on-target-hardware)

### Creating a temporay directory

    mkdir opennds-compile
    cd opennds-compile/

### Get libmicrohttpd
Run these two commands two download the latest version of libmicrohttpd:

    wget https://ftp.gnu.org/gnu/libmicrohttpd/libmicrohttpd-latest.tar.gz
    tar  -xf libmicrohttpd-latest.tar.gz
    rm libmicrohttpd-latest.tar.gz

Go to the new directory:
    
    cd libmicrohttpd-*

Compile libmicrohttpd:

    ./configure --disable-https
    make
    sudo rm /usr/local/lib/libmicrohttpd*
    sudo make install
    sudo rm /etc/ld.so.cache
    sudo ldconfig -v
    cd ..

### Get openNDS
Run:

    wget https://codeload.github.com/opennds/opennds/tar.gz/v9.9.1
    tar -xf v9.9.1
    cd openNDS-9.9.1
    make
    sudo make install
    cd ..

openNDS should now be installled on your system.

### Finishing up
Remove build artifacts:

    cd ..
    rm -r opennds-compile

Enable the opennds service:

    sudo systemctl enable opennds

## Fix the default configuration

### Change the network interface name
openNDS is now installed, but it is configured for routers using OpenWrt.
We need to fix a few things before we continue.
First, open the configuration file for openNDS:

    sudo nano /etc/opennds/opennds.conf

Change the name of the network interface. 
Remove the "#" at the start of this line to uncomment it:

    #GatewayInterface wlan0

### Fix the service file
Now, for some reasons, the openNDS service often fails to start.
The fix I found is to change the service configuration file.
Open the file:

    sudo nano /etc/systemd/system/opennds.service

Add this in the `[Service]` section:

    StartLimitInterval=3

Your file should look something like this:

    [Unit]
    Description=openNDS Captive Portal
    After=network.target

    [Service]
    Type=forking
    ExecStart=/usr/bin/opennds $OPTIONS
    Restart=on-failure
    StartLimitInterval=3

    [Install]
    WantedBy=multi-user.target

Save your changes by running this command:

    sudo systemctl daemon-reload

If your restart your Raspberry, you should now see OpenNDS default captive portal appear when trying to connect to the pi.

    sudo reboot


## How to check openNDS status
The status of openNDS can be checked with the following command:

    sudo ndsctl status

On most Linux distributions you can read the last entries for openNDS in the system message log with the command:

    sudo systemctl status opennds

If openNDS fails to start, check for error messages with the command:

    sudo journalctl -e

You can also increase the quantity of debug messages of openNDS by adding this line to `/etc/opennds/opennds.conf`:

    DebugLevel 3


## Use a custom web page
Great, you now have a captive portal!
But what if you want to show your own custom page instead?
To do this, you could use openNDS ThemSpecs settings.
However, I think it is much easier to use FAS (Forward Authentication Service) instead.

> _**Note:**_ In this example, we will use FAS in secure mode 0
>             This means that the authentication can easily be bypassed.
>             Consider using another authentification mode instead.

### Update openNDS configuration
To start with, we need to modify again the openNDS configuration file:

    sudo nano /etc/opennds/opennds.conf

Add this at the end of the file:

    fasport 8000
    faspath /
    fas_secure_enabled 0

### Create a web server to serve the splash page
Now, whenever someone tries to connect to the network, the connecting device will send an http request to our Raspberry on port 8000.
We need to answer with our splash page. 

Copy the content of `webserver` to the Raspberry:

    scp -r webserver pi@10.0.0.1:

### Setting up the webpage service
Source: [The linux handbook](https://linuxhandbook.com/create-systemd-services/)

Then, we need to make sure that our server starts when the Raspberry boots.
To do this, create a new service:

    sudo nano /etc/systemd/system/captive-portal.service

Paste this inside the newly created file:

    [Unit]
    Description=Captive Portal Server
    After=network-online.target

    [Service]
    Type=idle
    ExecStart=/usr/bin/python3 /home/pi/webserver/server.py
    WorkingDirectory=/home/pi/webserver
    Restart=always

    [Install]
    WantedBy=multi-user.target

Finally, enable the service, reboot and your captive portal should be done!

    sudo systemctl enable captive-portal
    sudo reboot

## Conclusion
Congratulation, you now have created a Raspberry Pi router with a Captive Portal!

# Offline mode
Source: [openNDS Issues](https://github.com/openNDS/openNDS/issues/170#issuecomment-851065691)

When you are not connected to the internet, things are a lot different if you want to show a captive portals to users. First, we wont need `opennds` in this part, because we dont need to protect our precious Internet on eth0 since we are not connected to anything. What we are going to do instead is send all http traffic to a python http server, similar to the one we already created before. This server is going to redirect users to our captive portal address, serve the captive portal page and fake Internet access to connected users. However, in order to achieve this, we first need to resolve all dns queries to our server ip and route all http requests to our python program. 
If you skipped the first part of this tutorial, I suggest following the first steps about making your Raspberry Pi into an AP, but you don't need to compile opennds and libmicrohttpd.

## Resolve all DNS queries to our ip
Source: [serverfault.com](https://serverfault.com/questions/351108/using-dnsmasq-to-resolve-all-hosts-to-the-same-address)

Add this at the end of `/etc/dnsmasq.conf`:

    # Added to resolve all dns queries to this router 
    address=/#/10.0.0.1

## Route all http requests to the python server
Source: [This very informative pdf](https://cdn.rootsh3ll.com/captive-portal/captive+portal+guide+-+rootsh3ll.pdf) on which most of this section is based.

We will do this by modifying the `iptables`. However, if you already mess with them in the previous part of the tutorial, I suggest removing those previous rules:
   
    sudo netfilter-persistent flush

Then, set the new routing rule:

    sudo iptables -t nat -A PREROUTING -d 0/0 -p tcp --dport 80 -j DNAT --to-destination 10.0.0.1:8000

And make it persistent again:

    sudo netfilter-persistent save

## The custom server
Finally, copy over the custom server:

        scp -r webserver-offline pi@10.0.0.1:

Now, if we manually start the server, everything should work. However, we want it to start automatically at boot time, so create yet another service:    

    sudo nano /etc/systemd/system/offline-captive-portal.service

Add this to the file as usual, but don't forget to change the description and file path:

    [Unit]
    Description=Offline Captive Portal Server
    After=network-online.target

    [Service]
    Type=idle
    ExecStart=/usr/bin/python3 /home/pi/eel-capo/webserver-offline/server.py
    WorkingDirectory=/home/pi/eel-capo/webserver-offline
    Restart=always

    [Install]
    WantedBy=multi-user.target

Tell systemd to read our service file:

    sudo systemctl daemon-reload

Finally, disable the previous server (if needed) and enable our new one:

    sudo systemctl disable captive-portal.service
    sudo systemctl enable offline-captive-portal.service

# Conclusion

Check this out for other ideas: https://www.dinofizzotti.com/blog/2022-04-24-running-a-man-in-the-middle-proxy-on-a-raspberry-pi-4/ 
