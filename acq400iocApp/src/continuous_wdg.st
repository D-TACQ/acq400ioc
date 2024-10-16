/*
continuous_wdg.stt : auto-restarts CONTINUOUS if acq400_stream drops out unexpectedly

INPUT
{uut}:MODE:CONTINUOUS
{uut}:MODE:CONTINUOUS:STATE
{uut}:1:SHOT
{uut}:1:COMPLETED_SHOT

OUTPUT
{uut}:MODE:CONTINUOUS
*/

program continuous_wdg
option +r;

int cmode;  	assign cmode to "{uut}:MODE:CONTINUOUS"; 	monitor cmode;
int cstate;  	assign cstate to "{uut}:MODE:CONTINUOUS:STATE"; monitor cstate;
int shot;  	assign shot to "{uut}:1:SHOT";
int comp_shot; 	assign comp_shot to "{uut}:1:COMPLETED_SHOT";


int verbose;

int rev = 1;

#define CM_EN	1
#define CS_RUN 	2

ss continuous_wdg {
	state init {
		entry {			
			if (macValueGet("verbose")){
				verbose = macValueGet("verbose")[0] - '0';
			}
			printf("continuous_wdg::init rev:%d verbose:%d\n", rev, verbose);
		}
		
		when() {

		} state waitContinuousActive
	}
	state waitContinuousActive {
		entry {
			if (verbose) printf("continuous_wdg::waitContinouousActive\n");
		}
		when(cmode == CM_EN){
			
		} state waitRun
	}
	
	state waitRun {
		entry {
			if (verbose) printf("continuous_wdg::waitRun\n");
		}		
		when(cstate == CS_RUN){
			
		} state waitStop
		when(cmode != CM_EN){
			
		} state waitContinuousActive
	}
	
	state waitStop {
		entry {
			if (verbose) printf("continuous_wdg::waitStop\n");
		}		
		when (cstate != CS_RUN && cmode == CM_EN){
			
		} state forceRestart
		when (cmode != CM_EN){
			
		} state waitContinuousActive
	}
	
	state forceRestart {
		entry {			
			cmode = !CM_EN; pvPut(cmode);
			if (verbose) printf("continuous_wdg::forceRestart RESET\n");
		}
		when(delay(10)){			
			cmode = CM_EN; pvPut(cmode);
			if (verbose) printf("continuous_wdg::forceRestart START\n");
		} state waitRun	
	}
}