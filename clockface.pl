#!/usr/bin/perl

#------------------------------------------------------------------------
#  Given list of file names of images:
#   Find timestamp in filename
#   Read the image
#   Add a clockface in one of the corners
#   Write to a new file with a format string for its name
#------------------------------------------------------------------------

my $VERSION = '$Revision: 1.9 $' ;
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

use Image::Magick;
use Getopt::Std ;
use POSIX ":sys_wait_h";


my $PIx2 = 3.1415927 * 2.0 ;

sub Usage { my ($msg) = @_ ;

	print STDERR "$msg"."\n" if (defined ($msg) && $msg ne "") ;
	print STDERR "Usage: $0 -o format-%d.string -g nw|ne|sw|se [-c colorspec] [-s clockpixelsize] [-h hours] [-m minutes] [-p] file [file ...]\n" ;
	print STDERR "    -p enables multi-core parallel processing\n" ;
	exit 0 ;
}

my $outfmt = '' ;
my $gravity = '' ;
my $clocksize = 50 ;
my $colorspec = '#fffffff' ;
my $houradj = 0 ;
my $minadj = 0 ;
my $multi = 0 ; # multiprocessor
my $cpucnt = 1 ; # need to glean from /proc/cpuinfo
my @pq ;
my $DBUG = 0 ;
my $t_start ;
my $t_end ;

my %opts ;
getopts ('o:g:s:c:h:m:pv', \%opts) ;

$outfmt = $opts{o} if (defined ($opts{o}) ) ;
$gravity = $opts{g} if (defined ($opts{g}) ) ; $gravity =~ tr/[A-Z]/[a-z]/ ;
$colorspec = $opts{c} if (defined ($opts{c}) ) ;
$clocksize = $opts{s} if (defined ($opts{s}) ) ;
$houradj = $opts{h} if (defined ($opts{h}) ) ;
$minadj = $opts{m} if (defined ($opts{m}) ) ;
$multi = defined ($opts{p}) ;
$DBUG = defined ($opts{v}) ;

&Usage ("AA") if ($outfmt eq "" || $gravity eq "") ;
&Usage ("Invalid gravity") unless ($gravity eq "nw" || $gravity eq "ne" || $gravity eq "se" || $gravity eq "sw") ;
&Usage ("Clock pixel size must be a positive integer") unless ($clocksize > 0) ;

if ($multi) {
	$cpucnt = CPUcount () ;
	if ($cpucnt > 2) {
		$cpucnt = int($cpucnt/2.0)+1 ;
	}
	printf STDERR "Going to town on %d CPUs!\n"
		, $cpucnt
		;
}
$t_start = time ;


my ($hr, $mn, $se) ;

my $n = 1 ;

