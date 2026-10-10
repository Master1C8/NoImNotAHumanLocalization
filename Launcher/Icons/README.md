# Original game icons

The macOS launcher uses the installed game's wrapper icon, copied byte for byte.
The Windows launcher uses the first RT_GROUP_ICON from the original game executable;
its nine original bitmap resources are preserved without resampling or compression.
`source.json` binds both assets to their source paths and SHA-256 values.

`build.py` embeds the ICO images as RT_ICON resources and the group as resource 1,
matching `Windows.c`'s LoadIconW call. The macOS bundle references App.icns and
increments CFBundleVersion when changing the icon. These assets belong to the game.

Regression: the Windows PE must contain group 1 with all nine exact original images,
and the macOS archive's App.icns must equal the original wrapper icon. Verify the
packaged resources, not just the source files or bundle metadata.
