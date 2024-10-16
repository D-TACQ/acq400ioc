/*
hudpResetOnStop.st : reset HUDP when stream stops to ensure no FIFO residuals on next start

INPUT
{uut}:MODE:CONTINUOUS:STATE
{uut}:10:HUDP:TX:ENABLED

OUTPUT
{uut}:10:HUDP:CONTROL
*/

program hudpResetOnStop
option +r;

int cstate; assign cstate to "{uut}:MODE:CONTINUOUS:STATE"; monitor cstate;
int txen;  assign txen to "{uut}:10:HUDP:TX:ENABLED"; monitor txen;
int ctrl;  assign ctrl to "{uut}:10:HUDP:CONTROL";


#define CTRL_OFF 	0
#define CTRL_RESET 	1
#define CTRL_ON		2

#define CS_STOP 0
#define CS_RUN 	2


int verbose;

ss hudpResetOnStop {
	state init {
		entry {
			if (macValueGet("verbose")){
				verbose = macValueGet("verbose")[0] - '0';
			}
			if (verbose) printf("hudpResetOnStop::init\n");
		}		
		
		when(cstate != CS_RUN) {

		} state waitContinuousActive
		
		when(cstate == CS_RUN){

		} state waitContinuousStop	
	}
	state waitContinuousActive {
		entry {
			if (verbose) printf("hudpResetOnStop::waitContinuousActive\n");
		}		
		when(cstate == CS_RUN){
			
		} state waitContinuousStop
	}
	
	state waitContinuousStop {
		entry {
			if (verbose) printf("hudpResetOnStop::waitContinuousStop\n");
		}
		when (txen == 1 && cstate == CS_STOP){
			
		} state resetOnStop
		when (txen != 1 && cstate == CS_STOP){
			
		} state waitContinuousActive
	}
	state resetOnStop {
		entry {			
			ctrl = CTRL_RESET; pvPut(ctrl);
			if (verbose) printf("hudpResetOnStop::resetOnStop\n");
		}
		when(delay(2)) {
			
		} state clearReset
	}
	
	state clearReset {
		entry {			
			ctrl = CTRL_ON; pvPut(ctrl);
			if (verbose) printf("hudpResetOnStop::clearReset\n");
		}
		when(){
			
		} state waitContinuousActive
	}
}