foreach my $fname (@ARGV) {

	unless ($fname =~ m/T(\d\d)(\d\d)(\d\d)\D/) {
		printf STDERR "%s: no time stamp found\n", $fname   if ($DBUG) ;
		next ;
	}
	$hr = $1 ;
	$mn = $2 ;
	$se = $3 ;

	if ($houradj != 0) {
		$hr += $houradj ;
		$hr += 24 if ($hr < 0) ;
		$hr %= 24 ;
	}
	if ($minadj != 0) {
		$mn += $minadj ;
		$mn += 60 if ($mn < 0) ;
		$mn %= 60 ;
	}

	my $pid = &ProcOneFrame ($fname, $n++, $clocksize, $gravity, $colorspec, $hr,$mn,$se, $multi) ;
	print STDERR "PID $pid\n" if ($pid > 0 && $DBUG) ;
	if ($multi) {
		push @pq, $pid  ;
		printf STDERR "%d of %d procs\n", ($#pq+1), $cpucnt   if ($DBUG) ;
		if ( ($#pq+1) >= $cpucnt) {
			my $dedpid = shift @pq ;
			waitpid($dedpid, 0);
		}
	}
}

if ($multi) {
	printf STDERR "End of loop with %d procs left.\n", ($#pq+1)    if ($DBUG) ;
	while ($#pq >= 0) {
		my $dedpid = shift @pq ;
		waitpid ($dedpid,0) ;
	}
}

$t_end = time ; 
my $lapsed = $t_end - $t_start ;
printf STDERR "%d clocks drawn in %d seconds (%0.2fs each, %0.2f/s)\n"
	, ($#ARGV+1)
	, $lapsed
	, ( ($lapsed * 1.0) / ($#ARGV+1) )
	, ( ($#ARGV+1) / ($lapsed * 1.0) )
	;

exit 0 ;


#-- --------------------------------------------------------------------
sub ProcOneFrame { my ($file, $frame, $size, $grav, $color, $hr, $mn, $se, $forkit) = @_ ;
#-- --------------------------------------------------------------------

	if ($forkit) {
		if (my $pid = fork() ) {
			print STDERR "$frame: Spun off $file\n"   if ($DBUG) ;
			return pid ;
		}
	}
	print STDERR "$frame: subprocess here\n"   if ($DBUG) ;
	my $img = Image::Magick->new ;
	$result = $img->Read($file) ;
	&ClockFace (\$img, $size, $grav, $color, $hr,$mn,$se) ;
	$newname = sprintf $outfmt, $frame ; 
	$img->Write (filename=>$newname, quality=>'100') ;
	undef $img ;

	exit 0 if ($forkit) ;

	return 0 ;
}

#-- --------------------------------------------------------------------
sub ClockFace { ($imgref, $size, $grav, $color, $h,$m,$s) = @_ ;
#-- --------------------------------------------------------------------

	my $buffer = 5 ; 
	$h = $h % 12 ; 
	my @csize = ($size, $size) ;

	my @imgsize = $$imgref->Get('width', 'height') ;


	# hour hand endpoints
	my $hpct = ( $h + ($m + ($s/60.0) ) / 60.0) / 12.0 ;
	my $hx = ($size / 2.0) + ($size / 3.2) * sin ($hpct * $PIx2) ;
	my $hy = ($size / 2.0) - ($size / 3.2) * cos ($hpct * $PIx2) ;
	my @offset = ($hx, $hy) ;
	($hx, $hy) = &Gravitas ($grav, \@imgsize, \@csize, \@offset, $buffer) ;


	# min hand endpoints
	my $mpct = ($m + ($s/60.0)) / 60.0 ;
	my $mx = ($size / 2.0) + ($size / 2.3) * sin ($mpct * $PIx2) ;
	my $my = ($size / 2.0) - ($size / 2.3) * cos ($mpct * $PIx2) ;
	@offset = ($mx, $my) ;
	($mx, $my) = &Gravitas ($grav, \@imgsize, \@csize, \@offset, $buffer) ;



	# center of clockface
	@offset = ( (($size/2)), (($size/2)) ) ;
	my ($center_x, $center_y) = &Gravitas ($grav, \@imgsize, \@csize, \@offset, $buffer ) ;

	# top edge of clockface
	@offset = ($size/2, 0) ;
	my ($twelve_x, $twelve_y) = &Gravitas ($grav, \@imgsize, \@csize, \@offset, $buffer ) ;

	if (defined ($opts{d}) ) {
	printf "%d: (%d, %d)  %d: (%d, %d)\n"
		, $h
		, $hx
		, $hy
		, $m
		, $mx
		, $my
		;
	}

	# bezel
	my $points = sprintf "%d,%d %d,%d"
		, $center_x
		, $center_y
		, $twelve_x
		, $twelve_y
		;
	$$imgref->Draw(stroke=>'white', strokewidth=>'3.5', fill=>'gray', opacity=>'50', primitive=>'circle', points=>$points);
	$$imgref->Draw(stroke=>'black', strokewidth=>'1', fill=>'none', opacity=>'50', primitive=>'circle', points=>$points);

	# hour hand
	$points = sprintf "%d,%d %d,%d"
		, $center_x
		, $center_y
		, $hx
		, $hy
		;
	$$imgref->Draw(stroke=>'white', strokewidth=>'3.5', primitive=>'line', points=>$points);
	$$imgref->Draw(stroke=>'black', strokewidth=>'1', primitive=>'line', points=>$points);

	# minute hand
	$points = sprintf "%d,%d %d,%d"
		, $center_x
		, $center_y
		, $mx
		, $my
		;
	$$imgref->Draw(stroke=>'white', strokewidth=>'2.5', primitive=>'line', points=>$points);
	$$imgref->Draw(stroke=>'black', strokewidth=>'1', primitive=>'line', points=>$points);


	$points = sprintf "%d:%0.2d", $h, $m ;
	$$imgref->Annotate(pointsize=>40, fill=>'red', text=>$points);

}


#-- --------------------------------------------------------------------
sub Gravitas { my ($grav, $imgsize, $cksize, $offset, $buffer) = @_ ;
#-- --------------------------------------------------------------------

	my $xpos, $ypos ;

	if ($grav =~ m/^n/) {
		$ypos = $offset->[1] + $buffer ;
	} else {
		$ypos = $imgsize->[1] - $cksize->[1] + $offset->[1] - $buffer ;
	}

	if ($grav =~ m/^.w/) {
		$xpos = $offset->[0] + $buffer ;
	} else {
		$xpos = $imgsize->[0] - $cksize->[0] + $offset->[0] - $buffer ;
	}

	return ($xpos, $ypos) ;

}

#-- --------------------------------------------------------------------
sub CPUcount { 

	my $maxcpu  = 0 ;
	open ($cpuinfo, "</proc/cpuinfo") || return 1 ;
	while (<$cpuinfo>) {
		if (m/processor\s*:\s*(\d+)\s*$/) {
			$maxcpu = $1 if ($1 > $maxcpu) ;
		}
	}

	return ($maxcpu + 1) ;
}
