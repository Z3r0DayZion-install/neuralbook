## Security model (build artifacts)

NeuralBook build artifacts form a **trust chain**:

- **Manifest**: hashes of encrypted outputs and a root hash.
- **Provenance**: describes inputs + links to manifest; includes build fingerprint and signatures.
- **Attestation**: summary linking manifest/provenance + CI context.

### Signing + verification policy

- **Demo/Internal builds** may be verified using the embedded public key inside provenance.
- **Release/External builds** are **strict by default**:
  - provenance must be signed
  - verification requires a **trusted key registry** (and optional revocations list)

### Key rotation

- Assign each signing key a stable **`key_id`** (e.g. `primary-2026-04`, `escrow-1`).
- Add the new public key to `trusted-keys.json` before switching signers.
- Keep old keys in the registry until all consumers have upgraded.

### Revocation

- Add compromised/deprecated key ids to `revocations.json`.
- Verification will fail for any signature with a revoked `key_id`.

### Multi-signer (recommended for release)

Provenance supports multiple signatures (`signatures[]`). Typical pattern:

- **primary**: main release key
- **escrow**: offline/secondary key
- **ci**: ephemeral CI signing key (optional)

