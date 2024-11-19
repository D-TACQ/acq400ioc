/* ------------------------------------------------------------------------- */
/*   Copyright (C) 2011 Peter Milne, D-TACQ Solutions Ltd
 *                      <Peter dot Milne at D hyphen TACQ dot com>

    http://www.d-tacq.com

    This program is free software; you can redistribute it and/or modify
    it under the terms of Version 2 of the GNU General Public License
    as published by the Free Software Foundation;

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.                */
/* ------------------------------------------------------------------------- */

/** @file AcqWfCalc.cpp Calc record to give calibrated WF output
 * 
 *  Created on: Apr 12, 2012
 *      Author: pgm
 *      INPA : the raw waveform
 *      INPB : VMAX[NCHAN]
 *      INPC : VMIN[NCHAN]
 */

#include "local.h"

#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <cmath>
#include <limits>


#include "alarm.h"
#include "cvtTable.h"
#include "dbDefs.h"
#include "dbAccess.h"
#include "dbScan.h"
#include "drvSup.h"
#include "recGbl.h"
#include "recSup.h"
#include "devSup.h"
#include "aSubRecord.h"
#include "link.h"
#include "menuFtype.h"
#include "epicsExport.h"
#include "epicsThread.h"
#include "waveformRecord.h"

#include <registryFunction.h>
#include <epicsExport.h>


#include <math.h>

#include <bitset>
#include <stack>
#include <string>
#include <vector>

#include <sstream>
#include <iomanip>



#define MILLION	1000000

static long raw_to_uvolts(aSubRecord *prec) {
       long long yy;
       long *raw = (long *)prec->a;
       int len = prec->noa;
       long * cooked = (long *)prec->vala;

       for (int ii=0; ii <len; ii++) {
    	   yy = raw[ii] >> 8;
    	   yy *= 10*MILLION;
           cooked[ii] = (long)(yy >> 23);
       }

       return 0;
   }

static int report_done;
static int verbose;


#define OR_THRESHOLD 32

/* ARGS:
 * INPUTS:
 * INPA : const T raw[size}
 * INPB : long maxcode
 * INPC : float vmax
 * INPD : long threshold (distance from rail for alarm)
 * INPL : window start index (0: beginning of data set)
 * INPM : window end index (0: end of data set)
 * INPO : double AOFF if set
 * INPS : double ASLO if set
 * OUTPUTS:
 * VALA : float* cooked
 * optional:
 * VALB : long* alarm
 * VALC : float* min
 * VALD : float* max
 * VALE : float* mean
 * VALF : float* stddev
 * VALG : float* rms
 * VALH : float* CV
 * VALI : short* top_half   when splitting a u32
 * VALJ : short* low_half
 *
 * INPP : float* iscale     for converting VALI
 * INPQ : float* jscale     for converting VALJ
 * INPR : long suppress     suppress P,Q conversion if set.
 * VALP : VALI * INPP
 * VALQ : VALJ * INPQ
 */




template <class T> double square(T raw) {
	double dr = static_cast<double>(raw);
	return dr*dr;
}

template <class T, int SHR> T scale(T raw) { return raw >> SHR; }


