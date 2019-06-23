#!/bin/bash
#
# -- Run pilapse.py and link latest image to www directory
#
#------------------------------------------------------------------------
# Copyright (c) 2019, EGB13.net
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * The names of its contributors may not be used to endorse or promote
#       products derived from this software without specific prior
#       written permission.
# 
# THIS SOFTWARE IS PROVIDED ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
# THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#------------------------------------------------------------------------

VERSION='$Revision: 1.7 $'

WWW=/var/lapse

[ -d "${WWW}" ] || { echo "$WWW: No such directory" >&2 ; exit 1 ; }

/usr/local/sbin/pilapse.py | while read f ; do

    vidset=`expr "$f" : '#VIDEO \(.*\)'`
    if [ "$vidset" != "" ] ; then
        eval $vidset
        while read img ; do
            /bin/fgrep -q "#" <<< "$img" && break
            [ -f "${img}" ] && {
                /bin/rm -f "${WWW}/latest.jpg"
                /bin/ln "${img}" "${WWW}/latest.jpg"
                ## /bin/rm -f "$img"
                /bin/cat "${WWW}/latest.jpg"
            }
        done | /usr/bin/nice /usr/local/bin/ffmpeg -loglevel 0 -y -f image2pipe -vcodec mjpeg -r ${fps:-24} -i - -vcodec mpeg4 -qscale 5 -r ${fps:-24} -f mp4 "${vidpath:?}"
    else
        [ -f "${f}" ] && {
            /bin/rm -f "${WWW}/latest.jpg"
            /bin/ln "${f}" "${WWW}/latest.jpg"
        }
    fi

done
