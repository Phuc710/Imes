from cryptography import x509
from cryptography.hazmat.backends import default_backend

def analyze_cert(file_path):
    with open(file_path, "rb") as f:
        cert_data = f.read()
    
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    
    print(f"Subject: {cert.subject}")
    print(f"Issuer: {cert.issuer}")
    print(f"Serial Number: {cert.serial_number}")
    print(f"Not Before: {cert.not_valid_before}")
    print(f"Not After: {cert.not_valid_after}")
    
    # Check for Basic Constraints
    try:
        ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.BASIC_CONSTRAINTS)
        print(f"Basic Constraints: {ext.value}")
    except x509.extensions.ExtensionNotFound:
        print("Basic Constraints: Not found")

if __name__ == "__main__":
    analyze_cert("pasted_cert.pem")
