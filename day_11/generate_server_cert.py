#!/usr/bin/env python3
"""
Generate ThingsBoard Server SSL Certificate
"""
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import datetime
import os
import ipaddress

OUTPUT_DIR = "tb_ssl"

def main():
    print("🔐 Generating ThingsBoard Server Certificate...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    key = rsa.generate_private_key(65537, 2048, default_backend())
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ThingsBoard"),
        x509.NameAttribute(NameOID.COMMON_NAME, "thingsboard.local"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
        key.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.now(datetime.UTC)
    ).not_valid_after(
        datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3650)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("thingsboard"),
            x509.IPAddress(ipaddress.IPv4Address("192.168.1.95")),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(key, hashes.SHA256(), default_backend())
    
    with open(os.path.join(OUTPUT_DIR, "server.pem"), "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    with open(os.path.join(OUTPUT_DIR, "server-key.pem"), "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()
        ))
    
    print("✅ tb_ssl/server.pem")
    print("✅ tb_ssl/server-key.pem")

if __name__ == "__main__":
    main()
