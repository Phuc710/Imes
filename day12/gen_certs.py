"""
X.509 Certificate Generator for ESP32 + ThingsBoard Auto-Provisioning
Generates CA certificate and device certificates based on MAC address
"""

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta
import os

# Configuration
CA_COMMON_NAME = "ThingsBoard Root CA"
CA_ORGANIZATION = "ThingsBoard"
CA_COUNTRY = "VN"
VALIDITY_DAYS = 3650  # 10 years

# Device configuration (example MAC address)
DEVICE_MAC = "A842E3578AD4"  # Change this to your ESP32 MAC address

def generate_ca_certificate():
    """Generate Root CA certificate and private key"""
    print("🔐 Generating Root CA certificate...")
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Create certificate subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, CA_COUNTRY),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, CA_ORGANIZATION),
        x509.NameAttribute(NameOID.COMMON_NAME, CA_COMMON_NAME),
    ])
    
    # Build certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=VALIDITY_DAYS))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )
    
    return cert, private_key

def generate_device_certificate(ca_cert, ca_key, device_mac):
    """Generate device certificate signed by CA"""
    print(f"📱 Generating device certificate for MAC: {device_mac}...")
    
    # Generate device private key
    device_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Create device certificate subject (CN = MAC address)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, CA_COUNTRY),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ESP32 Devices"),
        x509.NameAttribute(NameOID.COMMON_NAME, device_mac),  # CRITICAL: Must match MAC
    ])
    
    # Build device certificate
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(device_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=VALIDITY_DAYS))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    
    return cert, device_key

def save_certificate(cert, filename):
    """Save certificate to PEM file"""
    with open(filename, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"✅ Saved: {filename}")

def save_private_key(key, filename):
    """Save private key to PEM file"""
    with open(filename, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"✅ Saved: {filename}")

def main():
    print("=" * 60)
    print("🔒 X.509 Certificate Generator for ThingsBoard + ESP32")
    print("=" * 60)
    
    # Create certs directory if it doesn't exist
    os.makedirs("certs", exist_ok=True)
    os.makedirs("tb_ssl", exist_ok=True)
    
    # Generate CA certificate
    ca_cert, ca_key = generate_ca_certificate()
    save_certificate(ca_cert, "certs/root_ca.pem")
    save_certificate(ca_cert, "tb_ssl/rootCert.pem")  # Copy for ThingsBoard
    save_private_key(ca_key, "certs/root_ca.key")
    
    print("\n" + "=" * 60)
    
    # Generate device certificate
    device_cert, device_key = generate_device_certificate(ca_cert, ca_key, DEVICE_MAC)
    save_certificate(device_cert, f"certs/{DEVICE_MAC}.crt")
    save_private_key(device_key, f"certs/{DEVICE_MAC}.key")
    
    print("\n" + "=" * 60)
    print("✨ Certificate generation complete!")
    print("=" * 60)
    print("\n📋 Next steps:")
    print("1. Paste content of 'certs/root_ca.pem' into ThingsBoard Device Profile")
    print("2. Copy device cert and key to ESP32 code (esp32_certs.h)")
    print("3. Start ThingsBoard: docker-compose up -d")
    print("4. Flash ESP32 with updated firmware")
    print("\n⚠️  SECURITY WARNING:")
    print("   - NEVER upload 'root_ca.key' to ThingsBoard!")
    print("   - Keep CA private key secure and offline in production")
    print("=" * 60)

if __name__ == "__main__":
    main()