template <class T, int SHR>
long raw_to_volts(aSubRecord *prec) {
	double yy;
	const T *raw = (T *)prec->a;
	const epicsUInt32 len = prec->noa;
	float * cooked = (float *)prec->vala;
	const long rmax = *(long*)prec->b;
	const float vmax = *(float*)prec->c;
	const double aoff = *(double*)prec->o;
	const double aslo = *(double*)prec->s;
	const long* p_thresh = (long*)prec->d;
	long* p_over_range = (long*)prec->valb;
	float* p_min = (float*)prec->valc;
	float* p_max = (float*)prec->vald;
	float* p_mean = (float*)prec->vale;
	float* p_stddev = (float*)prec->valf;
	float* p_rms = (float*)prec->valg;
	float* p_cv = (float*)prec->valh;			// Coefficient of variance, VALE and VALF MUST be defined!
	unsigned short *p_top_half = (unsigned short*)prec->vali;	// user might consider these to be signed we don't care
	unsigned short *p_low_half = (unsigned short*)prec->valj;
	const epicsUInt32* p_w1 = (epicsUInt32*)prec->l;
	const epicsUInt32* p_w2 = (epicsUInt32*)prec->m;
	short suppress_pq = *(short*)prec->r;

	long min_value;
	long max_value;
	long over_range = 0;
	long alarm_threshold = rmax - (p_thresh? *p_thresh: OR_THRESHOLD);
	double sum = 0;
	double sumsq = 0;
	bool compute_squares = p_stddev != 0 || p_rms != 0;

	const epicsUInt32 window1 = p_w1 != 0? *p_w1: 0;
	const epicsUInt32 window2 = p_w2 != 0 && *p_w2 != 0? *p_w2: len-1;
	const epicsUInt32 winlen = window2 - window1 + 1;
	// if window2 < window1, winlen-> infinity, so mean -> 0, which is fair enough

	if (::verbose && ++report_done == 1){
		printf("aoff count: %u value: %p type: %d\n", prec->noo, prec->o, prec->fto);
		printf("aslo count: %u value: %p type: %d\n", prec->nos, prec->s, prec->fts);
		printf("raw_to_volts() ->b %p rmax %ld\n", prec->b, rmax);
		printf("raw_to_volts() ->c %p vmax %f\n", prec->c, vmax);
		printf("raw_to_volts() len:%d th:%ld p_over:%p\n",
				len, alarm_threshold, p_over_range);
		printf("scale %x becomes %x\n", 0xdead, (unsigned)scale<T, SHR>(0xdead));
		printf("window %u %u %u\n", window1, window2, winlen);
	}

	if (::verbose > 1 && strstr(prec->name, ":01") != 0){
		printf("%s : aslo:%.6e aoff:%.6e\n", prec->name, aslo, aoff);
	}

	min_value = scale<T, SHR>(raw[window1]);
	max_value = scale<T, SHR>(raw[window1]);

	for (epicsUInt32 ii = 0; ii <len; ii++) {
		T rx = scale<T, SHR>(raw[ii]);

		if (ii >= window1 && ii <= window2){
			if (rx > max_value) 		max_value = rx;
			if (rx < min_value) 		min_value = rx;
			if (rx > alarm_threshold) 	over_range = 1;
			if (rx < -alarm_threshold) 	over_range = -1;
			if (compute_squares) 		sumsq += square<T>(rx);
			sum += rx;
		}
		yy = rx*aslo + aoff;
		cooked[ii] = (float)yy;
		if (::verbose && ii==0 && strstr(prec->name, ":01") != 0){
			printf("%s : aslo:%.6e aoff:%.6e rx:%06x yy=%.5e window:%d,%d\n",
					prec->name, aslo, aoff, (unsigned)rx, yy, window1, window2);
		}
	}
	if (suppress_pq == 0 && sizeof(T) == 4 && prec->novi == len && prec->novj == len){
		if (::verbose > 1){
			printf("%s : splitting lw\n", prec->name);
		}
		epicsUInt32* uraw = (epicsUInt32*)raw;

		for (epicsUInt32 ii = 0; ii <len; ii++) {
			p_top_half[ii] = uraw[ii] >> 16;
			p_low_half[ii] = uraw[ii];
		}

		if (prec->novp == len && prec->novq == len){
			float iscale = *(float*)prec->p;
			float jscale = *(float*)prec->q;
			float* valp = (float*)prec->valp;
			float* valq = (float*)prec->valq;
			const bool i_is_int16 = prec->ftvi == menuFtypeSHORT;
			const bool j_is_int16 = prec->ftvj == menuFtypeSHORT;

			if (::verbose > 2 ){
				printf("%s : convert iscale:%f*%s,(%d) jscale:%f*%s,(%d)\n",
						prec->name,
						iscale, i_is_int16? "int16": "u16", prec->ftvi,
						jscale, j_is_int16? "int16": "u16", prec->ftvj);
			}
			for (epicsUInt32 ii = 0; ii<len; ii++) {
				if (i_is_int16){
					valp[ii] = iscale * ((short*)p_top_half)[ii];
				}else{
					valp[ii] = iscale * p_top_half[ii];
				}
				if (j_is_int16){
					valp[ii] = jscale * ((short*)p_low_half)[ii];
				}else{
					valq[ii] = jscale * p_low_half[ii];
				}
			}
		}
	}

	if (p_over_range){
		*p_over_range = over_range;
	}
	if (p_max) 	*p_max = max_value*aslo + aoff;
	if (p_min) 	*p_min = min_value*aslo + aoff;
	if (p_mean) 	*p_mean = (sum*aslo)/winlen + aoff;

	if (p_rms)	*p_rms = sqrt(sumsq/winlen)*aslo + aoff;
	if (p_stddev)	*p_stddev = winlen>1? sqrt((sumsq - (sum*sum)/winlen)/winlen) * aslo: 0;
	if (p_cv)	*p_cv = *p_stddev / *p_mean;
	return 0;
}

