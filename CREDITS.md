# Credits

The characters in [`banner.svg`](banner.svg) are pixel art by two artists,
recoloured and staged by [`scripts/build.py`](scripts/build.py). The wizard's
robe is shifted from purple to grey; the demon's body is dropped into shadow so
only its fire still reads.

- **Wizard Pack** by [LuizMelo](https://luizmelo.itch.io/wizard-pack) — CC0.
  Credit is not required, but the work deserves it.
- **Boss: Demon Slime** by [chierit](https://chierit.itch.io/boss-demon-slime) —
  **CC-BY 4.0**, which requires this attribution. The free version's demon-form
  idle cycle is the one used here.

The bridge, chasm, firelight and embers are drawn in SVG by the build script.

To rebuild, download both packs from the links above, unpack them so the tree
looks like `<src>/wizard/Wizard Pack/…` and
`<src>/demon/boss_demon_slime_FREE_v1.0/…`, then run:

```sh
python3 scripts/build.py --src <src> --out .
```

Gandalf and the Balrog are creations of J.R.R. Tolkien. This is a fan tribute,
not an official or licensed depiction.
