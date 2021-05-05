# Production Setup: SSL Encryption

Before running in production, it is necessary to setup a SSL certificate. A self-signed certificate can be created using the following commands. Other options include purchasing a certificate or using [LetsEncrypt](https://letsencrypt.org/) for a free certificate.

Certificates should be placed in the `ssl/` folder. The files referenced in `compose/nginx/nginx.conf` use the following files names:

- ghostwriter.crt
- ghostwriter.key
- dhparam.pem

If different filenames are used, update the `nginx.conf` to reflect the correct filenames.

## Creating a self-signed SSL certificate

### With Prompts

```
openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -keyout ghostwriter.key -out ghostwriter.crt
```

### Without Prompts

```
openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj "/C=/ST=/L=/O=Ghostwriter/CN=ghostwriter.local" -keyout ghostwriter.key -out ghostwriter.crt
```

### Creating the dhparam.pem

```
openssl dhparam -out dhparam.pem 4096
```
