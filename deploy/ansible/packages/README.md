# CODESYS Runtime Packages

This directory should contain the CODESYS runtime installation packages
for each target architecture. These are NOT committed to git (large binaries).

## Required Files

- `codesyscontrol_linux_3.5.20.0_arm64.deb` — For ARM64 IPCs (WAGO PFC200, RevPi)
- `codesyscontrol_linux_3.5.20.0_amd64.deb` — For x86_64 IPCs (Beckhoff CX)

## How to Obtain

1. Download from CODESYS Store: https://store.codesys.com/
2. Product: "CODESYS Control for Linux SL"
3. Place the .deb files in this directory before running Ansible

## Alternative: Fetch from S3 at Runtime

Instead of committing packages, the playbook can fetch from S3:
```yaml
- name: Download CODESYS runtime from S3
  aws_s3:
    bucket: aifactory-packages
    object: "codesys/{{ codesys_runtime_package }}"
    dest: "/tmp/{{ codesys_runtime_package }}"
    mode: get
```

Set `codesys_package_source: s3` in inventory vars to use this method.
