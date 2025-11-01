import logging
from datetime import datetime
from pathlib import Path

import click
import requests
from Crypto.Random import get_random_bytes

from pyplayready import InvalidCertificateChain, InvalidXmrLicense, __version__
from pyplayready.cdm import Cdm
from pyplayready.crypto.ecc_key import ECCKey
from pyplayready.crypto.key_wrap import unwrap_wrapped_key
from pyplayready.device import Device
from pyplayready.misc.exceptions import OutdatedDevice
from pyplayready.misc.revocation_list import RevocationList
from pyplayready.system.bcert import (
    BCertCertType,
    BCertFeatures,
    BCertKeyType,
    BCertKeyUsage,
    BCertObjType,
    Certificate,
    CertificateChain,
)
from pyplayready.system.pssh import PSSH


@click.group(invoke_without_command=True)
@click.option("-v", "--version", is_flag=True, default=False, help="Print version information.")
@click.option("-d", "--debug", is_flag=True, default=False, help="Enable DEBUG level logs.")
def main(version: bool, debug: bool) -> None:
    """Python PlayReady CDM implementation"""
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    log = logging.getLogger()

    current_year = datetime.now().year
    copyright_years = f"2024-{current_year}"

    log.info(
        "pyplayready version %s Copyright (c) %s DevLARLEY, Erevoc, DevataDev",
        __version__,
        copyright_years,
    )
    log.info("https://git.gay/ready-dl/pyplayready")
    log.info("Run 'pyplayready --help' for help")
    if version:
        return


@main.command(name="license")
@click.argument("device_path", type=Path)
@click.argument("pssh", type=PSSH)
@click.argument("server", type=str)
def license_(device_path: Path, pssh: PSSH, server: str) -> None:
    """
    Make a License Request to a server using a given PSSH
    Will return a list of all keys within the returned license

    Only works for standard license servers that don't use any license wrapping
    """
    log = logging.getLogger("license")

    device = Device.load(device_path)
    log.info(f"Loaded Device: {device.get_name()}")

    cdm = Cdm.from_device(device)
    log.info("Loaded CDM")

    session_id = cdm.open()
    log.info("Opened Session")

    challenge = cdm.get_license_challenge(session_id, pssh.wrm_headers[0], rev_lists=RevocationList.SupportedListIds)
    log.info("Created License Request (Challenge)")
    log.debug(challenge)

    license_response = requests.post(
        url=server,
        headers={
            "Content-Type": "text/xml; charset=UTF-8",
        },
        data=challenge,
    )

    if license_response.status_code != 200:
        log.error("Failed to send Challenge: [%s] %s", license_response.status_code, license_response.text)
        return

    licence = license_response.text
    log.debug(licence)

    try:
        cdm.parse_license(session_id, licence)
    except InvalidXmrLicense as e:
        log.error(e)
        return

    log.info("License Parsed Successfully")

    for key in cdm.get_keys(session_id):
        log.info(f"{key.key_id.hex}:{key.key.hex()}")

    cdm.close(session_id)
    log.info("Clossed Session")


