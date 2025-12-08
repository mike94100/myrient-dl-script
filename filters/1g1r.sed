# 1G1R Filter

# Exclude unreleased or unofficial games or non-game content
/^#/b; /(\(Beta)/s/^/#/
/^#/b; /(\(Demo)/s/^/#/
/^#/b; /(\(Tech Demo\))/s/^/#/
/^#/b; /(\(Pirate)/s/^/#/
/^#/b; /(\(Proto)/s/^/#/
/^#/b; /(\(Unl)/s/^/#/
/^#/b; /(\(Test Program\))/s/^/#/

# Exclude Non-English
/^#/b; /(\(Ja\))/s/^/#/

# Exclude Collections with redundant games
/^#/b; /(\(Virtual Console\))/s/^/#/
/^#/b; /(\(Switch Online\))/s/^/#/
/^#/b; /(\(Evercade\))/s/^/#/
/^#/b; /(\(Limited Run Games\))/s/^/#/
/^#/b; /(\(Castlevania Advance Collection\))/s/^/#/

# Exclude Non-Games
/^#/b; /(\[BIOS\])/s/^/#/
/^#/b; /(\(Kiosk\))/s/^/#/

# Include only USA and World regions
/^#/b; /(\(USA)/b; /(\(World\))/b; s/^/#/