/** ARGS:
 * INPUTS:
 * INPA : const T volts[size]
 * INPO : double AOFF if set
 * INPS : double ASLO if set
 * OUTPUTS:
 * VALA : link to raw
 */
template <class T, int SHL>
long volts_to_raw(aSubRecord *prec) {
	float * volts = reinterpret_cast<float*>(prec->a);
	int len = prec->nea;
	T *raw = reinterpret_cast<T *>(prec->vala);
	double aoff = *reinterpret_cast<double*>(prec->o);
	double aslo = *reinterpret_cast<double*>(prec->s);

	for (int ii=0; ii <len; ii++) {
		double yy = (volts[ii] - aoff) / aslo;

		raw[ii] = static_cast<T>(yy) << SHL;

		if (::verbose && ii < 5){
			printf("volts_to_raw [%d] %.2f -> %ld  # aslo %e aoff %e\n", ii, volts[ii], (long)raw[ii], aslo, aoff);
		}
	}
	/* ideally set NORD in OUTPUT to NORD in input .. */
	prec->neva = len;
	return 0;
}



/* ARGS:  T: short or long
 * INPUTS:
 * INPA : const T I [N]
 * INPB : const T Q [N]
 * INPC : float* fs [1]
 * INPD : int* is_cplx [1]
 * INPF : float* attenuation factor db [1]
 * OUTPUTS:
 * VALA : float* radius
 * optional:
 * VALB : float* theta
 */

#define RAD2DEG	(180/M_PI)

template <class T>
long cart2pol(aSubRecord *prec) {
	T *raw_i = reinterpret_cast<T*>(prec->a);
	T *raw_q = reinterpret_cast<T*>(prec->b);
	int len = prec->noa;
	float * radius = (float *)prec->vala;
	float * theta = (float *)prec->valb;

	for (int ii = 0; ii < len; ++ii){
		float I = raw_i[ii];;
		float Q = raw_q[ii];
		radius[ii] = sqrtf(I*I + Q*Q);
		theta[ii] = atan2f(I, Q) * RAD2DEG;
	}
	return 0;
}


/* ARGS:  T: UCHAR
 * Convert array of uchar to single long bitmask, TRUE if each value > threshold
 * INPA: Array of bool
 * INPB: Threshold (default = 0)
 * VALA: LONG outputs.
 */
