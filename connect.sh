#!/bin/bash

echo Trying to connect to the pi...
until nmcli dev wifi connect wifiedu
do
    PAGER="" nmcli device wifi list --rescan yes
    echo "Trying again"
done

ssh pi@10.0.0.1