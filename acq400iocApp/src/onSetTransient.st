/*
onSetTransient.st : ensures correct trg/event0 for transient condition

INPUT
acq1001_049:MODE:TRANSIENT
acq2006_016:MODE:TRANSIENT:PRE

OUTPUT
acq2006_016:1:TRG:DX		0 (hard) or 1 (soft)
acq2006_016:1:EVENT0		0 (PRE==0), 1 (PRE!=0)
*/

program onSetTransient
option +r;

int transient;	assign transient to 	"{uut}:MODE:TRANSIENT";
int pre; 	assign pre to 		"{uut}:MODE:TRANSIENT:PRE";
int soft_trig;	assign soft_trig to 	"{uut}:1:TRG:DX";
int event;	assign event to		"{uut}:1:EVENT0";

int reset;	assign reset to		"{uut}:1:SIG:SAMPLE_COUNT:RESET";
int resetl;	assign resetl to	"{uut}:1:SIG:sample_count:RESET";

monitor transient;
monitor pre;

int pre0;

int cmode; assign cmode to "{uut}:MODE:CONTINUOUS";
monitor cmode;

int enable; assign enable to "{uut}:asyn:NP.ENBL";

ss onSetTransient {
	state init {
		when(transient != 0) {
			pvGet(pre);
			pre0 = pre;
		} state action
	}
	
	state wait_pre {
		when(pre != pre0){
			pre0 = pre;	
		} state action
	}
	
	state action {
		when() {
			if (pre == 0){
				event = 0;	pvPut(event);
				soft_trig = 0;	pvPut(soft_trig);
			}else{
				event = 1;	pvPut(event);
				soft_trig = 1;	pvPut(soft_trig);
			}
		} state wait_pre
	} 
}


ss actOnContinuous {
	state init {
		when(cmode == 0){
			printf("actOnContinuous DISABLE link\n");
			enable = 0; pvPut(enable);
		} state wait_run
		
		when(cmode == 1){
			reset = 1; pvPut(reset, SYNC);
			resetl = 1; pvPut(resetl, SYNC);
			printf("actOnContinuous ENABLE link\n");
			enable = 1; pvPut(enable);
			reset = 0; pvPut(reset);
			resetl = 0; pvPut(resetl);
		} state wait_stop
	}
	
	state wait_run {
		when(cmode == 1 && delay(2)){
			printf("actOnContinuous RUN detect .. delay\n");
		} state wait_run_delay
	}
	
	state wait_run_delay {
		when(delay(3)){
		
		} state init
	}
	
	state wait_stop {
		when(cmode == 0){
			
		} state init
	}
}