@main.command()
@click.argument("device", type=Path)
@click.option(
    "-c",
    "--ckt",
    type=click.Choice(["aesctr", "aescbc"], case_sensitive=False),
    default="aesctr",
    help="Content Key Encryption Type",
)
@click.option(
    "-sl",
    "--security_level",
    type=click.Choice(["150", "2000", "3000"]),
    default="2000",
    help="Minimum Security Level",
)
@click.pass_context
def test(ctx: click.Context, device: Path, ckt: str, security_level: str) -> None:
    """
    Test the CDM code by getting Content Keys for the Tears Of Steel demo on the Playready Test Server.
    https://learn.microsoft.com/en-us/playready/advanced/testcontent/playready-2x-test-content#tears-of-steel---4k-content

    + DASH Manifest URL: https://test.playready.microsoft.com/media/profficialsite/tearsofsteel_4k.ism/manifest.mpd
    + MSS Manifest URL: https://test.playready.microsoft.com/media/profficialsite/tearsofsteel_4k.ism.smoothstreaming/manifest

    The device argument is a Path to a Playready Device (.prd) file which contains the device's group key and
    group certificate.
    """
    pssh = PSSH(
        "AAADfHBzc2gAAAAAmgTweZhAQoarkuZb4IhflQAAA1xcAwAAAQABAFIDPABXAFIATQBIAEUAQQBEAEUAUgAgAHgAbQBsAG4AcwA9ACIAaAB0AH"
        "QAcAA6AC8ALwBzAGMAaABlAG0AYQBzAC4AbQBpAGMAcgBvAHMAbwBmAHQALgBjAG8AbQAvAEQAUgBNAC8AMgAwADAANwAvADAAMwAvAFAAbABh"
        "AHkAUgBlAGEAZAB5AEgAZQBhAGQAZQByACIAIAB2AGUAcgBzAGkAbwBuAD0AIgA0AC4AMAAuADAALgAwACIAPgA8AEQAQQBUAEEAPgA8AFAAUg"
        "BPAFQARQBDAFQASQBOAEYATwA+ADwASwBFAFkATABFAE4APgAxADYAPAAvAEsARQBZAEwARQBOAD4APABBAEwARwBJAEQAPgBBAEUAUwBDAFQA"
        "UgA8AC8AQQBMAEcASQBEAD4APAAvAFAAUgBPAFQARQBDAFQASQBOAEYATwA+ADwASwBJAEQAPgA0AFIAcABsAGIAKwBUAGIATgBFAFMAOAB0AE"
        "cAawBOAEYAVwBUAEUASABBAD0APQA8AC8ASwBJAEQAPgA8AEMASABFAEMASwBTAFUATQA+AEsATABqADMAUQB6AFEAUAAvAE4AQQA9ADwALwBD"
        "AEgARQBDAEsAUwBVAE0APgA8AEwAQQBfAFUAUgBMAD4AaAB0AHQAcABzADoALwAvAHAAcgBvAGYAZgBpAGMAaQBhAGwAcwBpAHQAZQAuAGsAZQ"
        "B5AGQAZQBsAGkAdgBlAHIAeQAuAG0AZQBkAGkAYQBzAGUAcgB2AGkAYwBlAHMALgB3AGkAbgBkAG8AdwBzAC4AbgBlAHQALwBQAGwAYQB5AFIA"
        "ZQBhAGQAeQAvADwALwBMAEEAXwBVAFIATAA+ADwAQwBVAFMAVABPAE0AQQBUAFQAUgBJAEIAVQBUAEUAUwA+ADwASQBJAFMAXwBEAFIATQBfAF"
        "YARQBSAFMASQBPAE4APgA4AC4AMQAuADIAMwAwADQALgAzADEAPAAvAEkASQBTAF8ARABSAE0AXwBWAEUAUgBTAEkATwBOAD4APAAvAEMAVQBT"
        "AFQATwBNAEEAVABUAFIASQBCAFUAVABFAFMAPgA8AC8ARABBAFQAQQA+ADwALwBXAFIATQBIAEUAQQBEAEUAUgA+AA=="
    )

    license_server = f"https://test.playready.microsoft.com/service/rightsmanager.asmx?cfg=(persist:false,sl:{security_level},ckt:{ckt})"

    ctx.invoke(license_, device_path=device, pssh=pssh, server=license_server)


