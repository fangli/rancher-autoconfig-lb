# rancher-autoconfig-lb
Auto configure plugin for rancher load balancer

Rancher Autoconfig LB
=====================

Launch this image with the following labels:

**Labels**

    io.rancher.container.create_agent: true
    io.rancher.container.agent.role: environment
    autoconfig.proxy.service_name: your-proxy-name


Services Labels
===============

If you want to add services with auto proxy configuration, add the following labels:

**Labels**

    autoconfig.proxy.domain:  example.com:80/path=81

If you want to add multiple domains, use ';' as seperator.

The format of domain values see:

[SYNTAX OF THE COMBINATION OF ALL OPTIONAL FIELDS](http://docs.rancher.com/rancher/v1.1/zh/cattle/adding-load-balancers/#syntax-of-the-combination-of-all-optional-fields)