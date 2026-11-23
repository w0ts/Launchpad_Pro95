# Add Stop buttons at the bottom of the Session. Experimental
# SESSION__STOP_BUTTONS = True

# Link sessions between multiple launchpad95. Experimental
# SESSION__LINK = True

# Link stepseq to follow session. Experimental
# STEPSEQ__LINK_WITH_SESSION = True

# allow sep seq and instrument modes to save their scale settings.
# as live does not offer any api we are stuck with using the track or clip name...
# possible values : "clip" to save in clip, set, None,  (case matter)
# Experimental
# STEPSEQ__SAVE_SCALE = "clip"
# INSTRUMENT__SAVE_SCALE = "clip"
STEPSEQ__SAVE_SCALE = None
INSTRUMENT__SAVE_SCALE = None
