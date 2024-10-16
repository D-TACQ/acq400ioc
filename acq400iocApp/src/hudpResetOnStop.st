/*
hudpResetOnStop.st : reset HUDP when stream stops to ensure no FIFO residuals on next start

INPUT
{uut}:MODE:CONTINUOUS
{uut}:10:HUDP:TX:ENABLED

OUTPUT
{uut}:10:HUDP:CONTROL
*/

program hudpResetOnStop
option +r;

int cmode; assign cmode to "{uut}:MODE:CONTINUOUS"; monitor cmode;
int txen;  assign txen to "{uut}:10:HUDP:TX:ENABLED"; monitor txen;
int ctrl;  assign ctrl to "{uut}:10:HUDP:CONTROL";

/* symbolic constants WBN..
#define CTRL_OFF 	0
#define CTRL_RESET 	1
#define CTRL_ON		2
*/

int verbose;

ss hudpResetOnStop {
	state init {
		entry {
			if (macValueGet("verbose")){
				verbose = macValueGet("verbose")[0] - '0';
			}			
		}		
		
		when(cmode == 0) {

		} state waitContinouousActive
		
		when(cmode != 0){

		} state waitContinuousStop	
	}
	state waitContinouousActive {
		when(cmode != 0){
			
		} state waitContinuousStop
	}
	
	state waitContinuousStop {
		when (txen == 1 && cmode == 0){
			
		} state resetOnStop
		
		when (cmode == 0){
			
		} state waitContinouousActive
	}
	state resetOnStop {
		entry {
			if (verbose) printf("hudpResetOnStop RESET\n");
			ctrl = 1 /*CTRL_RESET*/; pvPut(ctrl);
		}
		when(delay(2)) {
			
		} state clearReset
	}
	
	state clearReset {
		entry {
			if (verbose) printf("hudpResetOnStop ON\n");
			ctrl = 2 /*CTRL_ON*/; pvPut(ctrl);
		}
		when(){
			
		} state waitContinouousActive
	}
}