@main.command()
@click.option("-k", "--group_key", type=Path, help="Device ECC private group key (zgpriv.dat)")
@click.option(
    "-pk",
    "--protected_group_key",
    type=Path,
    help="Protected Device ECC private group key (zgpriv_protected.dat)",
)
@click.option(
    "-e",
    "--encryption_key",
    type=Path,
    help="Optional Device ECC private encryption key (zprivencr.dat)",
)
@click.option("-s", "--signing_key", type=Path, help="Optional Device ECC private signing key (zprivsig.dat)")
@click.option(
    "-c",
    "--group_certificate",
    type=Path,
    required=True,
    help="Device group certificate chain (bgroupcert.dat)",
)
@click.option("-o", "--output", type=Path, default=None, help="Output Path or Directory")
@click.pass_context
def create_device(
    ctx: click.Context,
    group_key: Path,
    protected_group_key: Path,
    encryption_key: Path | None,
    signing_key: Path | None,
    group_certificate: Path,
    output: Path | None = None,
) -> None:
    """Create a Playready Device (.prd) file from an ECC private group key and group certificate chain"""
    if bool(group_key) == bool(protected_group_key):
        raise click.UsageError("You must provide exactly one of group_key or protected_group_key.", ctx)
    if not group_certificate.is_file():
        raise click.UsageError("group_certificate: Not a path to a file, or it doesn't exist.", ctx)

    log = logging.getLogger("create-device")

    if group_key:
        if not group_key.is_file():
            raise click.UsageError("group_key: Not a path to a file, or it doesn't exist.", ctx)

        group_key = ECCKey.load(group_key)
    elif protected_group_key:
        if not protected_group_key.is_file():
            raise click.UsageError("protected_group_key: Not a path to a file, or it doesn't exist.", ctx)

        wrapped_key = protected_group_key.read_bytes()
        unwrapped_key = unwrap_wrapped_key(wrapped_key)
        group_key = ECCKey.loads(unwrapped_key)

    certificate_chain = CertificateChain.load(group_certificate)

    if certificate_chain.get(0).get_type() == BCertCertType.DEVICE:
        raise InvalidCertificateChain("Device has already been provisioned")

    if certificate_chain.get(0).get_type() != BCertCertType.ISSUER:
        raise InvalidCertificateChain("Leaf-most certificate must be of type ISSUER to issue certificate of type DEVICE")

    if not certificate_chain.get(0).contains_public_key(group_key):
        raise InvalidCertificateChain("Group key does not match this certificate")

    certificate_chain.verify_chain(check_expiry=True, cert_type=BCertCertType.ISSUER)

    encryption_key = ECCKey.load(encryption_key) if encryption_key else ECCKey.generate()
    signing_key = ECCKey.load(signing_key) if signing_key else ECCKey.generate()

    new_certificate = Certificate.new_leaf_cert(
        cert_id=get_random_bytes(16),
        security_level=certificate_chain.get_security_level(),
        client_id=get_random_bytes(16),
        signing_key=signing_key,
        encryption_key=encryption_key,
        group_key=group_key,
        parent=certificate_chain,
    )
    certificate_chain.prepend(new_certificate)

    certificate_chain.verify_chain(check_expiry=True, cert_type=BCertCertType.DEVICE)

    device = Device(
        group_key=group_key.dumps(),
        encryption_key=encryption_key.dumps(),
        signing_key=signing_key.dumps(),
        group_certificate=certificate_chain.dumps(),
    )

    if output and output.suffix:
        if output.suffix.lower() != ".prd":
            log.warning(f"Saving PRD with the file extension '{output.suffix}' but '.prd' is recommended.")
        out_path = output
    else:
        out_dir = output or Path.cwd()
        out_path = out_dir / f"{device.get_name()}.prd"

    if out_path.exists():
        log.error(f"A file already exists at the path '{out_path}', cannot overwrite.")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(device.dumps())

    log.info("Created Playready Device (.prd) file, %s", out_path.name)
    log.info(" + Security Level: %s", device.security_level)
    log.info(" + Group Key: %s bytes", len(device.group_key.dumps()))
    log.info(" + Encryption Key: %s bytes", len(device.encryption_key.dumps()))
    log.info(" + Signing Key: %s bytes", len(device.signing_key.dumps()))
    log.info(" + Group Certificate: %s bytes", len(device.group_certificate.dumps()))
    log.info(" + Saved to: %s", out_path.absolute())


@main.command()
@click.option(
    "-e",
    "--encryption_key",
    type=Path,
    required=True,
    help="Optional Device ECC private encryption key (zprivencr.dat)",
)
@click.option(
    "-s",
    "--signing_key",
    type=Path,
    required=True,
    help="Optional Device ECC private signing key (zprivsig.dat)",
)
@click.option(
    "-c",
    "--group_certificate",
    type=Path,
    required=True,
    help="Provisioned device group certificate chain",
)
@click.option("-o", "--output", type=Path, default=None, help="Output Path or Directory")
@click.pass_context
def build_device(
    ctx: click.Context,
    encryption_key: Path | None,
    signing_key: Path | None,
    group_certificate: Path,
    output: Path | None = None,
) -> None:
    """
    Build a V2 Playready Device (.prd) file from encryption/signing ECC private keys and a group certificate chain.
    Your group certificate chain's leaf certificate must be of type DEVICE (be already provisioned) for this to work.
    """
    if not encryption_key.is_file():
        raise click.UsageError("encryption_key: Not a path to a file, or it doesn't exist.", ctx)
    if not signing_key.is_file():
        raise click.UsageError("signing_key: Not a path to a file, or it doesn't exist.", ctx)
    if not group_certificate.is_file():
        raise click.UsageError("group_certificate: Not a path to a file, or it doesn't exist.", ctx)

    log = logging.getLogger("build-device")

    encryption_key = ECCKey.load(encryption_key)
    signing_key = ECCKey.load(signing_key)

    certificate_chain = CertificateChain.load(group_certificate)
    leaf_certificate = certificate_chain.get(0)

    if not leaf_certificate.contains_public_key(encryption_key.public_bytes()):
        raise InvalidCertificateChain("Leaf certificate does not contain encryption public key")

    if not leaf_certificate.contains_public_key(signing_key.public_bytes()):
        raise InvalidCertificateChain("Leaf certificate does not contain signing public key")

    certificate_chain.verify_chain(check_expiry=True, cert_type=BCertCertType.DEVICE)

    device = Device(
        group_key=None,
        encryption_key=encryption_key.dumps(),
        signing_key=signing_key.dumps(),
        group_certificate=certificate_chain.dumps(),
    )

    if output and output.suffix:
        if output.suffix.lower() != ".prd":
            log.warning(f"Saving PRD with the file extension '{output.suffix}' but '.prd' is recommended.")
        out_path = output
    else:
        out_dir = output or Path.cwd()
        out_path = out_dir / f"{device.get_name()}.prd"

    if out_path.exists():
        log.error(f"A file already exists at the path '{out_path}', cannot overwrite.")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(device.dumps(version=2))

    log.info("Built Playready Device (.prd) file, %s", out_path.name)
    log.info(" + Security Level: %s", device.security_level)
    log.info(" + Encryption Key: %s bytes", len(device.encryption_key.dumps()))
    log.info(" + Signing Key: %s bytes", len(device.signing_key.dumps()))
    log.info(" + Group Certificate: %s bytes", len(device.group_certificate.dumps()))
    log.info(" + Saved to: %s", out_path.absolute())


