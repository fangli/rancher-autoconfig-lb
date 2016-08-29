FROM python:2.7-alpine

RUN pip install requests
ADD src/* /var/lib/rancher-autoconfig-lb/

WORKDIR /var/lib/rancher-autoconfig-lb/
CMD python -u rancher-autoconfig-lb.py
