/* rtm_buffer_mon.st
 * Optimise rtm_buffer such that BPB pulses occur per buffer. Restore full buffer for continuous capture.
 * Heuristic for BPB: < 50Hz : 1, < 100Hz : 2, > 100Hz 4   NOT AUTOMATED
 * BLEN must be a multiple of BPB*SSB and MINDMA
 * SM may adjust RTM_TRANSLEN to achieve goal
 * Later, adust WF SIZE for clean plot 


 * SSB :         Sample Size Bytes
 * MINDMA :      DMA transfers are modulo one page (4096b)
 * BPB :         Bursts per buffer:  
for a responsive system, ideally BPB==1, but if the burst rate is too high, we need to compromise.
 * RTM_TRANSLEN: length of Burst in samples
 * MAXBLEN :     maximum bufferlen (kernel memory allocation on device driver load)
 * RGM:          mode control 0: CONTINUOUS, 3: BURST
 * OPTIMISE_BUFFERLEN : 
for CONTINUOUS data, set buffer length to largest N samples that fit the buffer
buffers are ALWAYS channel aligned.
 * */

program rtm_buffer_mon
option +r;

int maxblen; 		assign maxblen 		to "{uut}:0:MAXBLEN";
int blen;    		assign blen 		to "{uut}:0:BLEN";
int bpb;     		assign bpb		to "{uut}:0:BPB";
int ssb;		assign ssb		to "{uut}:0:SSB";
int rtm_translen; 	assign rtm_translen 	to "{uut}:1:RTM_TRANSLEN";		monitor rtm_translen;
int rgm;		assign rgm 		to "{uut}:1:RGM";			monitor rgm;
int optimise_bufferlen;	assign optimise_bufferlen to "{uut}:0:OPTIMISE_BUFFERLEN";


#define PNAME		"rtm_buffer_mon "
#define MENU_RTM	3

#define MINDMA		4096

int verbose;

int rtm_translen0 = -1;
int rgm0 = -1;

int pages;


ss rtm_buffer_mon {
	state init {
		when() {
			if (macValueGet("verbose")){
				verbose = macValueGet("verbose")[0] - '0';
			}
			pvGet(maxblen);
			pvGet(blen);
			if (blen != maxblen){
				printf(PNAME "init: change maxblen from %d to blen %d\n", maxblen, blen);
				maxblen = blen;
				pvPut(maxblen);
		        }
		} state wait_rgm_change
	}
	state wait_rgm_change {
		when (rgm != rgm0 && rgm != MENU_RTM){
			rgm0 = rgm;
		} state go_continuous
		
		when ((rgm != rgm0 && rgm == MENU_RTM) || rtm_translen != rtm_translen0){
			rgm0 = rgm;
			rtm_translen0 = rtm_translen;
		} state go_rtm
	}
	
	state go_continuous {
		when() {
			if (verbose) printf(PNAME "go_continuous\n");
			blen = maxblen; 
			pvPut(blen);
			pvPut(optimise_bufferlen);
		} state wait_rgm_change
	} 
	
	state go_rtm {
		when() {
			if (verbose) printf(PNAME "go_rtm\n");
			pvGet(bpb);
			pvGet(ssb);
			blen = bpb * ssb * rtm_translen;
			pages =  blen / MINDMA;
			if (blen % MINDMA){
				blen = (pages+1) * MINDMA;
				rtm_translen = blen/(bpb*ssb);
			}
			if (blen > maxblen){
				printf(PNAME "ERROR: Buffer overrun, go with what we've got");
				blen = maxblen; 
				pvPut(blen);
				pvPut(optimise_bufferlen);
			}else{
				pvPut(blen);
				if (rtm_translen != rtm_translen0){
					pvPut(rtm_translen);
					rtm_translen0 = rtm_translen;
					if (verbose) printf(PNAME "info: new blen %d new translen %d\n", blen, rtm_translen);
				}else{
					if (verbose) printf(PNAME "info: new blen %d keep translen %d\n", blen, rtm_translen);
				}
			}
		} state wait_rgm_change
	}
}
