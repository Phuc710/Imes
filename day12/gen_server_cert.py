"""
Generate Server Certificate for ThingsBoard MQTT SSL
This creates the server certificate that ThingsBoard needs to accept SSL connections
"""

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta, timezone
import ipaddress
import os

# Configuration
CA_COMMON_NAME = "ThingsBoard Root CA"
SERVER_COMMON_NAME = "thingsboard"  # or your server IP/hostname
CA_COUNTRY = "VN"
VALIDITY_DAYS = 3650  # 10 years

def load_ca_certificate():
    """Load existing CA certificate and private key"""
    print("📂 Loading CA certificate and key...")
    
    with open("certs/root_ca.pem", "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
    
    with open("certs/root_ca.key", "rb") as f:
        ca_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    
    print("✅ CA certificate loaded")
    return ca_cert, ca_key

def generate_server_certificate(ca_cert, ca_key, server_name):
    """Generate server certificate signed by CA"""
    print(f"🖥️  Generating server certificate for: {server_name}...")
    
    # Generate server private key
    server_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Create server certificate subject
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, CA_COUNTRY),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ThingsBoard"),
        x509.NameAttribute(NameOID.COMMON_NAME, server_name),
    ])
    
    # Build server certificate with SAN (Subject Alternative Names)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=VALIDITY_DAYS))
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
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(server_name),
                x509.DNSName("localhost"),
                x509.DNSName("thingsboard"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address("192.168.1.95")),  # Your ThingsBoard IP
            ]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    
    return cert, server_key

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
    print("🔐 ThingsBoard Server Certificate Generator")
    print("=" * 60)
    
    # Create tb_ssl directory if it doesn't exist
    os.makedirs("tb_ssl", exist_ok=True)
    
    # Load CA certificate
    ca_cert, ca_key = load_ca_certificate()
    
    print("\n" + "=" * 60)
    
    # Generate server certificate
    server_cert, server_key = generate_server_certificate(ca_cert, ca_key, SERVER_COMMON_NAME)
    save_certificate(server_cert, "tb_ssl/server.pem")
    save_private_key(server_key, "tb_ssl/server-key.pem")
    
    print("\n" + "=" * 60)
    print("✨ Server certificate generation complete!")
    print("=" * 60)
    print("\n📋 Next steps:")
    print("1. Restart ThingsBoard: docker-compose restart thingsboard")
    print("2. Check ThingsBoard logs: docker-compose logs -f thingsboard")
    print("3. ESP32 should now connect successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