@main.command()
@click.argument("prd_path", type=Path)
@click.option("-e", "--encryption_key", type=Path, help="Optional Device ECC private encryption key")
@click.option("-s", "--signing_key", type=Path, help="Optional Device ECC private signing key")
@click.option("-o", "--output", type=Path, default=None, help="Output Path or Directory")
@click.pass_context
def reprovision_device(
    ctx: click.Context,
    prd_path: Path,
    encryption_key: Path | None,
    signing_key: Path | None,
    output: Path | None = None,
) -> None:
    """
    Reprovision a Playready Device (.prd) by creating a new leaf certificate and new encryption/signing keys.
    Will override the device if an output path or directory is not specified

    Only works on PRD Devices of v3 or higher
    """
    if not prd_path.is_file():
        raise click.UsageError("prd_path: Not a path to a file, or it doesn't exist.", ctx)

    log = logging.getLogger("reprovision-device")
    log.info("Reprovisioning Playready Device (.prd) file, %s", prd_path.name)

    device = Device.load(prd_path)

    if device.group_key is None:
        raise OutdatedDevice("Device does not support reprovisioning, re-create it or use a Device with a version of 3 or higher")

    if device.group_certificate.get(0).get_type() != BCertCertType.DEVICE:
        raise InvalidCertificateChain("Device is not provisioned")

    device.group_certificate.remove(0)

    encryption_key = ECCKey.load(encryption_key) if encryption_key else ECCKey.generate()
    signing_key = ECCKey.load(signing_key) if signing_key else ECCKey.generate()

    device.encryption_key = encryption_key
    device.signing_key = signing_key

    new_certificate = Certificate.new_leaf_cert(
        cert_id=get_random_bytes(16),
        security_level=device.group_certificate.get_security_level(),
        client_id=get_random_bytes(16),
        signing_key=signing_key,
        encryption_key=encryption_key,
        group_key=device.group_key,
        parent=device.group_certificate,
    )
    device.group_certificate.prepend(new_certificate)

    device.group_certificate.verify_chain(check_expiry=True, cert_type=BCertCertType.DEVICE)

    if output and output.suffix:
        if output.suffix.lower() != ".prd":
            log.warning(f"Saving PRD with the file extension '{output.suffix}' but '.prd' is recommended.")
        out_path = output
    else:
        out_path = prd_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(device.dumps())

    log.info("Reprovisioned Playready Device (.prd) file, %s", out_path.name)


