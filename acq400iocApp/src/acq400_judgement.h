/*
 * acq400_judgement.h
 *
 *  Created on: 7 Jan 2021
 *      Author: pgm
 */

#ifndef ACQ400IOCAPP_SRC_ACQ400_JUDGEMENT_H_
#define ACQ400IOCAPP_SRC_ACQ400_JUDGEMENT_H_

#include "asynPortDriver.h"

#define PS_NCHAN 		"NCHAN"				/* asynInt32, 		r/o */
#define PS_NSAM			"NSAM"				/* asynInt32,       r/o */
#define PS_ES_SPREAD	"ES_SPREAD"			/* asynInt32,       r/o */
#define PS_MASK_FROM_DATA 	"MAKE_MASK_FROM_DATA"		/* asynInt32,       r/w .. MU=y+val, ML=y-val */
#define PS_MASK_BOXCAR		"MASK_BOXCAR"			/* asynInt32        r/w numb boxcar elements */
#define PS_MASK_SQUARE		"MASK_SQUARE"			/* asynInt32        r/w numb squareoff elements */
#define PS_MU			"MASK_UPPER"			/* asynInt16Array   r/w */
#define PS_ML			"MASK_LOWER"			/* asynInt16Array   r/w */
#define PS_RAW			"RAW"				/* asynInt16Array   r/o */
#define PS_BN			"BUFFER_NUM"			/* asynInt32, 		r/o */
#define PS_WINL			"WINL"                          /* asynInt32,       r/w Window Left */
#define PS_WINR			"WINR"                          /* asynInt32,       r/w Window Right */

#define PS_RESULT_FAIL 		"RESULT_FAIL"			/* asynInt32 		r/o */ /* per port P=2 */
#define PS_RESULT_MASK32	"FAIL_MASK32"
#define PS_OK			"OK"				/* asynInt32		r/o */
#define PS_SAMPLE_COUNT		"SAMPLE_COUNT"			/* asynInt32		r/o */
#define PS_CLOCK_COUNT		"CLOCK_COUNT"			/* asynInt32		r/o */
#define PS_SAMPLE_TIME		"SAMPLE_TIME"			/* asynFloat64		r/o */ /* secs.usecs, synthetic */
#define PS_BURST_COUNT  	"BURST_COUNT"			/* asynInt32		r/o */
#define PS_SAMPLE_DELTA_NS	"SAMPLE_DELTA_NS"		/* asynInt32		r/w */
#define PS_UPDATE		"UPDATE_ON"			/* asynInt32		r/w */

#define ADDR_WIN_ALL	nchan

enum UPDATE {
	UPDATE_NEVER,
	UPDATE_ON_FAIL,
	UPDATE_ON_SUCCESS,
	UPDATE_ALWAYS
};

class acq400Judgement: public asynPortDriver {
public:
	virtual asynStatus readInt8Array(asynUser *pasynUser, epicsInt8 *value,
			size_t nElements, size_t *nIn);
	virtual asynStatus readInt16Array(asynUser *pasynUser, epicsInt16 *value,
			size_t nElements, size_t *nIn);

	static int factory(
		const char *portName, int nchan, int maxPoints, unsigned data_size, const char* site_channels, int bursts_per_buffer, unsigned ndma);
	static int verbose;
	static int stub_es;
	static const int _FIRST_SAM;
	void task_get_params();
	virtual void task();
	virtual void fill_request_task(void) {};
	virtual asynStatus updateTimeStamp(int offset);



protected:
	int handle_es(unsigned* raw);
	virtual void handle_burst(int vbn, int offset) = 0;
	/**< vbn: virtual buffer number. ib is physical buffer */
	bool calculate(epicsInt16* raw, const epicsInt16* mu, const epicsInt16* ml);
	/* return TRUE if any fail */
	bool onCalculate(bool fail);
	virtual void doDataUpdateCallbacks(int ic) = 0;
	virtual void doMaskUpdateCallbacks(int ic) = 0;

	acq400Judgement(const char* portName, int nchan, int nsam, const char* _site_channels, int bursts_per_buffer);
	virtual ~acq400Judgement(void) {}

	const int nchan;
	const int nsam;
	int es_spread;
	const int bursts_per_buffer;  /** aka bpb */
	std::vector<int> site_channels;

	/** Values used for pasynUser->reason, and indexes into the parameter library. */
	int P_NCHAN;
	int P_NSAM;
	int P_ES_SPREAD;
	int P_MASK_FROM_DATA;
	int P_MASK_BOXCAR;
	int P_MASK_SQUARE;
	int P_MU;
	int P_ML;
	int P_WINL;
	int P_WINR;
	int P_RAW;
	int P_BN;
	int P_RESULT_FAIL;
	int P_OK;
	int P_RESULT_MASK32;
	int P_SAMPLE_COUNT;
	int P_CLOCK_COUNT;
	int P_SAMPLE_TIME;
	int P_BURST_COUNT;
	int P_SAMPLE_DELTA_NS;
	int P_UPDATE;

	/* our data */

	epicsInt16* WINL;	/* window left [chan] 		 */
	epicsInt16* WINR;	/* window right [chan] 		 */

	epicsInt8* RESULT_FAIL;
	const int fail_mask_len;  /* number of elements in FAIL_MASK32 */
	epicsInt32* FAIL_MASK32;
	epicsInt32 sample_count;
	epicsTimeStamp t0, t1;
	unsigned clock_count[2];			     /* previous, current */
	epicsInt32 burst_count;
	epicsFloat64 sample_time;
	epicsInt32 sample_delta_ns;

	int ib;			/** ib is physical buffer contains bpb vpb's */
	bool fill_requested;

	int FIRST_SAM;
};

#endif /* ACQ400IOCAPP_SRC_ACQ400_JUDGEMENT_H_ */