long boolarray2u32(aSubRecord* prec)
{
	unsigned char* bools = (unsigned char*)(prec->a);
	unsigned *compact = (unsigned*)prec->vala;
	int len = prec->noa;
	unsigned char threshold = 0;
	if (prec->nob == 1){
		threshold = *(unsigned char*)prec->b;
	}


	unsigned cw = 0;

	for (int ii = 0; ii < len; ++ii){
		if (bools[ii] > threshold){
			cw |= 1<<ii;
		}
	}
	*compact = cw;
	return 0;
}

/** ARGS:
 * INPUTS:
 * INPA : const u8* elems
 * INPF : file name;
 * OUTPUTS:
 * VALA : link to raw
 */

const unsigned MAXBIT = 256;
typedef std::bitset<MAXBIT> ChannelMask;

ChannelMask createBitsetFromByteArray(unsigned char* bytes, int nbytes) {
    std::string bitString;
    for (int ii = 0; ii < nbytes; ++ii){
	    bitString += bytes[ii]? '1': '0';
    }

    return ChannelMask(bitString);
}

long bitmask(aSubRecord* prec)
{
	unsigned char* channels = (unsigned char*)(prec->a);
	int nchan = prec->noa;
	const char *fname = (char *)prec->f;

	ChannelMask cm = createBitsetFromByteArray(channels, nchan);

	std::stack<unsigned char> nibbles;

	unsigned char nibble = 0;
	for (unsigned char ic = 0, bx = 0; ic < cm.size(); ++ic, ++bx){
		nibble |= cm[ic]<<(bx%4);
		if (bx%4 == 3){
			nibbles.push(nibble);
			nibble = 0;
		}
	}
	if (nibble){
		nibbles.push(nibble);
	}

	FILE* fp = fopen(fname, "w");
	if (fp == 0){
		perror(fname);
		exit(errno);
	}
	fprintf(fp, "0x");
	for( ; !nibbles.empty(); nibbles.pop()){
		fprintf(fp, "%x", nibbles.top());
	}
	fprintf(fp, "\n");
	fclose(fp);
	return 0;
}

long bitmask(aSubRecord* prec)
{
	unsigned char* channels = (unsigned char*)(prec->a);
	int nchan = prec->noa;
	const char *fname = (char *)prec->f;

	ChannelMask cm = createBitsetFromByteArray(channels, nchan);

	std::stack<unsigned char> nibbles;

	unsigned char nibble = 0;
	for (unsigned char ic = 0, bx = 0; ic < cm.size(); ++ic, ++bx){
		nibble |= cm[ic]<<(bx%4);
		if (bx%4 == 3){
			nibbles.push(nibble);
			nibble = 0;
		}
	}
	if (nibble){
		nibbles.push(nibble);
	}

	FILE* fp = fopen(fname, "w");
	if (fp == 0){
		perror(fname);
		exit(errno);
	}
	fprintf(fp, "0x");
	for( ; !nibbles.empty(); nibbles.pop()){
		fprintf(fp, "%x", nibbles.top());
	}
	fprintf(fp, "\n");
	fclose(fp);
	return 0;
}

long timebase(aSubRecord *prec) {
	long pre = *(long*)prec->a;
	long post = *(long*)prec->b;
	float dt = *(float*)prec->c;
	float * tb = (float *)prec->vala;
	long maxtb = prec->nova;
	long len = pre + post + 1;    // [pre .. 0 .. post]

	if (len > maxtb) len = maxtb;

	for (int ii = 0; ii < len; ++ii){
		tb[ii] = (ii - pre)*dt;
	}
	return 0;
}

//#include <complex.h>
#include "fftw3.h"

#define MAXS	32768   // normalize /32768
#define MAXL	0x7fffffff

// avoid sqrt() function by dividing by 2 in log domain
#define LOGSQRT(n)	((n)/2)

#define DDC_ATTENUATION_FACTOR 20	// DDC attenuation in dB

#define RE	0
#define IM	1
//#define SWAP(aa,bb,tt)  ( tt = aa, aa = bb, bb = tt )
#define SWAP(x, y) do { typeof(x) SWAP = x; x = y; y = SWAP; } while (0)

