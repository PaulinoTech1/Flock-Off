# Release signing

How Flock-Off dataset releases are cryptographically signed, and what the
signature does and does not prove.

## What the manifest binds

`data/integrity/manifest.json` binds one dataset release to:

- `agencies_sha256`: SHA-256 of `data/agencies.json` (byte-exact),
- `timestamp`: UTC time the manifest was generated,
- `commit`: the git commit the hash was taken at (null in this tree, which
  has no local `.git`; the audit log records the commit per change),
- `signer`: SHA-256 fingerprint of the maintainer's public key,
- `signature`: detached SSH signature (`ssh-keygen -Y sign`, namespace
  `flock-off-dataset`) over the canonical unsigned payload.

Anyone can recompute the dataset hash client-side (the Tools tab
"Verify data integrity" widget does this) and compare it to the manifest.
The signature additionally binds the manifest to the maintainer's key.

What the signature does NOT prove: that the hosting origin is
uncompromised. A compromised host could serve a matching dataset+manifest
pair. The signature proves the release came from the key holder, not that
the server is honest.

## What the signature means (read this)

The release key is a **pipeline key**, not a personal key. The signature
attests: "the Flock-Off release pipeline produced this manifest from the
dataset state approved in review." It does **not** mean a human personally
re-verified every record in the release.

Human approval happens at the batch level: quarantined and changed items
are reviewed in bulk (weekly review), and the audit log records the actor
and the exact diff for every dataset change. The signature binds the
release to the pipeline; the audit log binds the release to the human
decision. Neither half claims what the other provides.

## Key setup

The private key is a dedicated single-purpose keypair generated on the
release VM. It is not a personal SSH key and is not used for anything
else. It lives at `~/.ssh/flock-off-release` (0600), outside the repo, and
is never copied into chat, logs, or the repository.

```sh
ssh-keygen -t ed25519 -f ~/.ssh/flock-off-release -N "" -C "flock-off-release-bot"
chmod 600 ~/.ssh/flock-off-release
```

The key path is configured once via the environment, not per command:

```sh
# ~/.config/flock-off/release.env (also sourced from ~/.profile)
export FLOCK_OFF_SIGNING_KEY="$HOME/.ssh/flock-off-release"
```

Publish the public half at `data/integrity/pubkey.pub` in the repo
(verbatim contents of `~/.ssh/flock-off-release.pub`).

Until `pubkey.pub` exists, releases are unsigned (bootstrap mode): the
test suite skips signature checks and the push gate warns. The moment
`pubkey.pub` is published, both go fail-closed: an unsigned or
badly-signed manifest blocks the release.

Threat model, stated plainly: anyone with read access to the release VM
can sign releases with this key. A VM compromise defeats the signature.
The mitigation is key rotation (below), not secrecy theater: the key's
value is pipeline integrity (detecting tampering between signing and
serve), not personal non-repudiation.

## Streamlined release

With the key configured, signing is one step, no ceremony:

```sh
python3 scripts/sign_manifest.py --sign     # key from $FLOCK_OFF_SIGNING_KEY
```

Or the full one-command release (validate, sign, push):

```sh
python3 scripts/flockoff.py release --message "Weekly review 2026-09-28"
```

The push gate re-verifies the signature before anything goes out. See
`--dry-run` on the release command to rehearse without pushing.

## Manual ceremony (fallback)

If the pipeline key is unavailable (rotation window, key host down), the
release can still be signed by hand. The private key never leaves the
signer's machine, and no agent in the release pipeline ever sees it:

1. **Pipeline** (after the dataset is final, before push):

   ```sh
   python3 scripts/sign_manifest.py --payload-out /tmp/release-payload.bin
   ```

   This writes the unsigned manifest and the exact canonical bytes the
   signature must cover. Send `/tmp/release-payload.bin` to the maintainer
   (any channel; it is public data).

2. **Maintainer** (their own machine, their own key):

   ```sh
   ssh-keygen -Y sign -f ~/.ssh/flock-off-release -n flock-off-dataset \
     < release-payload.bin > manifest.sig
   ```

   `manifest.sig` is public signature armor. Safe to send back over any
   channel. The private key is only ever read by `ssh-keygen` locally.

3. **Pipeline** (embed + verify + push):

   ```sh
   python3 scripts/sign_manifest.py --embed-sig manifest.sig \
     --pubkey data/integrity/pubkey.pub
   ```

   This embeds the armor, records the signer's key fingerprint, verifies,
   and writes the manifest. **It refuses to write if verification fails**,
   leaving any previous manifest untouched.

Then push normally. The push gate re-verifies the signature before any
data release goes out.

## Verifying a release (anyone)

```sh
python3 -c "
import json
m = json.load(open('data/integrity/manifest.json'))
sig = m.pop('signature'); m['signer'] = None; m['signature'] = None
open('/tmp/payload','wb').write(json.dumps(m, sort_keys=True,
    separators=(',',':')).encode())
open('/tmp/sig.asc','w').write(sig)"
printf 'flock-off-maintainer %s\n' "$(cat data/integrity/pubkey.pub)" \
  > /tmp/allowed_signers
ssh-keygen -Y verify -f /tmp/allowed_signers -I flock-off-maintainer \
  -n flock-off-dataset -s /tmp/sig.asc < /tmp/payload
```

Or: `python3 scripts/sign_manifest.py --verify --pubkey data/integrity/pubkey.pub`.

## Why commits are unsigned (and why that is acceptable)

Pushes go through GitHub's Git Data API (`flock-off-deploy/github_push.py`;
this tree has no local `.git`). Commits created via that API cannot carry
the pusher's GPG/SSH signature: GitHub only renders `Verified` for commits
made in the web UI (signed by GitHub's own key) or for locally-signed
commits pushed over the git protocol. This is a platform limitation, not a
configuration gap.

The signed release manifest is therefore the trust anchor for dataset
integrity, not the commit badge. If verified commits are ever required, the
push workflow must move to local git on the maintainer's machine with their
signing key, and the maintainer runs pushes themselves. That trade is
documented here so it is a conscious decision, not drift.

## Rotation

Generate a new keypair on the release VM, point `FLOCK_OFF_SIGNING_KEY` at
it, replace `data/integrity/pubkey.pub`, and sign the next release with
the new key. Delete the old private key from the VM. Old manifests remain
verifiable against the old public key, which stays in the repo history;
never rewrite history to erase it.
