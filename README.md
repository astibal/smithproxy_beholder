# Beholder - Smithproxy traffic controller

Beholder is PyQt application running webhook service for Smithproxy.   
It's designed to receive webhook requests and perform configured actions.

Content Tab: custom scripts can process or modify proxied traffic, capture samples
Workbench Tab: test your scripts offline
Connections Tab: see active and past connections list
Remotes: let you configure smithproxy hosts to connect
Logs: collect application logs on demand

## Mandatory Smithproxy webhook configuration

Simplest possible configuration:
```cfg
settings =   
  webhook = 
  {
    enabled = true
    url = "http://127.0.0.1:5000/webhook/<secret_string>"
    tls_verify = true
    hostid = ""
  }
}
```
Note: this config is very easy to configure in Smithproxy CLI

## Payload processing / modification
Beholder can receive 'content' webhook messages. Those are specific
requests containing L7 payload data, asking Beholder to display or modify them.
They can be modified in the app and sent back to proxy to replace original payload.  

Process of discovering traffic payload is simple, but multi-stage. It can be very
manual, but after script refinement it can run automatically.  

### Content replacement configuration

#### 1. have content profile with at least one match rule
```cfg
content_profiles = 
{
  wh = 
  {
    write_payload = true
    write_format = "pcap_single"
    webhook_enable = true             # <<< enable webhook content messages
    webhook_lock_traffic = true       # <<< "lock" the rest of the traffic before getting result 
    content_rules = ( ) 
  }
}
```
Important are `webhook_` settings. 

#### 2. apply content profile on policy
```cfg
policy = ( 
  {
    disabled = false
    name = "root"
    proto = "tcp"
    src = [ "any" ]
    sport = [ "all" ]
    dst = [ "root_cz" ]
    dport = [ "all" ]
    features = [ ]
    action = "accept"
    nat = "auto"
    routing = "none"
    tls_profile = "default"
    detection_profile = "detect"
    content_profile = "wh"                   # <<<< THIS
    auth_profile = "resolve"
    alg_dns_profile = "dns_default"
  },
}
```

Again, policy content-profile can be set in smithproxy CLI.