@main.command()
@click.option("-d", "--device", type=Path, default=None, help="PRD Device")
@click.option("-c", "--chain", type=Path, default=None, help="BCert Chain (bgroupcert.dat, bdevcert.dat)")
@click.pass_context
def inspect(ctx: click.Context, device: Path | None, chain: Path | None) -> None:
    """
    Inspect a (device's) Certificate Chain to display information about each of its Certificates.
    """
    if bool(device) == bool(chain):
        raise click.UsageError("You must provide exactly one of device or chain.", ctx)

    if device:
        if not device.is_file():
            raise click.UsageError("device: Not a path to a file, or it doesn't exist.", ctx)

        device = Device.load(device)
        chai = device.group_certificate
    elif chain:
        if not chain.is_file():
            raise click.UsageError("chain: Not a path to a file, or it doesn't exist.", ctx)

        chai = CertificateChain.load(chain)
    else:
        return None  # suppress warning

    log = logging.getLogger("inspect")
    log.info("Certificate Chain Inspection:")

    log.info(f" + Version: {chai.parsed.version}")
    log.info(f" + Certificate Count: {chai.parsed.certificate_count}")

    for i in range(chai.count()):
        cert = chai.get(i)

        log.info(f"   + Certificate {i}:")

        basic_info = cert.get_attribute(BCertObjType.BASIC)
        if basic_info:
            log.info(f"     + Cert Type: {BCertCertType(basic_info.attribute.cert_type).name}")
            log.info(f"     + Security Level: SL{basic_info.attribute.security_level}")
            log.info(f"     + Expiration Date: {datetime.fromtimestamp(basic_info.attribute.expiration_date)}")
            log.info(f"     + Client ID: {basic_info.attribute.client_id.hex()}")

        model_name = cert.get_name()
        if model_name:
            log.info(f"     + Name: {model_name}")

        feature_info = cert.get_attribute(BCertObjType.FEATURE)
        if feature_info and feature_info.attribute.feature_count > 0:
            features = list(map(lambda x: BCertFeatures(x).name, feature_info.attribute.features))
            log.info(f"     + Features: {', '.join(features)}")

        key_info = cert.get_attribute(BCertObjType.KEY)
        if key_info and key_info.attribute.key_count > 0:
            key_attr = key_info.attribute
            log.info("     + Cert Keys:")
            for idx, key in enumerate(key_attr.cert_keys):
                log.info(f"       + Key {idx}:")
                log.info(f"         + Type: {BCertKeyType(key.type).name}")
                log.info(f"         + Key Length: {key.length} bits")
                usages = list(map(lambda x: BCertKeyUsage(x).name, key.usages))
                if len(usages) > 0:
                    log.info(f"         + Usages: {', '.join(usages)}")

    return None


@main.command()
@click.argument("prd_path", type=Path)
@click.option("-o", "--out_dir", type=Path, default=None, help="Output Directory")
@click.pass_context
def export_device(ctx: click.Context, prd_path: Path, out_dir: Path | None = None) -> None:
    """
    Export a Playready Device (.prd) file to a Group Key and Group Certificate
    If an output directory is not specified, it will be stored in the current working directory
    """
    if not prd_path.is_file():
        raise click.UsageError("prd_path: Not a path to a file, or it doesn't exist.", ctx)

    log = logging.getLogger("export-device")
    log.info("Exporting Playready Device (.prd) file, %s", prd_path.stem)

    if not out_dir:
        out_dir = Path.cwd()

    out_path = out_dir / prd_path.stem
    if out_path.exists():
        if any(out_path.iterdir()):
            log.error("Output directory is not empty, cannot overwrite.")
            return
        else:
            log.warning("Output directory already exists, but is empty.")
    else:
        out_path.mkdir(parents=True)

    device = Device.load(prd_path)

    log.info(f"SL{device.security_level} {device.get_name()}")
    log.info(f"Saving to: {out_path}")

    if device.group_key:
        group_key_path = out_path / "zgpriv.dat"
        group_key_path.write_bytes(device.group_key.dumps(private_only=True))
        log.info("Exported Group Key as zgpriv.dat")
    else:
        log.warning("Cannot export zgpriv.dat, as v2 devices do not save the group key")

    # remove leaf cert to unprovision it
    device.group_certificate.remove(0)

    client_id_path = out_path / "bgroupcert.dat"
    client_id_path.write_bytes(device.group_certificate.dumps())
    log.info("Exported Group Certificate to bgroupcert.dat")


@main.command("serve", short_help="Serve your local CDM and Playready Devices remotely.")
@click.argument("config_path", type=Path)
@click.option("-h", "--host", type=str, default="127.0.0.1", help="Host to serve from.")
@click.option("-p", "--port", type=int, default=7723, help="Port to serve from.")
def serve_(config_path: Path, host: str, port: int) -> None:
    """
    Serve your local CDM and Playready Devices Remotely.

    [CONFIG] is a path to a serve config file.
    See `serve.example.yml` for an example config file.

    Host as 127.0.0.1 may block remote access even if port-forwarded.
    Instead, use 0.0.0.0 and ensure the TCP port you choose is forwarded.
    """
    import yaml

    from pyplayready.remote import serve

    config = yaml.safe_load(config_path.read_text(encoding="utf8"))
    serve.run(config, host, port)
