# assets/

## `pack.png`

The icon that `tools/build.py` writes into every artifact as `pack.png`. It is a **build input**,
not a generated artifact — delete it and the build stops.

This is the icon of *this port*, not the upstream one. Upstream ships a 128×128 icon and keeps its
Photoshop master in `SourceCode/icon.zip` as `icon.psd`; this port uses a different 96×96 icon, so
it cannot be taken from the upstream pack and has to live in the repository.

96×96 is accepted by the game, which scales the icon to fit, but 128×128 is the conventional size.
Replacing this file with a 128×128 version needs no code change.
