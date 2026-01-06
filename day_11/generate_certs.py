#!/usr/bin/env python3
"""
Generate X.509 Certificate Chain for ESP32
"""
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import datetime
import os

DEVICE_NAME = "A842E3578AD4"  # Real MAC from ESP32
VALIDITY_DAYS = 3650
OUTPUT_DIR = "certs"

def gen_key():
    return rsa.generate_private_key(65537, 2048, default_backend())

def save_pem(name, data, is_key=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, name)
    with open(path, "wb") as f:
        if is_key:
            f.write(data.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()
            ))
        else:
            f.write(data.public_bytes(serialization.Encoding.PEM))
    print(f"✅ {path}")

def create_root():
    key = gen_key()
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ThingsBoard"),
        x509.NameAttribute(NameOID.COMMON_NAME, "ThingsBoard Root CA"),
    ])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
        key.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.now(datetime.UTC)
    ).not_valid_after(
        datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=VALIDITY_DAYS)
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=1), critical=True
    ).sign(key, hashes.SHA256(), default_backend())
    return cert, key

def create_intermediate(root_cert, root_key):
    key = gen_key()
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ThingsBoard"),
        x509.NameAttribute(NameOID.COMMON_NAME, "ESP32-Devices"),
    ])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(
        root_cert.subject
    ).public_key(key.public_key()).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.UTC)
    ).not_valid_after(
        datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=VALIDITY_DAYS)
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=0), critical=True
    ).sign(root_key, hashes.SHA256(), default_backend())
    return cert, key

def create_device(int_cert, int_key, name):
    key = gen_key()
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ThingsBoard"),
        x509.NameAttribute(NameOID.COMMON_NAME, name),
    ])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(
        int_cert.subject
    ).public_key(key.public_key()).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.UTC)
    ).not_valid_after(
        datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=VALIDITY_DAYS)
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True
    ).add_extension(
        x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]), critical=True
    ).sign(int_key, hashes.SHA256(), default_backend())
    return cert, key

def to_c_string(name, data):
    lines = data.decode().strip().split('\n')
    code = f'const char* {name} = \n'
    for line in lines:
        code += f'  "{line}\\n"\n'
    return code + '  ;\n'

def main():
    print("🔐 Generating X.509 Certificate Chain...")
    
    root_cert, root_key = create_root()
    int_cert, int_key = create_intermediate(root_cert, root_key)
    dev_cert, dev_key = create_device(int_cert, int_key, DEVICE_NAME)
    
    save_pem("rootCert.pem", root_cert)
    save_pem("intermediateCert.pem", int_cert)
    save_pem("deviceCert.pem", dev_cert)
    save_pem("deviceKey.pem", dev_key, True)
    
    chain = (dev_cert.public_bytes(serialization.Encoding.PEM) +
             int_cert.public_bytes(serialization.Encoding.PEM) +
             root_cert.public_bytes(serialization.Encoding.PEM))
    
    with open(os.path.join(OUTPUT_DIR, "chain.pem"), "wb") as f:
        f.write(chain)
    print(f"✅ {OUTPUT_DIR}/chain.pem")
    
    key_pem = dev_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()
    )
    
    header = to_c_string("device_cert_chain", chain)
    header += "\n" + to_c_string("device_key", key_pem)
    
    with open(os.path.join(OUTPUT_DIR, "esp32_certs.h"), "w") as f:
        f.write(header)
    print(f"✅ {OUTPUT_DIR}/esp32_certs.h")
    
    print("\n📋 Next: Upload 'intermediateCert.pem' to ThingsBoard")
    print("📋 CN Regex: (.*)")  # Match any device name

if __name__ == "__main__":
    main()
