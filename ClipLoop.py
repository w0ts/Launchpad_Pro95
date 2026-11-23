"""Setting a clip's loop from the step sequencers."""


def set_loop_and_markers(clip, start, end):
    """Set the clip's loop and start/end markers to start..end. The order of the four writes
    keeps start < end at every step, whichever way the loop moves."""
    if start >= clip.loop_end:
        clip.loop_end = end
        clip.loop_start = start
        clip.end_marker = end
        clip.start_marker = start
    else:
        clip.loop_start = start
        clip.loop_end = end
        clip.start_marker = start
        clip.end_marker = end
