#!/bin/sh
# https://ffmpeg.org/ffmpeg-filters.html#blend
# https://video.stackexchange.com/a/36688/46212
# https://unix.stackexchange.com/questions/635721/efficient-way-to-compose-all-frames-in-a-video-to-a-single-image
ffmpeg -i tutorial-signin.gif -vf "tblend=all_mode=difference,format=gray,maskfun=low=0:high=1:fill=255,tblend=lighten,framestep=2,tblend=lighten,framestep=2,tblend=lighten,framestep=2" tutorial-signin-diff.gif
# flag{look!?wiiinnnd-of-missing-you-here-eventually-blows-to-the-geekgame~~~}