template <class T, unsigned SCALE>
class Spectrum {
	const int N;
	const int N2;
	fftwf_complex *in, *out;
	fftwf_plan plan;
	float* window;

	float* R;		/* local array computes R (magnitude) */
	float f0;		/* previous frequency .. do we have to recalc the bins? */

	const bool is_cplx;
	const float MINSPEC;
	double* smoo;

	void binFreqs(float* bins, float fs, int f_bin0, int nmax) {
		if (bins != 0 && floorf(fs/100) != floorf(f0/100)){
			float nyquist = fs/2;
			float fx = f_bin0*nyquist;
			float delta = nyquist/N2;

			for (int ii = 0; ii != nmax; ++ii){
				bins[ii] = fx;
				fx += delta;
			}
			f0 = fs;
		}
	}
	void binFreqs(float* bins, float fs) {
		if (is_cplx){
			binFreqs(bins, fs, -1, N);
		}else{
			binFreqs(bins, fs, 0, N2);
		}
	}

	void fillWindowTriangle() {
		printf("filling default triangle window\n");
		for (int ii = 0; ii < N2; ++ii){
			window[ii] = window[N-ii-1] = (float)ii/N2;
		}
	}
	void fillWindow()
	{
		FILE *fp = fopen("/dev/shm/window", "r");
		if (fp != 0){
			int nread = fread(window, sizeof(float), N, fp);
			fclose(fp);
			if (nread == N){
				printf("filled window from /dev/shm/window\n");
				return;
			}
		}
		fillWindowTriangle();
	}
	void windowFunction(T* re, T* im)
	{
		for (int ii = 0; ii < N; ++ii){
			in[ii][RE] = re[ii] * window[ii];
			in[ii][IM] = im[ii] * window[ii];
		}
	}
	void powerSpectrum(float* mag)
	{
		// ref http://www.fftw.org/fftw2_doc/fftw_2.html
		// r0, r1, r2, ..., rn/2, i(n+1)/2-1, ..., i2, i1
		// map to
		// in,....i1,r0,r1, .... rn/2
		// where r0 is at [N2]
		float *mn = mag;			// neg freqs
		float *mp = is_cplx? mag+N2: mn;	// pos freqs
		float sm = smoo==0? 0: (float)smoo[0];

		// calc magnitude of every bin
		for (int ii = 0; ii < N; ++ii){
			float I = out[ii][RE];
			float Q = out[ii][IM];
			I /= SCALE;
			Q /= SCALE;
			R[ii] = (I*I + Q*Q);
			float M = LOGSQRT(20*log10(R[ii])) - db0;

			if (ii && M < MINSPEC){
				M = MINSPEC;
			}
			if (is_cplx){
			// FFTW presents the spectrum 0..-F,+F..0 ? fix that
				if (ii < N2){
					mp[ii] = mp[ii]*sm + M*(1-sm);
				}else{
					mn[ii-N2] = mn[ii-N2]*sm + M*(1-sm);
				}
			}else{
				if (ii < N2){
					mp[ii] = mp[ii]*sm + M*(1-sm);
				}else{
					break;
				}
			}
		}
	}
public:
	Spectrum(int _N, float* _window, int isCplx, float atten_db, double* _smoo) :
		N(_N), N2(_N/2), window(_window),
		R(new float[_N]), f0(0), is_cplx(isCplx),
		MINSPEC(sizeof(T) == 2? -150: -180), smoo(_smoo) {

		printf("Spectrum B1014 %s MINSPEC %.1f\n",
			isCplx? "cplx": "real", MINSPEC);
		fillWindow();
		in = (fftwf_complex*) fftwf_malloc(sizeof(fftwf_complex) * N);
		out = (fftwf_complex*) fftwf_malloc(sizeof(fftwf_complex) * N);
		plan = fftwf_plan_dft_1d(N, in, out, FFTW_FORWARD, FFTW_ESTIMATE);
		// full scale I+Q Say all one bin 2 * 4096 ..
		db0 = 20 * log10(N*2) - atten_db;
	}
	virtual ~Spectrum() {
		fftwf_destroy_plan(plan);
		fftwf_free(in);
		fftwf_free(out);
	}

