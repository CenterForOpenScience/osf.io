#!/bin/bash
ttab -G eval "workon osf && invoke mongo -d"
sleep 5
ttab -G eval "workon osf && invoke mailserver"
sleep 10
ttab -G eval "workon osf && invoke rabbitmq"
sleep 10
ttab -G eval "workon osf && invoke celery_worker"
sleep 10
ttab -G eval "workon osf && invoke elasticsearch"
sleep 10
ttab -G eval "workon osf && invoke assets -dw"
sleep 10
ttab -G eval "workon osf && invoke server"