	void exec (T* re, T* im, float* mag, float* bins, float fs)
	{
		windowFunction(re, im);
		fftwf_execute(plan);
		powerSpectrum(mag);
		if (bins != 0) binFreqs(bins, fs);
	}
	float db0;
};

template <class T, unsigned SCALE>
long spectrum(aSubRecord *prec)
{
	T *raw_i = reinterpret_cast<T*>(prec->a);
	T *raw_q = reinterpret_cast<T*>(prec->b);
	float *fs = reinterpret_cast<float*>(prec->c);
	int* isCplx = reinterpret_cast<int*>(prec->d);
	float *attenuation = reinterpret_cast<float*>(prec->f);
	float atten_db = prec->nof? *attenuation: DDC_ATTENUATION_FACTOR;
	double* smoo = prec->nos? reinterpret_cast<double*>(prec->s): 0;
	int len = prec->noa;

	float* mag = reinterpret_cast<float*>(prec->vala);
	float* freqs = prec->nob>1? reinterpret_cast<float*>(prec->valb): 0;
	float *window = reinterpret_cast<float*>(prec->valc);

	static Spectrum<T, SCALE> *spectrum;
	if (!spectrum){
		spectrum = new Spectrum<T, SCALE>(len, window, *isCplx, atten_db, smoo);
	}
	spectrum->db0 = atten_db;
	spectrum->exec(raw_i, raw_q, mag, freqs, *fs);
	return 0;
}

static registryFunctionRef my_asub_Ref[] = {
       {"raw_to_uvolts", (REGISTRYFUNCTION) raw_to_uvolts},
       {"raw_to_volts_LONG",  (REGISTRYFUNCTION) raw_to_volts<long, 8>},
       {"raw_to_volts_INT24",  (REGISTRYFUNCTION) raw_to_volts<long, 0>},
       {"raw_to_volts_SHORT",  (REGISTRYFUNCTION) raw_to_volts<short, 0>},
       {"volts_to_raw_SHORT", (REGISTRYFUNCTION) volts_to_raw<short, 0>},
       {"volts_to_raw_LONG", (REGISTRYFUNCTION) volts_to_raw<long, 8>},
       {"volts_to_raw_DAC20", (REGISTRYFUNCTION) volts_to_raw<long, 0>},
       {"cart2pol", (REGISTRYFUNCTION) cart2pol<short>},
       {"cart2pol_LONG", (REGISTRYFUNCTION) cart2pol<long>},
       {"cart2pol_SHORT", (REGISTRYFUNCTION) cart2pol<short>},
       {"boolarray2u32", (REGISTRYFUNCTION) boolarray2u32},
       {"bitmask", (REGISTRYFUNCTION) bitmask},
       {"timebase", (REGISTRYFUNCTION) timebase},
       {"spectrum", (REGISTRYFUNCTION) spectrum<short, MAXS>},
       {"spectrum_LONG", (REGISTRYFUNCTION) spectrum<long, MAXL>},
       {"spectrum_LONG18", (REGISTRYFUNCTION) spectrum<long, (2<<17)>},
       {"spectrum_SHORT", (REGISTRYFUNCTION) spectrum<short, MAXS>},
 };

 static void raw_to_uvolts_Registrar(void) {
	 const char* vs = getenv("ACQWFCALC_VERBOSE");
	 if (vs) verbose = atoi(vs);

	 registryFunctionRefAdd(my_asub_Ref, NELEMENTS(my_asub_Ref));
 }

 epicsExportRegistrar(raw_to_uvolts_Registrar);
